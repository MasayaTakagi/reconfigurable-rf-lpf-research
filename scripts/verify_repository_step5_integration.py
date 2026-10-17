#!/usr/bin/env python3
"""Phase 2 Step 5 read-only structural and preserved-source verification.

The procedure verifies integrity and traceability of previously saved results.
It does not re-simulate RF circuits or claim physical verification.
"""
from __future__ import annotations

import csv
import hashlib
import json
import posixpath
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
BASE = "bdb39904379637aeca5cf56ec3096e9e1b15f62a"
ALLOW_EXISTING_PATH_EDITS = {
    ".github/workflows/audit.yml",
    "README.md", "docs/historical_results.md", "docs/roadmap.md",
    "scripts/report_research_pareto.py",
    "data/experiment_evidence_inventory.csv",
    "scripts/audit_experiment_inventory.py", "scripts/build_reference_inventory.py",
    "src/lpf/experiment_manifest.py",
    "tests/test_experiment_provenance.py", "tests/test_candidate_guardrails.py",
}
ADDED_NAV = {
    "docs/README.md", "docs/current/phase2_status.md",
    "docs/current/open_research_questions.md", "docs/results/README.md",
    "docs/results/phase2_candidate_catalog_20261017.md",
    "docs/archive/README.md", "docs/methods/README.md",
    "docs/governance/README.md", "data/README.md", "experiments/README.md",
    "scripts/README.md", "data/catalog/README.md",
    "data/repository_reviews/README.md",
    "docs/repository_audits/step1_20261017_report.md",
    "docs/repository_audits/step1_20261017_review_notes.md",
    "docs/phase2_repository_step4_review_20261017.md",
}
LOCAL_LINK = re.compile(r"\]\(([^)]+)\)")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def tree(ref):
    records = {}
    for entry in git("ls-tree", "-r", "-l", "-z", ref).split(b"\0"):
        if not entry:
            continue
        left, path = entry.split(b"\t", 1)
        mode, kind, sha, byte_size = left.decode().split(" ", 3)
        if kind != "blob":
            raise ValueError("non-blob entry: " + path.decode())
        records[path.decode("utf-8")] = {
            "blob_sha1": sha, "bytes": int(byte_size), "mode": mode,
        }
    return records


def sha256(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def read_csv(path):
    with (ROOT / path).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run():
    main_head = git("rev-parse", "origin/main").decode().strip()
    if main_head != BASE:
        raise ValueError("main moved: audit this newer baseline in a separate run")
    old, current = tree(BASE), tree("HEAD")
    if len(old) != 1043:
        raise ValueError("unexpected 2026-10-17 tracked baseline")
    missing = sorted(set(old) - set(current))
    changed = sorted(path for path in old if path in current and
                     old[path]["blob_sha1"] != current[path]["blob_sha1"])
    if missing:
        raise ValueError("original tracked source removed: " + repr(missing))
    unapproved = sorted(set(changed) - ALLOW_EXISTING_PATH_EDITS)
    if unapproved:
        raise ValueError("original source file changed unexpectedly: " + repr(unapproved))
    if not set(ADDED_NAV).issubset(current):
        raise ValueError("one or more navigation pages were not integrated")
    for p in ("data/constraints/registry.json", "data/bands.csv",
              "data/constraints/formal/RF-F003.json", "data/design_constraints.json"):
        if old[p]["blob_sha1"] != current[p]["blob_sha1"]:
            raise ValueError("RF canonical input changed: " + p)
    formal = json.loads((ROOT / "data/constraints/formal/RF-F003.json").read_text())
    registry = json.loads((ROOT / "data/constraints/registry.json").read_text())
    if registry["active_formal_id"] != "RF-F003":
        raise ValueError("formal constraint unexpectedly changed")
    if (ROOT / "data/constraints/formal/RF-F003.json").read_bytes() != (
            ROOT / "data/design_constraints.json").read_bytes():
        raise ValueError("formal compatibility bytes diverge")
    parasitic_hashes = {}
    for kind in ("input_parasitic", "output_parasitic"):
        item = formal["external_port_parasitics"][kind]
        path = item["path"]
        h = sha256(path)
        if h != item["sha256"] or old[path]["blob_sha1"] != current[path]["blob_sha1"]:
            raise ValueError("fixed S2P source does not match RF-F003: " + path)
        parasitic_hashes[kind] = h

    snap = json.loads((ROOT / "data/pareto_snapshots/rf_t005_rf_f003_20261017.json").read_text())
    summary = json.loads((ROOT / "data/catalog/phase2_candidate_catalog_20261017_summary.json").read_text())
    candidates = read_csv("data/catalog/phase2_candidate_catalog_20261017.csv")
    if (len(candidates), summary["legacy_count"], summary["snapshot_count"]) != (24, 14, 10):
        raise ValueError("derived catalog candidate count diverges from source")
    if [x["constraint_id"] for x in snap["conditions"]] != ["RF-T005", "RF-F003"]:
        raise ValueError("original Pareto constraint identities changed")
    expected = {"RF-T005": 6, "RF-F003": 4}
    grouped = {}
    for condition in snap["conditions"]:
        cid = condition["constraint_id"]
        if len(condition["candidates"]) != expected[cid]:
            raise ValueError("original snapshot front candidate count changed")
        records = [r for r in candidates if r["constraint_id"] == cid]
        if len(records) != expected[cid]:
            raise ValueError("merged catalog missing current candidates")
        fingerprints = {(r["constraint_class"], r["constraint_id"],
                         r["effective_constraint_sha256"], r["objective"],
                         r["requirement_db"], r["threshold_classification"],
                         r["comparison_key"]) for r in records}
        if len(fingerprints) != 1:
            raise ValueError("RF-T005/RF-F003 policy comparison contamination: " + cid)
        if (condition["effective_constraint_sha256"] !=
                next(iter(fingerprints))[2]):
            raise ValueError("snapshot effective policy hash mismatch")
        by_id = {r["catalog_id"]: r for r in records}
        for rec in condition["candidates"]:
            row = by_id[rec["id"]]
            if float(row["worst_il_db"]) != float(rec["metrics"]["worst_il_db"]):
                raise ValueError("saved worst IL differs: " + rec["id"])
            if not rec["verification"]["finite_mesh_H2_H3_30dB_pass"]:
                raise ValueError("candidate mandatory H2/H3 not passed: " + rec["id"])
            original = rec["source"]["complete_parameter_vector"]
            p = original["path"]
            if old[p]["blob_sha1"] != current[p]["blob_sha1"] or current[p]["blob_sha1"] != original["blob_sha"]:
                raise ValueError("original 10-vector source hash changed: " + p)
        grouped[cid] = len(records)

    missing_links = []
    local_links_checked = 0
    for source in sorted(ADDED_NAV | {"README.md", "docs/roadmap.md",
                                     "docs/historical_results.md"}):
        body = (ROOT / source).read_text(encoding="utf-8")
        for m in LOCAL_LINK.finditer(body):
            raw = unquote(m.group(1).split("#", 1)[0].split("?", 1)[0])
            if not raw or raw.startswith(("https:", "http:", "mailto:", "data:", "//")):
                continue
            normalized = posixpath.normpath(posixpath.join(
                posixpath.dirname(source), raw.lstrip("/")))
            local_links_checked += 1
            if not (ROOT / normalized).exists():
                missing_links.append({"source": source, "target": raw})
    if missing_links:
        raise ValueError("local Markdown links unresolved: " + repr(missing_links))

    step1 = json.loads((ROOT / "data/repository_audits/step1_20261017_summary.json").read_text())
    step4 = json.loads((ROOT / "data/repository_reviews/step4_summary_20261017.json").read_text())
    if (step1["tracked_entries"] != 1043 or
            step4["source_main_document_count"] != 56 or
            step4["identical_blob_groups"] != 34 or
            step4["retention_review_records"] != 46 or
            step4["source_files_moved_or_deleted"] != 0):
        raise ValueError("archived Step 1/4 baseline audits diverge")

    return {
        "phase": "Phase 2",
        "main_sha": BASE,
        "head_sha": git("rev-parse", "HEAD").decode().strip(),
        "main_original_paths": len(old),
        "original_paths_deleted": 0,
        "existing_paths_modified": len(changed),
        "modified_original_paths": changed,
        "preserved_original_blob_count": len(old) - len(changed),
        "source_changes_outside_explicit_allowlist": [],
        "added_file_count": len(current) - len(old),
        "total_integrated_tracked_files": len(current),
        "added_navigation_markdown_pages_checked": len(ADDED_NAV),
        "local_markdown_links_checked": local_links_checked,
        "unresolved_local_links": 0,
        "formal_constraint": "RF-F003",
        "formal_copy_byte_equal": True,
        "fixed_s2p_sha256": parasitic_hashes,
        "preserved_current_pareto": grouped,
        "combined_catalog_count": len(candidates),
        "archived_step1_original_count": step1["tracked_entries"],
        "archived_step4_retention_pending": step4["retention_review_records"],
        "new_Rf_simulation": False,
        "physical_qualification": False,
        "phase3_started": False,
        "limits": ["No new RF MNA/reoptimization performed here.",
                   "Original full simulation replay remains unverified.",
                   "Static docs link resolution only; external pages/anchors unverified.",
                   "End-to-end repository CI must pass separately."],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    out = run()
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
