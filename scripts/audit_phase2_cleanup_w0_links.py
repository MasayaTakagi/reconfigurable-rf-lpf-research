#!/usr/bin/env python3
"""W0 complementary full-Markdown and deletion-risk review at pinned main."""
import argparse
import collections
import csv
import io
import json
import posixpath
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = "055b222c79c73c7fbeacb19383f21c1da0625195"
PREFIX = "data/repository_reviews/w0_cleanup_20261017_"
CANDIDATES = "data/repository_reviews/phase2_cleanup_deletion_candidates_20261017.csv"
LINK = re.compile(r"!?\[[^\]\n]+\]\(([^)\n]+)\)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)")
HTML = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""")


def at_main(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", BASE + ":" + path]).decode("utf-8", "replace")


def read_csvs(glob_pattern):
    rows = []
    for p in sorted(ROOT.glob(glob_pattern)):
        with p.open(newline="", encoding="utf-8") as stream:
            rows += list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Missing CSV inputs: " + glob_pattern)
    return rows


def to_csv(rows, fields):
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue()


def resolve(raw, source, known):
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1:value.index(">")]
    else:
        value = value.split(" ", 1)[0]
    if value.startswith("#"):
        return source, "anchor_unchecked"
    if not value:
        return "", "empty"
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or value.startswith("//"):
        return "", "external_or_github_url_unchecked"
    target = unquote(parts.path)
    if not target:
        return source, "anchor_unchecked"
    target = posixpath.normpath(target.lstrip("/") if target.startswith("/")
                                else posixpath.join(posixpath.dirname(source), target))
    if target == ".." or target.startswith("../"):
        return target, "outside_repository"
    if target in known:
        return target, "exists_anchor_unchecked" if parts.fragment else "exists"
    if any(p.startswith(target.rstrip("/") + "/") for p in known):
        return target, "directory_exists"
    return target, "missing"


def make():
    inventory = read_csvs("data/repository_audits/w0_20261017_files_*.csv")
    edges = read_csvs("data/repository_audits/w0_20261017_references_*.csv")
    summary0 = json.loads((ROOT / "data/repository_audits/w0_20261017_summary.json").read_text())
    if summary0["main_sha"] != BASE:
        raise ValueError("Unexpected W0 baseline commit")
    known = {r["path"]: r for r in inventory}
    md_paths = sorted(p for p in known if p.endswith((".md", ".markdown", ".mdx")))
    md_contents = {}
    mdlinks = []
    for path in md_paths:
        body = at_main(path)
        md_contents[path] = body
        fenced = None
        for number, line in enumerate(body.splitlines(), 1):
            stripped = line.lstrip()
            if fenced:
                if re.match(re.escape(fenced[0]) + "{" + str(fenced[1]) + ",}", stripped):
                    fenced = None
                continue
            marker = re.match(r"(\x60{3,}|~{3,})", stripped)
            if marker:
                fenced = (marker.group(1)[0], len(marker.group(1)))
                continue
            matches = [("inline", m.group(1)) for m in LINK.finditer(line)]
            definition = REFERENCE.match(line)
            if definition:
                matches.append(("reference_definition", definition.group(1)))
            matches += [("html_href", m.group(1)) for m in HTML.finditer(line)]
            for kind, raw in matches:
                target, status = resolve(raw, path, known)
                mdlinks.append(dict(source=path, line=number, kind=kind,
                                    raw_destination=raw, resolved_path=target, status=status))
    mdlinks.sort(key=lambda x: (x["source"], x["line"], x["raw_destination"]))
    m_in = collections.defaultdict(set)
    for row in mdlinks:
        if row["resolved_path"] in known and row["resolved_path"] != row["source"]:
            m_in[row["resolved_path"]].add(row["source"])
    s_in = collections.defaultdict(set)
    for row in edges:
        if row["kind"] != "markdown" and row["target"] in known:
            s_in[row["target"]].add(row["source"])
    cs = read_csvs(CANDIDATES)
    if len(cs) != 23:
        raise ValueError("Expected 23 plan candidate decisions")
    old46 = read_csvs("data/repository_reviews/step4_retention_46_20261017.csv")
    if len(old46) != 46 or any(known[x["path"]]["git_blob_sha1"] != x["git_blob_sha1"] for x in old46):
        raise ValueError("Original 46 protection records have changed")
    flows = sorted(p for p in known if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")))
    workflow_text = {p: at_main(p) for p in flows}
    decisions = []
    for c in cs:
        path = c["source_path_or_scope"]
        source = known.get(path)
        if source and source["git_blob_sha1"] != c["source_git_blob_sha1_at_planning"]:
            raise ValueError("Source SHA drift: " + path)
        basename = posixpath.basename(path.rstrip("/"))
        weaker = sorted(p for p, text in md_contents.items()
                       if p != path and basename in text and p not in m_in[path])
        flow_refs = sorted(p for p, text in workflow_text.items() if path in text or basename in text)
        decisions.append({
            "candidate_id": c["candidate_id"], "workstream": c["workstream"],
            "source_path": path, "source_sha": source["git_blob_sha1"] if source else "",
            "source_bytes": source["bytes"] if source else "",
            "markdown_inbound": ";".join(sorted(m_in[path])),
            "other_static_path_inbound": ";".join(sorted(s_in[path])),
            "basename_mentions_unverified": ";".join(weaker),
            "workflow_mentions_unverified": ";".join(flow_refs),
            "recommendation": "retain_pending_individual_review",
            "delete_approval": "not_granted", "deleted": "false",
            "followup": c["before_deletion_checks"],
        })
    unresolved = [x for x in mdlinks if x["status"] in ("missing", "outside_repository", "empty")]
    j = {
        "phase": "Phase 2", "operation": "W0 read-only audit",
        "base_main_sha": BASE, "tracked_paths": len(known),
        "tracked_bytes": summary0["tracked_bytes"],
        "scanned_markdown_files": len(md_paths),
        "markdown_links": len(mdlinks),
        "unresolved_local_link_candidates": len(unresolved),
        "markdown_link_status_counts": dict(sorted(collections.Counter(x["status"] for x in mdlinks).items())),
        "scanned_workflow_files": len(flows),
        "existing_static_reference_edges": len(edges),
        "deletion_document_candidates": sum(x["candidate_id"].startswith("D-") for x in cs),
        "review_candidate_rows": len(cs), "protected_old_files_verified": len(old46),
        "same_blob_groups": summary0["same_blob_groups"],
        "same_blob_extra_paths": summary0["same_blob_extra_paths"],
        "owner_approved_deletions": 0, "executed_deletions": 0,
        "limitations": ["Pinned main at original W0 start; not full Git history.",
                        "Markdown regex excludes fenced code but may include inline-code fixtures.",
                        "Nested link destinations, fragments, anchors, GitHub URLs and external sites not fully checked.",
                        "Dynamic Python/YAML paths and untracked experiment outputs not fully discoverable.",
                        "Exact links, static references and basename mentions differ in confidence.",
                        "Original source uniqueness and owner deletion approval not established."],
    }
    outputs = {
        PREFIX + "markdown_links.csv": to_csv(mdlinks, ["source", "line", "kind", "raw_destination", "resolved_path", "status"]),
        PREFIX + "deletion_decisions.csv": to_csv(decisions, ["candidate_id", "workstream", "source_path", "source_sha",
            "source_bytes", "markdown_inbound", "other_static_path_inbound",
            "basename_mentions_unverified", "workflow_mentions_unverified", "recommendation",
            "delete_approval", "deleted", "followup"]),
        PREFIX + "summary.json": json.dumps(j, ensure_ascii=False, indent=2) + "\n",
    }
    report = [
        "# Phase 2 W0：全追跡ファイル・リンク・削除候補監査",
        "", "状態：監査実行済み、元研究ファイル削除0件。Phase 2を継続する。",
        "基準main commit: " + BASE,
        "",
        "## 基準mainの計数", "",
        "| 監査 | 結果 |", "|---|---:|",
        "| 追跡ファイル | " + str(len(known)) + " |",
        "| 非圧縮bytes | " + str(summary0["tracked_bytes"]) + " |",
        "| Markdownファイル | " + str(len(md_paths)) + " |",
        "| Markdownリンク抽出 | " + str(len(mdlinks)) + " |",
        "| 未解決ローカルリンク候補 | " + str(len(unresolved)) + " |",
        "| workflow YAMLファイル | " + str(len(flows)) + " |",
        "| 全文静的参照辺 | " + str(len(edges)) + " |",
        "| 同一blob | " + str(summary0["same_blob_groups"]) + "組・追加" + str(summary0["same_blob_extra_paths"]) + "path |",
        "| 旧保全46件 | SHA一致46件 |",
        "| 実削除 | 0件 |",
        "", "## 未解決リンク候補", "",
        "Markdownリンクの正規表現抽出。実際の欠落かコード例由来かはW1で手動判定。",
        "外部GitHub URLの実際の到達性とアンカーは確認していない。", "",
    ]
    if unresolved:
        report += ["| 文書 | 行 | 内容 | 状態 |", "|---|---:|---|---|"]
        for row in unresolved[:25]:
            report.append("| " + row["source"] + " | " + str(row["line"]) +
                          " | " + row["raw_destination"].replace("|", "/")[:90] +
                          " | " + row["status"] + " |")
        if len(unresolved) > 25:
            report.append("残り" + str(len(unresolved)-25) + "件は機械可読CSV参照。")
    else:
        report.append("抽出範囲の未解決リンク候補なし。アンカー・動的リンクの全保証ではない。")
    report += [
        "", "## 削除候補D-001～D-007（リンク元一覧はCSV）", "",
        "| 候補 | path | Markdownリンク出典 | その他静的path出典 | 扱い |",
        "|---|---|---:|---:|---|",
    ]
    for x in decisions:
        if not x["candidate_id"].startswith("D-"):
            continue
        count = lambda key: len(x[key].split(";")) if x[key] else 0
        report.append("| " + x["candidate_id"] + " | " + x["source_path"] + " | " +
                      str(count("markdown_inbound")) + " | " +
                      str(count("other_static_path_inbound")) +
                      " | 独自情報と出典の審査待ち、削除不可 |")
    report += [
        "", "## 次工程と限界", "",
        "- W1：現行説明の旧状態を訂正し、抽出されたローカルリンク候補を手動確認する。",
        "- W3：削除候補ごとの固有数値・実行状況・元PR/コミットと文書移設先を確認する。",
        "- 既存46要レビュー資料は元のGit blob SHA一致を確認しただけで、削除可能なことを意味しない。",
        "- Gitの過去コミットからの復元と、現行スクリプト・READMEの参照互換性は別問題。",
        "- 入力は固定mainの追跡tree。Git履歴全体・未追跡成果・動的参照を網羅していない。",
        "", "詳細：data/repository_audits/w0_20261017_summary.json、",
        "data/repository_reviews/w0_cleanup_20261017_summary.json、",
        "data/repository_reviews/w0_cleanup_20261017_markdown_links.csv、",
        "data/repository_reviews/w0_cleanup_20261017_deletion_decisions.csv。", "",
    ]
    outputs["docs/phase2_cleanup_w0_current_main_audit_20261017.md"] = "\n".join(report)
    return outputs, j


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result, overview = make()
    for rel, data in result.items():
        p = ROOT / rel
        if args.check:
            if not p.exists() or p.read_text(encoding="utf-8") != data:
                raise SystemExit("W0 output missing or stale: " + rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(data, encoding="utf-8")
    print(json.dumps({"status": "check" if args.check else "generated",
                      "files": overview["tracked_paths"], "md": overview["scanned_markdown_files"],
                      "unresolved": overview["unresolved_local_link_candidates"],
                      "deletions": overview["executed_deletions"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
