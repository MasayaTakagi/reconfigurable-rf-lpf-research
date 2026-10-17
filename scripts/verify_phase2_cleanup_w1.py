#!/usr/bin/env python3
"""Phase 2 W1 current-document and tracked-Markdown static link regression.

Audits the checked-out PR tree, unlike the pinned W0 historical inventory.
No deletion, Git write, experiment replay or external-link availability claim.
"""
from __future__ import annotations

import csv
import json
import posixpath
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MD_LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
MD_REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)")
HTML_REFERENCE = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""")
EXPECTED_BASE_SHA = "055b222c79c73c7fbeacb19383f21c1da0625195"
CURRENT_PATHS = (
    "README.md",
    "docs/roadmap.md",
    "docs/current/open_research_questions.md",
    "docs/current/phase2_status.md",
    "docs/results/README.md",
    "data/README.md",
    "scripts/README.md",
    "experiments/README.md",
)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def resolve(raw, source, tracked):
    dest = raw.strip()
    if dest.startswith("<") and ">" in dest:
        dest = dest[1:dest.index(">")]
    else:
        dest = dest.split(" ", 1)[0]
    if not dest:
        return "", "empty"
    if dest.startswith("#"):
        return source, "anchor_unverified"
    if dest.startswith(("//", "mailto:", "tel:", "data:")):
        return "", "external_unverified"
    parsed = urlsplit(dest)
    if parsed.scheme or parsed.netloc:
        return "", ("github_url_unverified" if "github.com" in parsed.netloc
                    else "external_unverified")
    rawpath = unquote(parsed.path)
    if not rawpath:
        return source, "anchor_unverified"
    normal = posixpath.normpath(
        rawpath.lstrip("/") if rawpath.startswith("/")
        else posixpath.join(posixpath.dirname(source), rawpath))
    if normal in {"..", "."} or normal.startswith("../"):
        return normal, "outside_repository"
    if normal in tracked:
        return normal, "exists_anchor_unverified" if parsed.fragment else "exists"
    if any(p.startswith(normal.rstrip("/") + "/") for p in tracked):
        return normal, "directory_exists"
    return normal, "missing"


def scan_links(tracked):
    counts = {}
    issues = []
    total_links = 0
    markdown_count = 0
    for path in sorted(p for p in tracked if p.endswith((".md", ".markdown", ".mdx"))):
        markdown_count += 1
        body = (ROOT / path).read_text(encoding="utf-8")
        fence = None
        for lineno, rawline in enumerate(body.splitlines(), 1):
            line = rawline.lstrip()
            if fence:
                if re.match(re.escape(fence[0]) + "{" + str(fence[1]) + ",}", line):
                    fence = None
                continue
            match = re.match(r"(" + re.escape(chr(96)) + r"{3,}|~{3,})", line)
            if match:
                fence = (match.group(1)[0], len(match.group(1)))
                continue
            # Same extraction scope as W0; Markdown nested links, URL
            # availability, anchors and inline-code false positives remain
            # outside the full validation guarantee.
            refs = [m.group(1) for m in MD_LINK.finditer(rawline)]
            definition = MD_REFERENCE.match(rawline)
            if definition:
                refs.append(definition.group(1))
            refs += [m.group(1) for m in HTML_REFERENCE.finditer(rawline)]
            for dest in refs:
                normal, status = resolve(dest, path, tracked)
                counts[status] = counts.get(status, 0) + 1
                total_links += 1
                if status in {"missing", "outside_repository", "empty"}:
                    issues.append({
                        "source": path, "line": lineno, "target": dest,
                        "resolved": normal, "status": status,
                    })
    return markdown_count, total_links, counts, issues


def current_state_guardrails():
    top = (ROOT / "README.md").read_text(encoding="utf-8").split(
        "## 2026-10-15時点の研究状況", 1)[0]
    rm = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split(
        "## 2026-10-17以前の計画・進捗", 1)[0]
    current = (ROOT / "docs/current/open_research_questions.md").read_text(encoding="utf-8")
    results = (ROOT / "docs/results/README.md").read_text(encoding="utf-8")
    data = (ROOT / "data/README.md").read_text(encoding="utf-8")
    scripts = (ROOT / "scripts/README.md").read_text(encoding="utf-8")
    exp = (ROOT / "experiments/README.md").read_text(encoding="utf-8")
    required = {
        "root current integrated PR": (top, "統合済みPR #71"),
        "root latest 24": (top, "24件"),
        "roadmap 24": (rm, "24候補"),
        "roadmap repaired CI": (rm, "39028160775"),
        "research questions historical repair": (current, "39028160775"),
        "research questions remaining provenance": (current, "seed"),
        "results catalog": (results, "phase2_candidate_catalog_20261017.csv"),
        "data catalog": (data, "phase2_candidate_catalog_20261017.csv"),
        "scripts --catalog": (scripts, "--catalog"),
        "experiments original unchanged": (exp, "元manifest"),
    }
    for name, (text, token) in required.items():
        if token not in text:
            raise AssertionError("W1 current documentation not updated: " + name)
    stale_snippets = (
        "最新10点は未統合", "新パレート10点は未統合",
        "全回帰PASSしていない", "全CI PASSは未成立",
        "現行RF-F003/T005の10点と旧14件候補台帳が別管理",
    )
    for tag, text in (("root current", top), ("roadmap current", rm),
                      ("open questions", current), ("results", results),
                      ("data", data), ("scripts", scripts), ("experiments", exp)):
        for bad in stale_snippets:
            if bad in text:
                raise AssertionError("W1 stale active status: " + tag + ": " + bad)
    original = (ROOT / "experiments/chatgpt_topology_search/runs/EXP-004/README.md").read_text()
    if "(../../../../actions/workflows/lpf-target040.yml)" not in original:
        raise AssertionError("EXP-004 immutable source no longer matches historic link evidence")
    # The original README is manifest-hash-pinned and MUST NOT be patched.
    # Provide a verified working URL only in an editable navigation document.
    overview = (ROOT / "experiments/README.md").read_text(encoding="utf-8")
    if "https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/workflows/lpf-target040.yml" not in overview:
        raise AssertionError("Working URL missing from experiments navigation")
    if "保全例外" not in overview:
        raise AssertionError("Known source-immutable broken link not disclosed")
    if ".github/workflows/lpf-target040.yml" not in git("ls-files").decode():
        raise AssertionError("referenced source workflow does not exist")


def protection_guardrails():
    for path in ("data/bands.csv", "data/constraints/registry.json",
                 "data/constraints/formal/RF-F003.json",
                 "data/constraints/trial/RF-T005.json",
                 "data/design_constraints.json",
                 "data/parasitics/circuit1_ant_coupler_0_6ghz.s2p",
                 "data/parasitics/circuit2_poc_through_0_6ghz.s2p",
                 "experiments/chatgpt_topology_search/runs/EXP-047/manifest.json"):
        orig = git("rev-parse", EXPECTED_BASE_SHA + ":" + path).decode().strip()
        cur = git("hash-object", str(ROOT / path)).decode().strip()
        if orig != cur:
            raise AssertionError("Original protected research blob changed: " + path)
    with (ROOT / "data/repository_reviews/step4_retention_46_20261017.csv").open(
            newline="", encoding="utf-8") as f:
        protected = list(csv.DictReader(f))
    if len(protected) != 46:
        raise AssertionError("Protected source index length differs from 46")
    for row in protected:
        p = row["path"]
        if not (ROOT / p).is_file() or git("hash-object", str(ROOT / p)).decode().strip() != row["git_blob_sha1"]:
            raise AssertionError("Original pending research evidence changed: " + p)
    return len(protected)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", default="")
    args = parser.parse_args()
    tracked = set(p for p in git("ls-files", "-z").decode().split("\0") if p)
    markdown_count, link_count, statuses, problems = scan_links(tracked)
    current_state_guardrails()
    retained = protection_guardrails()
    known_immutable_link = {
        "source": "experiments/chatgpt_topology_search/runs/EXP-004/README.md",
        "target": "../../../../actions/workflows/lpf-target040.yml",
        "status": "missing",
    }
    waived = [p for p in problems
              if (p["source"], p["target"], p["status"]) ==
              (known_immutable_link["source"], known_immutable_link["target"],
               known_immutable_link["status"])]
    remaining = [p for p in problems if p not in waived]
    if len(waived) != 1:
        raise AssertionError("Manifest-pinned EXP-004 historic broken link count differs from one")
    summary = {
        "phase": "Phase 2",
        "scope": "checked-out W1 worktree; 2026-10-17 fixed W0 base",
        "original_main": EXPECTED_BASE_SHA,
        "total_tracked_paths_in_w1_worktree": len(tracked),
        "markdown_documents_scanned": markdown_count,
        "markdown_links_extracted": link_count,
        "status_counts": dict(sorted(statuses.items())),
        "broken_local_markdown_links": problems,
        "unresolved_because_immutable_historical_source": len(waived),
        "unresolved_unexpected_links": len(remaining),
        "known_historical_exception": known_immutable_link,
        "protected_original_blob_checks": 8,
        "retained_46_sha_validated": retained,
        "historical_exp004_workflow_source_exists": True,
        "source_deletions": 0,
        "caveats": [
            "Markdown regex scope; not full nested destination or HTML/anchors verification",
            "GitHub URL reachability not checked; user should open Actions link",
            "CI and structural checks are not new RF simulation/physical evidence",
        ],
    }
    if args.summary:
        out = ROOT / args.summary
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "tracked": len(tracked), "markdown": markdown_count, "links": link_count,
        "issues": len(problems), "waived_original_immutable": len(waived),
        "unexpected_issues": len(remaining), "retained": retained,
        "states": dict(sorted(statuses.items())),
    }, ensure_ascii=False))
    if remaining:
        raise SystemExit("W1 unexpected broken tracked Markdown links: " +
                         json.dumps(remaining[:15], ensure_ascii=False))


if __name__ == "__main__":
    main()
