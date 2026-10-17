#!/usr/bin/env python3
"""Read-only W0 inventory of the pinned main tree before Phase 2 cleanup.

Outputs only a review report and CSV/JSON ledgers. This script never changes
the source tree, experiments, RF constraints or existing evidence.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import posixpath
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
OUT_DATA = ROOT / "data/repository_audits"
OUT_DOCS = ROOT / "docs/repository_audits"
STAMP = "w0_20261017"
BASE_MAIN = "055b222c79c73c7fbeacb19383f21c1da0625195"
TEXT_EXTENSIONS = {
    ".md", ".py", ".json", ".jsonl", ".csv", ".txt", ".yml", ".yaml",
    ".toml", ".ini", ".cfg", ".sh", ".lock", ".gitignore", ".rst",
}
PATH_PATTERN = re.compile(
    r"(?<![\w/])(?:\.\./|\./|/)?"
    r"(?:data|docs|scripts|src|tests|experiments|candidates|"
    r"\.github|results|artifacts)/[A-Za-z0-9_.+/@-]+"
    r"(?:/[A-Za-z0-9_.+@-]+)*"
)
LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def read_at_main(path: str) -> bytes:
    return git("show", BASE_MAIN + ":" + path)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_parts(stem: str, fields: list[str], rows: list[dict], cap: int = 95000) -> list[str]:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    parts, group = [], []
    for row in rows:
        test = group + [row]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(test)
        if len(buf.getvalue().encode("utf-8")) > cap and group:
            parts.append(group)
            group = [row]
        else:
            group = test
    if group or not parts:
        parts.append(group)
    files = []
    for i, chunk in enumerate(parts, 1):
        name = f"{STAMP}_{stem}_{i:03d}.csv"
        with (OUT_DATA / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(chunk)
        files.append(name)
    return files


def classify(path: str, triage: set[str]) -> tuple[str, str, str]:
    area = path.split("/", 1)[0]
    if path in triage:
        return "D", area, "retain_pending_source_context_review"
    if (path.startswith(("data/constraints/", "data/parasitics/")) or path in {
        "data/bands.csv", "data/design_constraints.json",
        "data/experiment_number_registry.csv",
        "docs/chatgpt_project_instructions.md", "uv.lock",
    } or (path.startswith("experiments/") and path.endswith("/manifest.json"))):
        return "A", area, "immutable_or_identity_preserving"
    if (path.startswith(("data/pareto_snapshots/", "data/validation/")) or
            path in {"data/research_candidate_register.csv", "data/experiment_index.csv",
                     "docs/roadmap.md", "docs/specification.md", "README.md"} or
            re.search(r"/EXP-0(4[2-9]|5[0-9])/", path)):
        return "B", area, "retain_index_and_link"
    if (path.startswith("candidates/") or
            (path.startswith("experiments/") and "/EXP-" in path) or
            (path.startswith("docs/") and re.search(r"202610(1[0-5]|0[1-9])", path))):
        return "C", area, "retain_historical_provenance"
    if any(p in path for p in ("/tasks/", "/locks/", "manager.log", "/code_snapshot/")):
        return "D", area, "review_role_no_deletion"
    return "B", area, "retain_in_place_until_review"


def normalize_link(source: str, raw: str, known: set[str]) -> str | None:
    target = unquote(raw.strip().split("#", 1)[0].split("?", 1)[0])
    if not target or target.startswith(("http:", "https:", "mailto:", "data:", "//")):
        return None
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join(posixpath.dirname(source), target))


def main() -> None:
    main_sha = git("rev-parse", BASE_MAIN).decode().strip()
    entries = []
    for item in git("ls-tree", "-r", "-l", "-z", BASE_MAIN).split(b"\0"):
        if not item:
            continue
        left, rawpath = item.split(b"\t", 1)
        mode, typ, sha, size = left.decode().split(" ", 3)
        entries.append({"path": rawpath.decode("utf-8", "surrogateescape"),
                        "mode": mode, "type": typ, "git_blob_sha1": sha,
                        "bytes": int(size) if size != "-" else 0})
    entries.sort(key=lambda e: e["path"])
    known = {e["path"] for e in entries}
    sources = {}
    for e in entries:
        p = e["path"]
        if e["type"] != "blob" or e["bytes"] > 400000:
            continue
        if Path(p).suffix.lower() not in TEXT_EXTENSIONS and Path(p).name not in {
            ".gitignore", "Dockerfile", "Makefile", "requirements.txt", "LICENSE"
        }:
            continue
        data = read_at_main(p)
        if b"\0" in data:
            continue
        sources[p] = data.decode("utf-8", "replace")

    triage = set()
    triage_path = "data/research_storage_triage.csv"
    if triage_path in sources:
        triage = {r["path"] for r in csv.DictReader(io.StringIO(sources[triage_path]))
                  if r.get("path")}

    edges = set()
    missing_markdown = []
    dirs = {posixpath.dirname(p) for p in known}
    for source, text in sources.items():
        for match in LINK_PATTERN.finditer(text):
            target = normalize_link(source, match.group(1), known)
            if target is None:
                continue
            if target in known:
                edges.add((source, target, "markdown"))
            elif target in dirs:
                continue
            elif any(target.lower().endswith(ext) for ext in
                     (".md", ".json", ".csv", ".py", ".yml", ".yaml", ".s2p",
                      ".zip", ".toml", ".txt", ".png", ".svg")):
                missing_markdown.append({"source": source, "target": target,
                                         "raw": match.group(1)[:200]})
        for match in PATH_PATTERN.finditer(text):
            token = match.group(0).strip(".,:;")
            token = token.split("#", 1)[0]
            proposals = [
                posixpath.normpath(token.lstrip("/")),
                posixpath.normpath(posixpath.join(posixpath.dirname(source), token)),
            ]
            for target in proposals:
                if target in known and target != source:
                    edges.add((source, target, "inline"))
                    break

    by_sha = collections.defaultdict(list)
    for e in entries:
        if e["type"] == "blob":
            by_sha[e["git_blob_sha1"]].append(e["path"])
    duplicates = {k: v for k, v in by_sha.items() if len(v) > 1}
    inbound, outbound = collections.Counter(), collections.Counter()
    for s, t, kind in edges:
        inbound[t] += 1
        outbound[s] += 1

    rows = []
    for e in entries:
        path = e["path"]
        cls, area, action = classify(path, triage)
        rows.append({**e, "area": area, "retention_class": cls,
                     "proposed_disposition": action,
                     "inbound_static_ref_count": inbound[path],
                     "outbound_static_ref_count": outbound[path],
                     "same_blob_other_path_count": len(by_sha[e["git_blob_sha1"]]) - 1,
                     "legacy_triage": "yes" if path in triage else "no",
                     "move_risk": "high" if cls in ("A", "D") or inbound[path] else "needs_review"})
    file_parts = csv_parts("files", list(rows[0]), rows)
    edge_rows = [{"source": s, "target": t, "kind": k} for s, t, k in sorted(edges)]
    edge_parts = csv_parts("references", ["source", "target", "kind"], edge_rows)
    missing_parts = csv_parts("unresolved_markdown_links",
                              ["source", "target", "raw"], missing_markdown)
    duplicate_rows = [{"git_blob_sha1": k, "path_count": len(v), "paths": ";".join(v)}
                      for k, v in sorted(duplicates.items())]
    duplicate_parts = csv_parts("same_blob_groups",
                                ["git_blob_sha1", "path_count", "paths"], duplicate_rows)

    issues = []
    registry = json.loads(sources["data/constraints/registry.json"])
    if registry.get("active_formal_id") != "RF-F003":
        issues.append("active formal RF ID is not RF-F003")
    a = read_at_main("data/constraints/formal/RF-F003.json")
    b = read_at_main("data/design_constraints.json")
    formal_equal_compatibility = a == b
    if not formal_equal_compatibility:
        issues.append("design_constraints.json differs from RF-F003 formal file")
    rf = json.loads(a)
    s2p_checks = []
    par = rf.get("external_port_parasitics", {})
    for item in ("input_parasitic", "output_parasitic"):
        spec = par.get(item, {})
        p = spec.get("path", "")
        expected = spec.get("sha256", "")
        if p not in known:
            issues.append("missing external parasitic: " + p)
            s2p_checks.append({"path": p, "status": "missing"})
        else:
            got = digest(read_at_main(p))
            ok = got == expected
            if not ok:
                issues.append("parasitic hash mismatch: " + p)
            s2p_checks.append({"path": p, "sha256": got, "matches_spec": ok})

    snapshot_path = "data/pareto_snapshots/rf_t005_rf_f003_20261017.json"
    snapshot = json.loads(read_at_main(snapshot_path))
    by_condition = {}
    checkpoint_checks = []
    for condition in snapshot["conditions"]:
        candidates = condition.get("candidates", [])
        by_condition[condition["constraint_id"]] = len(candidates)
        for item in candidates:
            src = item.get("source", {}).get("complete_parameter_vector", {})
            path, claimed = src.get("path", ""), src.get("blob_sha", "")
            actual = next((e["git_blob_sha1"] for e in entries if e["path"] == path), "")
            ok = bool(actual) and (not claimed or claimed == actual)
            checkpoint_checks.append({"candidate_id": item.get("id"),
                                      "path": path, "exists": bool(actual),
                                      "blob_sha_matches_snapshot": ok})
            if not ok:
                issues.append("Pareto checkpoint reference/hash issue: " + str(item.get("id")))

    out_classes = collections.Counter(r["retention_class"] for r in rows)
    top = collections.defaultdict(lambda: [0, 0])
    for row in rows:
        top[row["area"]][0] += 1
        top[row["area"]][1] += row["bytes"]

    report_lines = [
        "# Step 1：最新main全追跡ファイル棚卸しと参照監査（2026-10-17）",
        "",
        "> **実行済みの読み取り専用監査。** この文書は自動抽出結果であり、"
        "移動・削除・無参照証明・回路最適化・物理検証ではない。",
        "",
        f"- 対象main SHA：`{main_sha}`",
        f"- 再帰Git tree：**{len(entries)} entries**（Git ls-tree -r、全追跡entry）",
        f"- 追跡ファイルの非圧縮size合計：**{sum(r['bytes'] for r in rows):,} bytes**",
        f"- 静的参照として検出：**{len(edges)} edges**（text {len(sources)} filesを解析）",
        f"- 同一Git blob複数path：**{len(duplicates)} groups**（余分なpath {sum(len(v)-1 for v in duplicates.values())}件）",
        f"- 旧46要レビュー台帳に記録：**{len(triage)} paths**（現mainに存在：{len(triage & known)}）",
        f"- 未解決候補のMarkdownローカルリンク：**{len(missing_markdown)}**（手動精査が必要）",
        "",
        "## 1. ルート領域の個数・非圧縮サイズ",
        "",
        "| area | entries | bytes |",
        "|---|---:|---:|",
    ]
    for key, val in sorted(top.items(), key=lambda kv: -kv[1][1]):
        report_lines.append(f"| `{key}` | {val[0]} | {val[1]:,} |")
    report_lines += [
        "",
        "## 2. 分類と処置（削除の自動承認なし）",
        "",
        "| 保全分類 | 件数 | 処置 |",
        "|---|---:|---|",
        f"| A：正本・原manifest | {out_classes['A']} | 元pathを維持 |",
        f"| B：成果・検証／稼働文書 | {out_classes['B']} | 索引化し元を保全 |",
        f"| C：履歴 | {out_classes['C']} | 出典を保全し目次で分離 |",
        f"| D：個別要レビュー | {out_classes['D']} | 削除・移動は保留 |",
        "",
        "※自動分類はパス・過去台帳に基づく**一次分類**。B/C分類にも重要な原証拠が存在する。",
        "※inbound参照0は不要の証明でない。動的パス、Git履歴、外部チャット、実行時依存は静的解析では網羅できない。",
        "",
        "## 3. 重要な正本・最新パレートの照合",
        "",
        f"- 制約台帳 active正式ID：`{registry.get('active_formal_id')}`",
        f"- `data/design_constraints.json`と正式RF-F003のバイト一致：**{formal_equal_compatibility}**",
        f"- 2026-10-17パレート保存点：**{by_condition}**",
        f"- 完全checkpoint参照：**{sum(x['blob_sha_matches_snapshot'] for x in checkpoint_checks)}/{len(checkpoint_checks)} SHA一致かつ現存**",
    ]
    for item in s2p_checks:
        report_lines.append(f"- S2P原本：`{item['path']}` SHA256合致：**{item.get('matches_spec', False)}**")
    report_lines += [
        "",
        "## 4. 優先して手動確認する事項",
        "",
        "1. 未解決Markdownリンク：ファイル移動の前に意図した相対パスかを調査する（検出＝自動破損判定ではない）。",
        "2. A区分の正本・元manifest、D区分の旧46証拠に対する移動を禁止したまま、B/Cの閲覧用索引のみ先行整備する。",
        "3. 動的に組み立てるコードのパス、JSON内フィールド参照、CIの相互依存は別途意味解析を行う。",
        "4. 同一blobはrun由来やsource_prの意味が異なる可能性があるため、削除しない。",
        "5. 現行10候補の出典・面積・独立検証と、旧14件候補台帳の統合方法はStep 3で定義する。",
        "",
        "## 5. 機械可読データ",
        "",
        "- 全ファイル台帳（path、size、Git blob SHA、区分、静的参照数、移動リスク）："
        + ", ".join(f"[{x}](../../data/repository_audits/{x})" for x in file_parts),
        "- 検出参照辺：" + ", ".join(f"[{x}](../../data/repository_audits/{x})" for x in edge_parts),
        "- 未解決Markdownリンク候補：" + ", ".join(f"[{x}](../../data/repository_audits/{x})" for x in missing_parts),
        "- 同一blobの別path：" + ", ".join(f"[{x}](../../data/repository_audits/{x})" for x in duplicate_parts),
        "- [集計JSON](../../data/repository_audits/step1_20261017_summary.json)",
        "",
        "## 6. 適用範囲の限界",
        "",
        "本監査は2026-10-17 W0固定mainのtracked Git treeと読み取れる小容量テキストを検査した。"
        "Git履歴全体・未追跡ローカル結果・外部添付・Actions期限付きartifact、"
        "実行時に生成される依存関係は調べていない。リンク抽出は保守的な静的ヒューリスティックであり"
        "未検出参照を根拠に消去してはならない。全tracked bytesはpack容量を表さない。",
        "",
        "**現在の作業はStep 1の棚卸しのみ。研究Phase 2を維持し、Phase 3は開始しない。**",
    ]
    if issues:
        report_lines += ["", "## 監査上の不整合（解決前に移動禁止）", ""] + [
            "- " + x for x in issues
        ]
    OUT_DOCS.mkdir(parents=True, exist_ok=True)
    (OUT_DOCS / (STAMP + "_report.md")).write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8")
    summary = {
        "phase": "Phase 2", "audit_type": "read_only_git_main_tree_static_dependencies",
        "main_sha": main_sha, "tracked_entries": len(entries),
        "tracked_bytes": sum(e["bytes"] for e in entries),
        "top_level": {k: {"count": v[0], "bytes": v[1]} for k, v in sorted(top.items())},
        "retention_class_counts": dict(out_classes),
        "static_reference_edges": len(edges), "scanned_text_files": len(sources),
        "same_blob_groups": len(duplicates),
        "same_blob_extra_paths": sum(len(v) - 1 for v in duplicates.values()),
        "prior_triage_records": len(triage), "prior_triage_paths_present": len(triage & known),
        "unresolved_markdown_link_candidates": len(missing_markdown),
        "active_formal_constraint": registry.get("active_formal_id"),
        "formal_copy_byte_equal": formal_equal_compatibility,
        "parasitic_sha256_checks": s2p_checks,
        "pareto_candidate_counts": by_condition,
        "pareto_checkpoint_checks": checkpoint_checks,
        "issues": issues, "read_only": True, "no_deletions": True,
        "files": file_parts, "references": edge_parts,
        "unresolved_links": missing_parts, "duplicate_groups": duplicate_parts,
        "limitations": ["static_paths_only", "source_text_le_400KB",
                        "no_git_history_or_untracked_files", "classification_is_provisional"],
    }
    (OUT_DATA / (STAMP + "_summary.json")).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "main_sha": main_sha, "tracked_entries": len(entries),
        "tracked_bytes": summary["tracked_bytes"], "reference_edges": len(edges),
        "classification": summary["retention_class_counts"],
        "pareto_counts": by_condition, "issues": issues,
        "files_parts": file_parts, "reference_parts": edge_parts
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
