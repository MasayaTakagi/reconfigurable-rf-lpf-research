#!/usr/bin/env python3
"""W3 read-only gate: preserve dated sources until per-path owner approval.

This verifies current tracked blob identity and the ability to retrieve
the same file bytes from the pinned pre-W3 main commit. It does not
prove there are no dynamic/code/external links.
"""
import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = "731e901e79cfa367fd06b4350844c6987b30caa5"
REVIEW = ROOT / "data/repository_reviews/w3_document_disposition_20261017.csv"
OLD_PROTECTED = ROOT / "data/repository_reviews/step4_retention_46_20261017.csv"
EXPECTED_IDS = {"D-%03d" % i for i in range(1, 8)}
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


def check_original(relpath, original_sha):
    path = ROOT / relpath
    if Path(relpath).is_absolute() or ".." in Path(relpath).parts:
        raise AssertionError("Bad path: " + relpath)
    if not path.is_file() or path.is_symlink():
        raise AssertionError("Original source missing or symlink: " + relpath)
    actual = git("hash-object", relpath).strip()
    expected_at_main = git("rev-parse", MAIN + ":" + relpath).strip()
    if not actual == original_sha == expected_at_main:
        raise AssertionError("Original Git blob changed: " + relpath)
    # Verify real byte-for-byte git-show recovery, not just a ref name.
    recovered = git("show", MAIN + ":" + relpath, text=False)
    if recovered != path.read_bytes():
        raise AssertionError("Recovered file bytes differ: " + relpath)


def main():
    with REVIEW.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ids = [row["candidate_id"] for row in rows]
    assert len(rows) == 7 and set(ids) == EXPECTED_IDS
    assert len(set(ids)) == len(ids)
    for row in rows:
        assert row["review_main_commit"] == MAIN
        assert row["owner_delete_approval"] == "not_granted"
        assert row["tree_state"] == "retained"
        assert row["w3_disposition"] in (
            "conditional_replacement_before_owner_review",
            "retain_unique_historical_numerics",
            "retain_independent_verification_context",
            "retain_unique_historical_scope",
        )
        assert row["source_path"].startswith("docs/")
        check_original(row["source_path"], row["git_blob_sha1"])

    with OLD_PROTECTED.open(newline="", encoding="utf-8") as f:
        protected = list(csv.DictReader(f))
    assert len(protected) == 46, len(protected)
    for row in protected:
        check_original(row["path"], row["git_blob_sha1"])

    names = git("diff", "--name-only", MAIN, "HEAD").splitlines()
    deletions = git("diff", "--diff-filter=D", "--name-only", MAIN, "HEAD").splitlines()
    assert not deletions, "W3 must not delete any tracked file: " + str(deletions)
    for name in names:
        assert not name.startswith(PROTECTED_PREFIXES) and name not in PROTECTED_FILES, (
            "W3 modifies original RF/experimental evidence: " + name
        )

    # Diagnostic only: this is not complete reference discovery.
    for row in rows:
        path = row["source_path"]
        print(row["candidate_id"], "original blob/restore PASS", path)
    print(
        "W3 PASS: 7 original docs byte-identical and restorable;"
        " 46 older protected files identical; no tree deletion or RF source change."
    )
    print("Note: static link coverage is checked separately by the W1 verifier;"
          " dynamic/external references and full Git history remain unverified.")


if __name__ == "__main__":
    main()
