#!/usr/bin/env python3
"""W2: derived, provenance-pinned electrical and magnetic search for 24 entries.

No RF simulation, optimization, or evidence mutations. Unknown legacy fields
remain unknown; signed k is a numerical coupling parameter and NOT a proof
that a physical coil dot orientation or placement is feasible.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
from collections import Counter
from pathlib import Path

from build_phase2_candidate_catalog import git_blob_sha1, safe_evidence

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "data/catalog/phase2_candidate_catalog_20261017.csv"
DEST = "data/catalog/phase2_candidate_topology_search_20261017.csv"
SUMMARY = "data/catalog/phase2_candidate_topology_search_20261017_summary.json"
REPORT = "docs/results/phase2_candidate_topology_search_20261017.md"
FIELDS = (
    "catalog_id", "experiment_id", "constraint_class", "constraint_id",
    "comparison_key", "chip_area_units", "worst_il_db", "number_of_inductors",
    "topology_label_as_reported", "inductor_electrical_edges",
    "inductor_physical_order_as_reported", "signed_coupling_pair_order",
    "signed_coupling_values", "coupling_sign_pattern", "positive_k_count",
    "negative_k_count", "zero_k_count", "physical_dot_orientation_proven",
    "electrical_connections_extraction", "physical_order_extraction",
    "coupling_values_extraction", "source_checkpoint_path",
    "source_checkpoint_git_blob_sha1", "source_subcandidate_id",
    "structural_metadata_status",
)
THREE = ("L0-Ls", "Ls-L1")
FOUR = ("L0-L1", "L1-L3", "L3-L2")
TOKEN_3L = ("k01", "k(L0,Ls)", "k_L0_Ls", "k(L0-Ls)")
TOKEN_4L = ("k01", "k(L0-L1)")
EDGE_REGEX = re.compile(r"(L\d+|Ls)\((\d+),(\d+)\)")


def read_csv(root, rel):
    with (root / rel).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fmt_csv(rows):
    dest = io.StringIO(newline="")
    w = csv.DictWriter(dest, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return dest.getvalue()


def topology_from_source(source):
    if isinstance(source.get("topology"), str) and source["topology"]:
        return source["topology"]
    if isinstance(source.get("base_topology"), str) and source["base_topology"]:
        return source["base_topology"]
    if isinstance(source.get("variant"), str) and source["variant"]:
        return source["variant"]
    if isinstance(source.get("new_semantics"), str) and source["new_semantics"]:
        return source["new_semantics"]
    return "unknown"


def reported_edges(source):
    explicit = source.get("L_edges")
    if isinstance(explicit, list) and all(
            isinstance(x, list) and len(x) == 2 and
            all(isinstance(v, int) for v in x) for x in explicit):
        return ";".join(f"L{i}({edge[0]},{edge[1]})"
                        for i, edge in enumerate(explicit)), "explicit_L_edges"
    text = source.get("topology", "")
    if not isinstance(text, str):
        return "unknown", "not_reported"
    matches = EDGE_REGEX.findall(text)
    if matches:
        return ";".join(f"{l}({a},{b})" for l, a, b in matches), "parsed_reported_topology"
    return "unknown", "not_reported"


def physical_order(source):
    for key in ("physical_L_order", "physical_inductor_order", "L_order"):
        val = source.get(key)
        if isinstance(val, list) and all(isinstance(x, str) for x in val):
            return "-".join(val), "explicit_" + key
        if isinstance(val, str) and val:
            return val, "explicit_" + key
    topo = source.get("topology", "")
    if isinstance(topo, str) and "adjacent k [L0-Ls,Ls-L1]" in topo:
        return "L0-Ls-L1", "reported_adjacent_pair_chain"
    return "unknown", "not_reported"


def signed_couplings(record, source):
    n_l = record["num_lqp02hv"]
    descriptor = str(source.get("vector_order") or source.get("variables") or "")
    if n_l == "3":
        pairs, idx, expected_len = THREE, 6, 26
        if not any(s in descriptor for s in TOKEN_3L):
            raise ValueError("3L coupling variable names not explicit: " + record["catalog_id"])
    elif n_l == "4":
        pairs, idx, expected_len = FOUR, 8, 29
        if "params" not in source and not any(s in descriptor for s in TOKEN_4L):
            raise ValueError("4L coupling variable names not explicit: " + record["catalog_id"])
    else:
        raise ValueError("unexpected archived target L count")
    if "candidates" in source:
        target = record["source_subcandidate_id"]
        matched = [c for c in source["candidates"] if c.get("id") == target]
        if len(matched) != 1:
            raise ValueError("checkpoint selected subcandidate missing: " + target)
        params = matched[0]["params"]
        if not isinstance(params, dict):
            raise ValueError("missing selected params")
        if n_l != "4" or source.get("L_order") != "L0-L1-L3-L2":
            raise ValueError("unexpected multi-candidate k layout")
        vals = params["k_adjacent_L0_L1_L1_L3_L3_L2"]
        vector = params["flattened_vector"]
        if len(vector) != expected_len or any(
                not math.isclose(float(a), float(b), abs_tol=1e-12)
                for a, b in zip(vals, vector[idx:idx+len(pairs)])):
            raise ValueError("named coupling values are inconsistent with vector")
        method = "explicit_selected_params_k_pairs"
    else:
        vector = source.get("vector")
        if not isinstance(vector, list) or len(vector) != expected_len:
            raise ValueError("checkpoint vector length or source format changed")
        vals = vector[idx:idx+len(pairs)]
        method = "reported_named_vector_order"
    if len(vals) != len(pairs) or not all(
            isinstance(v, (int, float)) and math.isfinite(v) and -0.101 <= v <= 0.101
            for v in vals):
        raise ValueError("non-finite or out-of-policy signed k in " + record["catalog_id"])
    signs = ["+" if v > 1e-10 else "-" if v < -1e-10 else "0" for v in vals]
    return (
        ";".join(pairs), ";".join(f"{float(v):.12g}" for v in vals),
        ",".join(signs), signs.count("+"), signs.count("-"), signs.count("0"), method
    )


def build(root=ROOT):
    root = Path(root)
    existing = read_csv(root, SOURCE)
    if len(existing) != 24 or len({r["catalog_id"] for r in existing}) != 24:
        raise ValueError("expected 24 unique 2026-10-17 archive candidates")
    results = []
    for item in existing:
        row = {
            "catalog_id": item["catalog_id"],
            "experiment_id": item["experiment_id"],
            "constraint_class": item["constraint_class"],
            "constraint_id": item["constraint_id"],
            "comparison_key": item["comparison_key"],
            "chip_area_units": item["chip_area_units"],
            "worst_il_db": item["worst_il_db"],
            "number_of_inductors": item["num_lqp02hv"] or "unknown",
            "topology_label_as_reported": "unknown",
            "inductor_electrical_edges": "unknown",
            "inductor_physical_order_as_reported": "unknown",
            "signed_coupling_pair_order": "unknown",
            "signed_coupling_values": "unknown",
            "coupling_sign_pattern": "unknown",
            "positive_k_count": "unknown",
            "negative_k_count": "unknown",
            "zero_k_count": "unknown",
            "physical_dot_orientation_proven": "false",
            "electrical_connections_extraction": "not_extracted",
            "physical_order_extraction": "not_extracted",
            "coupling_values_extraction": "not_extracted",
            "source_checkpoint_path": item["checkpoint_path"],
            "source_checkpoint_git_blob_sha1": item["checkpoint_git_blob_sha1"],
            "source_subcandidate_id": item["source_subcandidate_id"],
            "structural_metadata_status": "legacy_not_extracted",
        }
        if item["origin"] == "archived_pareto_snapshot":
            raw = safe_evidence(root, item["checkpoint_path"])
            if git_blob_sha1(raw) != item["checkpoint_git_blob_sha1"]:
                raise ValueError("source checkpoint Git blob changed: " + item["catalog_id"])
            source = json.loads(raw)
            label = topology_from_source(source)
            edges, edge_method = reported_edges(source)
            order, order_method = physical_order(source)
            pairs, values, signs, positives, negatives, zeros, couplings = signed_couplings(item, source)
            row.update({
                "topology_label_as_reported": label,
                "inductor_electrical_edges": edges,
                "inductor_physical_order_as_reported": order,
                "signed_coupling_pair_order": pairs,
                "signed_coupling_values": values,
                "coupling_sign_pattern": signs,
                "positive_k_count": positives, "negative_k_count": negatives,
                "zero_k_count": zeros,
                "electrical_connections_extraction": edge_method,
                "physical_order_extraction": order_method,
                "coupling_values_extraction": couplings,
                "structural_metadata_status": "source_reported_numeric_k_not_physical_proof",
            })
        else:
            # Historic rows have diverse source schemas; do not fabricate a
            # physical ordering or connection graph from the row's chip count.
            if item["origin"] != "legacy_curated_register":
                raise ValueError("unexpected archival row origin: " + str(item["origin"]))
        results.append(row)
    counts = Counter(x["structural_metadata_status"] for x in results)
    if (len(results), counts["source_reported_numeric_k_not_physical_proof"],
            counts["legacy_not_extracted"]) != (24, 10, 14):
        raise ValueError("unexpected structural extraction coverage")
    return results, {
        "phase": "Phase 2", "status": "derived_search_metadata_not_new_rf_results",
        "source_catalog": SOURCE, "rows": len(results),
        "archived_current_rf_candidate_rows_with_reported_signed_k": 10,
        "historical_legacy_rows_preserved_as_unknown": 14,
        "structure_status_counts": dict(sorted(counts.items())),
        "unknown_is_not_zero": True,
        "physical_dot_orientations_proven": 0,
        "new_rf_solver_runs": 0, "original_source_files_modified": 0,
        "limitations": [
            "L connectivity only when explicitly reported; unknown otherwise",
            "Reported physical coil order is only source metadata, not physical placement verification",
            "Signed k parameter does not prove physical coupling or magnet dot orientation",
            "Old 14 candidates remain unknown pending per-checkpoint schema review",
            "No computation of IL, harmonics, MNA, EM, layout, SRF, Q(f), or tolerances",
        ],
    }


def make():
    rows, summary = build()
    lines = [
        "# Phase 2 W2：24候補の回路構造・結合符号検索（2026-10-17）",
        "",
        "旧14件＋RF-T005/RF-F003最新10件の派生索引。"
        "元CSV/JSON/checkpointを変更せず、元Git blob SHAと実際のsource項目を照合。",
        "**結合の符号は数値モデル中のsigned kを表し、実際の巻線ドット極性・EMでの同時結合実現性を証明しない。**",
        "",
        f"[検索CSV](../../{DEST}) と [監査サマリー](../../{SUMMARY}) を参照。",
        "",
        "| catalog_id | 条件 | L数 | 電気的L接続 | 物理順（元文書記載） | k符号順 |",
        "|---|---|---:|---|---|---|",
    ]
    for r in rows:
        lines.append("| " + " | ".join([
            r["catalog_id"], r["constraint_id"] or "historical",
            r["number_of_inductors"], r["inductor_electrical_edges"],
            r["inductor_physical_order_as_reported"], r["coupling_sign_pattern"]]) + " |")
    lines += [
        "", "## 検索と限界", "",
        "- num_lqp02hv/constraint_id/chip_area_units/worst_il_db は元24候補台帳と合わせて絞り込む。",
        "- coupling_sign_pattern は明示されたLペア順に正(+)、負(-)、ほぼ0(0)を並べた記録値。",
        "- 電気的接続は checkpoint の L_edges または topology の明示エッジ表記のみ抽出。",
        "- 旧14候補の未解析構造は unknown（「存在しない」「結合0」ではない）。",
        "- 当日保存されたcheckpoint固有の変数並びを確認してkを抽出。再最適化・EM検証ではない。",
        "- ソースの Git blob が変化したら再生成・照合は失敗する。",
        "- **Phase 2継続、Phase 3未着手。**", "",
    ]
    outputs = {
        DEST: fmt_csv(rows),
        SUMMARY: json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        REPORT: "\n".join(lines),
    }
    return outputs, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files, overview = make()
    for rel, content in files.items():
        path = ROOT / rel
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise SystemExit("W2 structure search output drift: " + rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(json.dumps({
        "status": "PASS" if args.check else "generated",
        "candidates": overview["rows"],
        "source_extracted": overview["archived_current_rf_candidate_rows_with_reported_signed_k"],
        "historical_unknown": overview["historical_legacy_rows_preserved_as_unknown"],
        "original_sources_changed": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
