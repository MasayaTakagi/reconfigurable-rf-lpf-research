#!/usr/bin/env python3
"""Non-destructive historical branch-head blob audit; not a deletion permit."""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = "data/branch_retention_review_20261015.csv"
RESEARCH = ("data/validation/", "experiments/", "candidates/")


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)


def tree_blobs(root, ref):
    records = {}
    for record in git(root, "ls-tree", "-rz", "--full-tree", ref).split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, kind, sha = metadata.split()
            if kind == b"blob":
                records[path.decode("utf-8")] = sha.decode("ascii")
    return records


def audit_branches(root=ROOT, main_ref="origin/main"):
    root = Path(root)
    with (root / REGISTER).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    cols = ["branch", "merged_pr", "expected_head_sha", "review_status", "disposition"]
    if not rows or list(rows[0]) != cols:
        raise ValueError("Invalid branch review registry")
    main = tree_blobs(root, main_ref)
    main_blobs = set(main.values())
    main_sha = git(root, "rev-parse", main_ref).decode().strip()
    records, seen = [], set()
    for row in rows:
        branch = row["branch"]
        if (branch in seen or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", branch)
                or ".." in branch or branch.startswith("-")):
            raise ValueError("Duplicate or unsafe branch name")
        seen.add(branch)
        if (not re.fullmatch(r"[0-9a-f]{40}", row["expected_head_sha"])
                or not row["merged_pr"].isdigit()
                or row["review_status"] != "merged_and_head_compared"
                or row["disposition"] != "retain_pending_owner_approval"):
            raise ValueError("Bad provenance or deletion authority in branch ledger")
        ref = "refs/remotes/origin/" + branch
        actual = git(root, "rev-parse", "--verify", ref).decode().strip()
        if actual != row["expected_head_sha"]:
            raise ValueError("Branch head moved after recorded review: " + branch)
        blobs = tree_blobs(root, ref)
        only_on_branch = sorted(p for p, sha in blobs.items() if sha not in main_blobs)
        research = [p for p in only_on_branch if p.startswith(RESEARCH)]
        records.append({
            "branch": branch, "merged_pr": int(row["merged_pr"]),
            "head_sha": actual, "head_files": len(blobs),
            "head_blobs_absent_in_current_main": len(only_on_branch),
            "research_head_blobs_absent_in_current_main": research,
            "nonresearch_head_blobs_absent_in_current_main":
                [p for p in only_on_branch if p not in research],
            "deletion_authorized": False,
        })
    allrefs = git(root, "for-each-ref", "--format=%(refname:short)",
                  "refs/remotes/origin/").decode().splitlines()
    not_reviewed = sorted(
        set(x.removeprefix("origin/") for x in allrefs) - seen - {"main", "HEAD"}
    )
    return {
        "schema_version": 1, "phase": "Phase 2",
        "scope": "HEAD blob identity only; not full Git history",
        "main_sha": main_sha, "reviewed_merged_branches": len(records),
        "branch_records": records, "unreviewed_branches": not_reviewed,
        "all_reviewed_research_blobs_present_in_current_main":
            all(not x["research_head_blobs_absent_in_current_main"] for x in records),
        "deletions_executed": 0,
        "limits": [
            "Squash merge means branch commit may be not an ancestor of main.",
            "Blob match proves bytes only; not equivalent provenance or full history.",
            "An owner-authorized separate delete and verified backup are still necessary.",
            "Merged PR status verified externally and recorded in the static ledger.",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    summary = audit_branches()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    if args.check and not summary["all_reviewed_research_blobs_present_in_current_main"]:
        raise SystemExit("FAIL: A retained historical branch has a research blob absent from main")
    print("PASS branch provenance review:", json.dumps({
        "reviewed": summary["reviewed_merged_branches"],
        "unreviewed": summary["unreviewed_branches"],
        "deleted": summary["deletions_executed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
