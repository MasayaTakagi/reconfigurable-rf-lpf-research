#!/usr/bin/env python3
"""W3 approved-deletion gate: exact four-doc allowlist, historical recovery and no source loss.

Check removal against pinned pre-deletion main. Raw experiment evidence and
the 46 previously reviewed source blobs must remain byte-identical.
External links, dynamic paths and all Git history are not fully audited.
"""
import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRE_DELETE = "88562135dae2edf8ba7763aa529181c05f7c1ded"
INITIAL_W3_REVIEW = "731e901e79cfa367fd06b4350844c6987b30caa5"
REVIEW = ROOT / "data/repository_reviews/w3_document_disposition_20261017.csv"
PLAN = ROOT / "data/repository_reviews/phase2_cleanup_deletion_candidates_20261017.csv"
OLD_PROTECTED = ROOT / "data/repository_reviews/step4_retention_46_20261017.csv"
HISTORY = ROOT / "docs/archive/w3_consolidated_documents_20261017.md"
APPROVED_IDS = {"D-%03d" % i for i in range(1, 5)}
RETAINED_IDS = {"D-%03d" % i for i in range(5, 8)}
EXPECTED_IDS = APPROVED_IDS | RETAINED_IDS
PROTECTED_PREFIXES = (
    "data/constraints/", "data/parasitics/", "data/validation/",
    "experiments/", "candidates/",
)
PROTECTED_FILES = {
    "data/design_constraints.json", "data/bands.csv",
    "data/experiment_number_registry.csv",
}


def git(*args, text=True):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=text)


def require_original(relpath, source_sha, *, removed):
    rel = Path(relpath)
    assert not rel.is_absolute() and ".." not in rel.parts and relpath.startswith(("docs/", "data/", "experiments/", "candidates/"))
    expected_git_blob = git("rev-parse", PRE_DELETE + ":" + relpath).strip()
    assert source_sha == expected_git_blob, "Pre-delete source hash mismatch: " + relpath
    recovered = git("show", PRE_DELETE + ":" + relpath, text=False)
    actual_blob = subprocess.check_output(
        ["git", "hash-object", "--stdin"], input=recovered, cwd=ROOT
    ).decode().strip()
    assert actual_blob == source_sha, "git show recovery differs: " + relpath
    file = ROOT / relpath
    if removed:
        assert not file.exists() and not file.is_symlink(), "Approved deleted path is still in tree: " + relpath
    else:
        assert file.is_file() and not file.is_symlink(), "Retained file missing: " + relpath
        assert file.read_bytes() == recovered, "Retained source changed: " + relpath


def main():
    with REVIEW.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    items = {row["candidate_id"]: row for row in rows}
    assert len(rows) == 7 and items.keys() == EXPECTED_IDS
    expected_deleted = {items[k]["source_path"] for k in APPROVED_IDS}
    assert len(expected_deleted) == 4
    history_text = HISTORY.read_text(encoding="utf-8")

    for key, row in items.items():
        assert row["review_main_commit"] == INITIAL_W3_REVIEW
        if key in APPROVED_IDS:
            assert row["owner_delete_approval"] == "granted_2026-10-17T14-55-06Z"
            assert row["tree_state"] == "removed_from_current_revision"
            assert row["w3_disposition"] == "approved_removed_after_consolidation"
            assert row["source_path"] in history_text
            assert row["git_blob_sha1"] in history_text
            require_original(row["source_path"], row["git_blob_sha1"], removed=True)
        else:
            assert row["owner_delete_approval"] == "not_granted"
            assert row["tree_state"] == "retained"
            require_original(row["source_path"], row["git_blob_sha1"], removed=False)

    with PLAN.open(newline="", encoding="utf-8") as f:
        planning = {r["candidate_id"]: r for r in csv.DictReader(f)}
    for k in APPROVED_IDS:
        assert planning[k]["execution_state"] in {"removed_from_current_revision_owner_approved_20261017", "removed_after_owner_approval_20261017"}
        assert planning[k]["source_git_blob_sha1_at_planning"] == items[k]["git_blob_sha1"]
    for k in RETAINED_IDS:
        assert planning[k]["execution_state"] == "not_started_unapproved"

    with OLD_PROTECTED.open(newline="", encoding="utf-8") as f:
        protected = list(csv.DictReader(f))
    assert len(protected) == 46
    for row in protected:
        require_original(row["path"], row["git_blob_sha1"], removed=False)

    deleted = set(git("diff", "--diff-filter=D", "--name-only", PRE_DELETE, "HEAD").splitlines())
    assert deleted == expected_deleted, "Unapproved deletion or missing four deletions: " + str(deleted)
    changed = git("diff", "--name-only", PRE_DELETE, "HEAD").splitlines()
    for path in changed:
        assert not path.startswith(PROTECTED_PREFIXES) and path not in PROTECTED_FILES, (
            "Changed protected RF or original research evidence: " + path
        )
    print("W3 PASS: exactly four owner-approved historical documents removed from tree.")
    print("W3 PASS: original four Git blobs byte-for-byte restorable with git show.")
    print("W3 PASS: retained D-005 to D-007, all 46 source documents and RF evidence unchanged.")
    print("Limit: not a complete verification of dynamic paths, all external URLs or full repository history.")


if __name__ == "__main__":
    main()
