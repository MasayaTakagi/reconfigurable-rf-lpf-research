#!/usr/bin/env python3
"""Phase 2 W3 read-only approved deletion gate.

D-001..D-004 were owner-approved for retirement from the current tree.
Validate actual historical byte restoration and the exact approved deletion
set, while retaining D-005..D-007 and the 46 old protected sources.
"""
import csv
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_MAIN = "731e901e79cfa367fd06b4350844c6987b30caa5"
PRE_DELETE_MAIN = "88562135dae2edf8ba7763aa529181c05f7c1ded"
REVIEW = ROOT / "data/repository_reviews/w3_document_disposition_20261017.csv"
OLD_PROTECTED = ROOT / "data/repository_reviews/step4_retention_46_20261017.csv"
CONSOLIDATED = "docs/archive/w3_consolidated_documents_20261017.md"
EXPECTED_IDS = {"D-%03d" % i for i in range(1, 8)}
REMOVABLE = {
    "docs/repository_reorganization_plan.md",
    "docs/research_result_governance.md",
    "docs/phase2_actions_ci_repair_20261017.md",
    "docs/repository_storage_audit_20261014.md",
}
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


def safe_path(relpath):
    if Path(relpath).is_absolute() or ".." in Path(relpath).parts:
        raise AssertionError("Bad path: " + relpath)


def hash_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify_historic_blob(path, sha):
    safe_path(path)
    recovered = git("show", PRE_DELETE_MAIN + ":" + path, text=False)
    assert hash_blob(recovered) == sha, ("Restoration SHA mismatch", path)
    assert git("rev-parse", PRE_DELETE_MAIN + ":" + path).strip() == sha, (
        "Git tree SHA mismatch", path
    )
    return recovered


def verify_unchanged(path, sha):
    safe_path(path)
    target = ROOT / path
    assert target.is_file() and not target.is_symlink(), "Missing original: " + path
    actual = target.read_bytes()
    assert hash_blob(actual) == sha, "Current blob changed: " + path
    assert git("rev-parse", ORIGINAL_MAIN + ":" + path).strip() == sha, (
        "Original baseline mismatch", path
    )


def main():
    with REVIEW.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 7
    assert {r["candidate_id"] for r in rows} == EXPECTED_IDS
    assert len({r["candidate_id"] for r in rows}) == 7
    consolidated = (ROOT / CONSOLIDATED).read_text(encoding="utf-8")
    assert PRE_DELETE_MAIN in consolidated
    seen_removed = set()

    for row in rows:
        path, sha = row["source_path"], row["git_blob_sha1"]
        assert row["review_main_commit"] == ORIGINAL_MAIN
        assert path.startswith("docs/")
        if row["candidate_id"] in {"D-001", "D-002", "D-003", "D-004"}:
            seen_removed.add(path)
            assert row["tree_state"] == "removed_from_current_tree"
            assert row["owner_delete_approval"] == "approved_2026-10-17_user_message"
            assert row["w3_disposition"] == "owner_approved_historical_consolidation"
            assert not (ROOT / path).exists(), "Approved path was not removed: " + path
            verify_historic_blob(path, sha)
            assert path in consolidated and sha in consolidated, (
                "Consolidation missing SHA/path provenance", path
            )
            print(row["candidate_id"], "historical recovery PASS", path)
        else:
            assert row["owner_delete_approval"] == "not_granted"
            assert row["tree_state"] == "retained"
            verify_unchanged(path, sha)
            print(row["candidate_id"], "retained SHA PASS", path)
    assert seen_removed == REMOVABLE, ("unexpected removed paths", seen_removed)

    with OLD_PROTECTED.open(newline="", encoding="utf-8") as f:
        protected = list(csv.DictReader(f))
    assert len(protected) == 46
    for row in protected:
        verify_unchanged(row["path"], row["git_blob_sha1"])

    names = git("diff", "--name-only", PRE_DELETE_MAIN, "HEAD").splitlines()
    deleted = set(git("diff", "--diff-filter=D", "--name-only",
                      PRE_DELETE_MAIN, "HEAD").splitlines())
    assert deleted == REMOVABLE, ("Unexpected deletion set", deleted)
    for name in names:
        assert not name.startswith(PROTECTED_PREFIXES) and name not in PROTECTED_FILES, (
            "RF/experimental evidence changed: " + name
        )
    print(
        "W3 PASS: exactly 4 owner-approved historical docs retired,"
        " all four original blobs restorable from pre-delete main,"
        " 3 retained original docs and 46 protected sources unchanged."
    )
    print(
        "No numeric RF analysis or physical validation is implied."
        " W1 tests tracked Markdown links separately."
    )


if __name__ == "__main__":
    main()
