#!/usr/bin/env python3
"""Read-only Git-only Phase 2 storage size auditor.

Audits tracked worktree bytes (not .git pack/history). Reviews new files versus
origin/main and warns about curation budgets without changing historical files.
"""
import argparse
import collections
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data/phase2_git_storage_budget.json"


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)


def tracked_paths(root):
    raw = git(root, "ls-files", "--cached", "-z")
    return sorted(p.decode("utf-8") for p in raw.split(b"\0") if p)


def new_paths(root, base_ref):
    git(root, "rev-parse", "--verify", base_ref)
    raw = git(root, "diff", "--diff-filter=A", "--name-only", "-z",
              base_ref + "..HEAD")
    return set(p.decode("utf-8") for p in raw.split(b"\0") if p)


def _scope(path):
    parts = path.split("/")
    if len(parts) >= 5 and parts[:4] == [
        "experiments", "chatgpt_topology_search", "runs", parts[3]]:
        return "experiments/" + parts[3]
    if len(parts) >= 4 and parts[:2] == ["data", "validation"]:
        return "data/validation/" + parts[2]
    if len(parts) >= 2 and parts[0] == "data":
        return "data/other"
    return parts[0]


def _size_report(paths, new_set, sizes, policy):
    lim = policy["thresholds"]
    counts = collections.Counter()
    budgets = collections.Counter()
    reviewed = []
    for path in paths:
        size = sizes[path]
        counts[_scope(path)] += size
        if path in new_set:
            group = _scope(path)
            budgets[group] += size
            if size > lim["individual_new_file_soft_bytes"]:
                reviewed.append({
                    "path": path, "bytes": size, "group": group,
                    "severity": ("hard_limit" if size >
                                 lim["individual_new_file_hard_bytes"] else "review"),
                })
    for group, size in sorted(budgets.items()):
        if group.startswith(("experiments/", "data/validation/")) and (
                size > lim["new_experiment_curated_soft_bytes"]):
            reviewed.append({"group": group, "new_bytes": size, "severity": "group_review"})
    total = sum(sizes[p] for p in paths)
    return {
        "schema_version": 1,
        "phase": "Phase 2",
        "storage_backend": "GitHub Git only",
        "tracked_file_count": len(paths),
        "tracked_uncompressed_bytes": total,
        "size_excludes_git_history": True,
        "total_review_threshold_bytes": lim["total_tracked_bytes_review_bytes"],
        "total_over_review_threshold": total > lim["total_tracked_bytes_review_bytes"],
        "bytes_by_scope": dict(sorted(counts.items())),
        "added_file_count": len(new_set & set(paths)),
        "added_file_bytes": sum(sizes[p] for p in new_set if p in sizes),
        "review_items": reviewed,
        "new_file_hard_limit_violations": [
            x["path"] for x in reviewed if x["severity"] == "hard_limit"],
        "file_deletions": 0,
        "evidence_edits": 0,
        "metadata_notes": [
            "Soft limits signal review; no automatic delete or history rewrite.",
            "Git .git packed repository size requires separate git count-objects audit.",
            "Missing raw search traces cannot be recreated from aggregate run data.",
        ],
    }


def audit(root=ROOT, base_ref="origin/main"):
    root = Path(root)
    policy = json.loads((root / "data/phase2_git_storage_budget.json")
                        .read_text(encoding="utf-8"))
    if policy["storage_backend"] != "GitHub Git only" or policy["external_archive_required"]:
        raise ValueError("Unexpected external storage requirement")
    paths = tracked_paths(root)
    sizes = {}
    for p in paths:
        path = root / p
        if not path.is_file() or path.is_symlink():
            raise ValueError("Tracked source missing or symbolic link: " + p)
        sizes[p] = path.stat().st_size
    added = new_paths(root, base_ref)
    result = _size_report(paths, added, sizes, policy)
    result["base_ref"] = base_ref
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="Fail on new >1MiB Git blobs; only warn on soft size budgets")
    args = parser.parse_args()
    report = audit(base_ref=args.base)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
    print("Phase 2 Git-only capacity", json.dumps({
        "tracked_file_count": report["tracked_file_count"],
        "tracked_bytes": report["tracked_uncompressed_bytes"],
        "new_file_bytes": report["added_file_bytes"],
        "review_count": len(report["review_items"]),
        "hard_limit_count": len(report["new_file_hard_limit_violations"]),
        "total_review_threshold_exceeded": report["total_over_review_threshold"],
        "deletions": report["file_deletions"],
    }, ensure_ascii=False))
    if args.check and report["new_file_hard_limit_violations"]:
        raise SystemExit("FAIL new Git blob exceeds 1MiB without separate owner review")


if __name__ == "__main__":
    main()
