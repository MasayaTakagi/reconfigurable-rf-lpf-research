#!/usr/bin/env python3
"""Read-only Step 4 history and same-blob disposition audit, pinned to main.

All Git-tracked originals remain at their original paths. This script produces
a derived historical-document index and review-only evidence ledgers; it never
deletes, moves or rewrites any existing tracked research evidence.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import posixpath
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_MAIN_SHA = "bdb39904379637aeca5cf56ec3096e9e1b15f62a"
DATE = "2026-10-17"

DOC_CSV = "data/repository_reviews/step4_historical_documents_20261017.csv"
DUP_CSV = "data/repository_reviews/step4_identical_blob_groups_20261017.csv"
TRIAGE_CSV = "data/repository_reviews/step4_retention_46_20261017.csv"
SUMMARY = "data/repository_reviews/step4_summary_20261017.json"
ARCHIVE_MD = "docs/archive/README.md"
REPORT = "docs/phase2_repository_step4_review_20261017.md"

CURRENT_DOCS = {
    "docs/chatgpt_project_instructions.md",
    "docs/specification.md",
    "docs/roadmap.md",
    "docs/pareto_rf_t005_rf_f003_20261017.md",
}
METHOD_BASENAMES = {
    "full_lpf_execution.md", "local_execution.md", "p4_a_scope.md",
    "inductor_series_policy.md", "topology_search_lessons.md",
    "r2_handoff.md", "EXP015_COMMON_MODEL_AUDIT.json",
}
GOVERNANCE_BASENAMES = {
    "experiment_manifests.md",
    "experiment_number_reservation_policy_20261015.md",
    "experiment_result_storage_policy_proposal_20261015.md",
    "research_result_governance.md",
    "repository_reorganization_plan.md",
    "result_record_corrections_20261014.md",
    "repository_storage_audit_20261014.md",
    "phase2_repository_optimization_review_20261015.md",
    "phase2_evidence_triage_20261015.md",
    "phase2_storage_pareto_review_20261015.md",
    "phase2_actions_ci_repair_20261017.md",
}
GROUP_NAMES = {
    "current_reference": "現行の正本・結果（履歴として移動しない）",
    "old_rft003": "旧RF-T003 系列（当時の計算・試験条件）",
    "old_rff002_t004": "旧RF-F001 / RF-F002 / RF-T004・EXP研究の記録",
    "methods_and_theory": "研究方法・基礎理論（実装・物理検証との区別を要する）",
    "governance_and_provenance": "保全・出典・管理・旧計画（当時の状態）",
    "other_historical": "その他の時点付き研究・計画",
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def read_source(path: str) -> bytes:
    return git("show", "origin/main:" + path)


def collect_main_tree():
    actual = git("rev-parse", "origin/main").decode().strip()
    if actual != BASE_MAIN_SHA:
        raise ValueError("main SHA changed; review and re-pin the historical evidence before re-running")
    result = []
    for raw in git("ls-tree", "-r", "-l", "-z", "origin/main").split(b"\0"):
        if not raw:
            continue
        left, path = raw.split(b"\t", 1)
        mode, typ, sha, size = left.decode("ascii").split(" ", 3)
        if typ != "blob":
            raise ValueError("unexpected non-blob in tracked tree: " + str(path))
        result.append({
            "path": path.decode("utf-8", "surrogateescape"), "git_blob_sha1": sha,
            "bytes": int(size), "mode": mode,
        })
    result.sort(key=lambda x: x["path"])
    if len(result) != 1043:
        raise ValueError("Step 1 baseline expected exactly 1,043 main tracked entries")
    return result


def group_doc(path: str) -> str:
    name = posixpath.basename(path)
    if path in CURRENT_DOCS:
        return "current_reference"
    if name.startswith("rft003_"):
        return "old_rft003"
    if (name.startswith(("rf_f002_", "exp016_", "exp017_")) or
            name.startswith("phase2_exp017_") or
            path.startswith("docs/research/")):
        return "old_rff002_t004"
    if (name in METHOD_BASENAMES or
            name.startswith(("phase2_t_", "phase2_pi_"))):
        return "methods_and_theory"
    if (name in GOVERNANCE_BASENAMES or path.startswith("docs/maintenance/")):
        return "governance_and_provenance"
    return "other_historical"


def format_csv(records, columns):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return out.getvalue()


def source_title(path: str) -> str:
    if path.endswith(".json"):
        return posixpath.basename(path) + " (JSON source)"
    for line in read_source(path).decode("utf-8", "replace").splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip().replace("|", "／")[:160]
    return posixpath.basename(path)


def classify_blob(paths):
    if set(paths) == {"data/constraints/formal/RF-F003.json",
                      "data/design_constraints.json"}:
        return "immutable_formal_compatibility_mirror", "A", "retain_both_paths"
    if any("/source_pr" in x for x in paths):
        return "pr_source_provenance", "D", "retain_pending_source_review"
    if any("/code_snapshot/" in x for x in paths):
        return "execution_code_snapshot", "A", "retain_source_and_execution_copy"
    if all("/logs/" in x or x.endswith("/manager.log") for x in paths):
        return "run_log_restart_evidence", "D", "retain_pending_run_context_review"
    if all("/tasks/" in x for x in paths):
        return "run_task_restart_evidence", "D", "retain_pending_run_context_review"
    if all(x.endswith("/config.json") or x.split("/")[-1].endswith("-config-max-attempts-2.json")
           or (x.startswith("data/validation/") and x.endswith(".json"))
           for x in paths):
        return "run_configuration_or_replay_evidence", "D", "retain_pending_run_context_review"
    return "historical_cross_run_source", "D", "retain_pending_source_review"


def build():
    entries = collect_main_tree()
    by_path = {e["path"]: e for e in entries}
    by_sha = collections.defaultdict(list)
    for e in entries:
        by_sha[e["git_blob_sha1"]].append(e)

    duplicates = []
    for sha, group in sorted(by_sha.items()):
        if len(group) == 1:
            continue
        paths = sorted(x["path"] for x in group)
        role, protection, decision = classify_blob(paths)
        size = group[0]["bytes"]
        duplicates.append({
            "group_id": f"DUP-{len(duplicates) + 1:03d}",
            "source_main_sha": BASE_MAIN_SHA,
            "git_blob_sha1": sha,
            "path_count": len(paths),
            "additional_checkout_paths": len(paths) - 1,
            "blob_bytes": size,
            "theoretical_repeated_worktree_bytes": size * (len(paths) - 1),
            "source_context_kind": role,
            "protection_class": protection,
            "disposition": decision,
            "owner_deletion_approval": "not_granted",
            "paths_semicolon": ";".join(paths),
        })

    triage = list(csv.DictReader(io.StringIO(
        read_source("data/research_storage_triage.csv").decode("utf-8"))))
    if len(triage) != 46:
        raise ValueError("46 historical review records expected")
    retained = []
    for record in triage:
        path = record["path"]
        if path not in by_path:
            raise ValueError("legacy review source disappeared: " + path)
        if by_path[path]["git_blob_sha1"] != record["git_blob_sha1"]:
            raise ValueError("legacy review source blob changed: " + path)
        if record["disposition"] != "retain_pending_source_context_review":
            raise ValueError("original review disposition unexpectedly changed: " + path)
        retained.append({
            "review_id": record["review_id"],
            "source_main_sha": BASE_MAIN_SHA,
            "path": path,
            "git_blob_sha1": record["git_blob_sha1"],
            "bytes": by_path[path]["bytes"],
            "original_review_class": record["review_class"],
            "original_content_kind": record["source_content_kind"],
            "existing_text_ref_count": record["exact_path_text_ref_count"],
            "markdown_ref_count": record["markdown_resolved_ref_count"],
            "same_blob_other_count": record["same_blob_other_count"],
            "action": record["followup_action"],
            "current_disposition": "retain_pending_source_context_review",
            "moved_or_deleted": "false",
            "owner_approval_to_remove": "not_granted",
        })

    doc_rows = []
    for file in entries:
        path = file["path"]
        if not path.startswith("docs/"):
            continue
        group = group_doc(path)
        doc_rows.append({
            "source_main_sha": BASE_MAIN_SHA,
            "path": path,
            "git_blob_sha1": file["git_blob_sha1"],
            "bytes": file["bytes"],
            "group": group,
            "original_heading": source_title(path),
            "status": "current_reference" if group == "current_reference" else "dated_source",
            "original_path_preserved": "true",
            "proposed_physical_move": "none",
            "move_approved": "false",
        })
    if len(doc_rows) != 56:
        raise ValueError("Step 1 expected 56 docs under main")

    result = {}
    for path, rows in ((DOC_CSV, doc_rows), (DUP_CSV, duplicates), (TRIAGE_CSV, retained)):
        result[path] = format_csv(rows, list(rows[0]))

    groups = collections.Counter(r["group"] for r in doc_rows)
    classes = collections.Counter(r["original_review_class"] for r in retained)
    kinds = collections.Counter(r["source_context_kind"] for r in duplicates)
    repeated_bytes = sum(r["theoretical_repeated_worktree_bytes"] for r in duplicates)
    summary = {
        "phase": "Phase 2",
        "source_main_sha": BASE_MAIN_SHA,
        "source_main_tracked_files": len(entries),
        "source_main_document_count": len(doc_rows),
        "document_group_counts": dict(sorted(groups.items())),
        "identical_blob_groups": len(duplicates),
        "same_blob_extra_paths": sum(r["additional_checkout_paths"] for r in duplicates),
        "duplicate_source_context_kinds": dict(sorted(kinds.items())),
        "same_blob_theoretical_repeated_worktree_bytes": repeated_bytes,
        "same_blob_git_history_pack_saving_claim": "none; identical Git blobs already deduplicated by content addressing",
        "retention_review_records": len(retained),
        "retention_review_classes": dict(sorted(classes.items())),
        "retention_existing_blob_unchanged": True,
        "source_files_moved_or_deleted": 0,
        "owner_deletion_approvals": 0,
        "source_limited_to": ["origin/main pinned SHA; Git tracked tree", 
                              "data/research_storage_triage.csv review metadata",
                              "the first heading of 56 docs"],
        "not_claimed": ["git_history_exhaustive_audit", "source_semantics_fully_reviewed",
                        "no_dynamic_dependencies", "approval_to_delete",
                        "RF_new_simulation", "all_CI_regressions_pass"],
        "files": {"documents": DOC_CSV, "duplicate_groups": DUP_CSV,
                  "retention_46": TRIAGE_CSV, "history_index": ARCHIVE_MD,
                  "report": REPORT},
    }
    result[SUMMARY] = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"

    lines = [
        "# 歴史資料・研究記録の案内 — 2026-10-17（Phase 2）", "",
        "> **非破壊の仮想フォルダ索引。** 旧文書の本体を本ディレクトリに移動していない。"
        "元の相対パス／Git blob SHAを保存し、条件・作成日・出典を確認して読む。"
        "現行正式制約は [RF-F003](../../data/constraints/formal/RF-F003.json)。"
        "参照する際は制約レジストリ上のactive IDを優先する。",
        "",
        "**最新の正式仕様を確認する場合：** "
        "[制約台帳](../../data/constraints/registry.json)、"
        "[現行仕様要約](../specification.md)、"
        "[保存パレート](../pareto_rf_t005_rf_f003_20261017.md)。"
        "旧RF-F002、RF-T004、RF-T003の成果をRF-F003へ置き換えない。",
        "",
        f"監査基準main: `{BASE_MAIN_SHA}`。元`docs/`配下は**{len(doc_rows)}件**。"
        "以下は実ファイルの所在を提示する索引であり、移動・改名済みの意味ではない。",
        "",
    ]
    for group in GROUP_NAMES:
        contents = [r for r in doc_rows if r["group"] == group]
        lines += [f"## {GROUP_NAMES[group]}（{len(contents)}件）", ""]
        if group == "current_reference":
            lines += ["これらは現行の入口・正本に関係する文書。**archiveへ移動する候補ではない**。", ""]
        if group == "governance_and_provenance":
            lines += ["過去の提案、PR状態、旧条件を含む。すべてが導入済みとは限らない。", ""]
        if group == "methods_and_theory":
            lines += ["理論・方法・実装計画の出典。計算実行と物理検証の有無は各原文で確認。", ""]
        for row in contents:
            relative = posixpath.relpath(row["path"], "docs/archive")
            title = row["original_heading"].replace("[", "［").replace("]", "］")
            lines.append(f"- [{title}]({relative}) — `{row['path']}`")
        lines.append("")

    lines += [
        "## 個別証拠の追跡と履歴復旧", "",
        "- [56件の文書分類台帳](../../data/repository_reviews/step4_historical_documents_20261017.csv)"
        " は元path、Git blob SHAと仮分類を保持する。",
        "- [同一内容34グループ](../../data/repository_reviews/step4_identical_blob_groups_20261017.csv)"
        " および [要レビュー46件](../../data/repository_reviews/step4_retention_46_20261017.csv)"
        " は削除の候補リストではなく、重複の意味を明示する保全台帳。",
        "- [Step 4保全評価報告](../phase2_repository_step4_review_20261017.md)"
        " に条件別の保持判断と検証の限界をまとめた。",
        "- [旧Gitコミットからの復旧手順](../historical_results.md)"
        " と [2026-10-14ブランチ整理記録](../maintenance/branch_cleanup_20261014.md)"
        " は当時の出典に基づく。2026-10-17時点で新たなbranch削除はしていない。",
        "", "**Phase 2を継続。Phase 3へは所有者の明示承認まで移行しない。**", "",
    ]
    result[ARCHIVE_MD] = "\n".join(lines)

    report = [
        "# Step 4：歴史資料・重複証拠の分類レビュー（2026-10-17）", "",
        "> **監査と導線整理のみ実行。原研究資料の物理移動・削除なし。**"
        " 本書は所有者の削除承認ではない。Phase 2を継続し、Phase 3は未承認。",
        "", f"対象main: `{BASE_MAIN_SHA}`（全{len(entries)}追跡ファイル）。"
        " 差分PRは元mainのデータを変更せず、派生の目次・台帳を追加した。", "",
        "## 1. 歴史文書の区分", "",
        "| 分類 | 件数 | 取り扱い |", "|---|---:|---|",
    ]
    for group in GROUP_NAMES:
        report.append(f"| {GROUP_NAMES[group]} | {groups[group]} | 元pathを保管し"
                      + ("、現行正本として参照 |" if group == "current_reference" else "、分類目次で案内 |"))
    report += [
        "", "現行正式RF-F003と試験RF-T005への閲覧導線は"
        " [パレート](pareto_rf_t005_rf_f003_20261017.md)と"
        " [制約台帳](../data/constraints/registry.json)を先頭にする。"
        " 旧RF-T003/F002/T004や理論研究と混同しない。"
        " 全56文書の分類は[CSV](../data/repository_reviews/step4_historical_documents_20261017.csv)、"
        "人間向け目次は[docs/archive/README](archive/README.md)に保存。", "",
        "## 2. 同一Git blob 34グループ／追加path 38件", "",
        "| 出典上の役割（仮分類） | グループ数 | 処置 |",
        "|---|---:|---|",
    ]
    for role, count in sorted(kinds.items()):
        report.append(f"| `{role}` | {count} | 原パス保持・消去せず個別レビュー |")
    report += [
        "", f"Git同内容グループ：**{len(duplicates)}**、追加path："
        f"**{sum(r['additional_checkout_paths'] for r in duplicates)}**。"
        f"重複パスのcheckout上の最大理論バイト合計は**{repeated_bytes:,} B**"
        "（同内容だけに基づく上界の参考値）。Gitの同一blobはcontent-addressedで既に共有されるため、"
        "**この数値をGit pack容量の削減見込みに使用してはならない**。",
        "",
        "- `data/constraints/formal/RF-F003.json`と`data/design_constraints.json`:"
        " 同一blobだが正本＋互換コピーであり**両方を保持**。",
        "- `EXP-020/source_pr38/`にある同一blob:"
        " 原PR出典の復旧性と当時のコンテキストを優先して保持。",
        "- `logs/`、`tasks/`、各`config.json`:"
        " 失敗／再開／並列ベンチの再現に重要な可能性があり、同じSHAでも条件と意味が異なる。",
        "- `code_snapshot/`と現行スクリプト:"
        " 実行時のコード指紋を保護。自動リンク置換や重複除去を禁止。",
        "- `EXP-012/search_cost.py`と`EXP-013/model013.py`:"
        " 同一blobでも実験系譜・実行時点を確認するまで双方保持。",
        "",
        "[同一blob台帳CSV](../data/repository_reviews/step4_identical_blob_groups_20261017.csv)"
        "にはSHA、全paths、サイズ、仮分類、現在の保全処置を記録する。",
        "",
        "## 3. 過去の46件保全レビュー", "",
        f"全**{len(retained)}件**は旧台帳と同じGit blob SHAで現mainに存在。",
        "",
        "| 既存レビュー区分 | 件数 |",
        "|---|---:|",
    ]
    for key, count in sorted(classes.items()):
        report.append(f"| `{key}` | {count} |")
    report += [
        "", "旧台帳の全件`retain_pending_source_context_review`を引き継いだ。"
        "Markdownからの参照、PR source、同一blob、独立検証・実行復旧上の役割は"
        "ファイル内容と関連実験の証拠が揃うまで確定できない。",
        "[46件の照合台帳](../data/repository_reviews/step4_retention_46_20261017.csv)"
        " と [元の2026-10-15の出典レビュー](phase2_evidence_triage_20261015.md)を参照。",
        "",
        "## 4. 現段階での保全判断と承認ゲート", "",
        "1. **即時変更：文書の閲覧索引・再生成可能な監査台帳のみ**。元文書、元実験、"
        "元S2P、元制約、Git branches、元checkpointは移動・改変・削除しない。",
        "2. **継続レビュー：同一blobの各出典／46要レビュー件**。削除対象確定ではない。"
        "個別に元コード参照、run ID、PRとGit履歴の復元、SHA、"
        "相対リンク・CIを点検した後、所有者の明示承認を要する。",
        "3. **別PRで扱う：新しい文書ディレクトリへ元ファイルを動かす場合**。"
        "依存参照とblob一致、使用例、履歴・旧ブランチを調査し、元パスも追跡可能にする。",
        "4. **Step 5ゲート：既存Phase 2 regression全体のPASS**。"
        "EXP-047 manifestの既知問題は本整理作業で修正しない。"
        "本Step 4専用監査のPASSと全体CIのPASSは別。",
        "",
        "## 5. 再実行と限界", "",
        "```bash",
        "git fetch origin main",
        "python scripts/audit_repository_reorganization_step4.py --check",
        "```",
        "",
        "本監査は指定mainの追跡tree、保存済み46件台帳、"
        "文書の先頭見出しを使う一次分類であり、"
        "**本文の意味全体、全Git履歴、未追跡出力、動的パス参照の完全調査ではない**。"
        "日付や保存時点の「現在」は現行正式条件を意味しない。"
        "新たなRFシミュレーション・回路最適化・物理検証を行っていない。",
        "",
    ]
    result[REPORT] = "\n".join(report)
    return result, summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true",
                   help="compare generated evidence reviews with checked-in files")
    args = p.parse_args()
    result, summary = build()
    for path, content in result.items():
        dest = ROOT / path
        if args.check:
            if not dest.is_file() or dest.read_text(encoding="utf-8") != content:
                raise SystemExit("STALE Step 4 review: " + path)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
    print(json.dumps({
        "main_sha": summary["source_main_sha"],
        "main_docs": summary["source_main_document_count"],
        "same_blob_groups": summary["identical_blob_groups"],
        "same_blob_extra_paths": summary["same_blob_extra_paths"],
        "retention_reviews": summary["retention_review_records"],
        "originals_deleted_or_moved": summary["source_files_moved_or_deleted"],
        "outputs": list(result), "mode": "check" if args.check else "generate",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
