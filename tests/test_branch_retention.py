"""Regression guard: historical Git branch audit never deletes or edits evidence."""
import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.audit_branch_retention import audit_branches, tree_blobs


class BranchRetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        p = self.root / "experiments/test/evidence.json"
        p.parent.mkdir(parents=True)
        p.write_text('{"id":"one"}\n', encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "save evidence")
        first = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", first)
        self.git("update-ref", "refs/remotes/origin/review/test-branch", first)
        self.ledger(first)

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, stderr=subprocess.PIPE
        ).decode("utf-8").strip()

    def ledger(self, sha):
        p = self.root / "data/branch_retention_review_20261015.csv"
        p.parent.mkdir(exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as out:
            writer = csv.writer(out)
            writer.writerow(("branch", "merged_pr", "expected_head_sha",
                             "review_status", "disposition"))
            writer.writerow(("review/test-branch", "49", sha,
                             "merged_and_head_compared",
                             "retain_pending_owner_approval"))

    def test_identical_head_is_not_deletion_authority(self):
        report = audit_branches(self.root)
        self.assertTrue(report["all_reviewed_research_blobs_present_in_current_main"])
        self.assertFalse(report["branch_records"][0]["deletion_authorized"])
        self.assertEqual(0, report["deletions_executed"])
        self.assertIn("experiments/test/evidence.json", tree_blobs(self.root, "HEAD"))

    def test_missing_research_blob_is_detected_even_if_branch_pr_is_merged(self):
        self.git("checkout", "-b", "review/test-branch")
        p = self.root / "experiments/test/unmerged.json"
        p.write_text('{"source":"branch"}\n', encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "add unique evidence")
        sha = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/review/test-branch", sha)
        self.ledger(sha)
        report = audit_branches(self.root)
        self.assertFalse(report["all_reviewed_research_blobs_present_in_current_main"])
        self.assertEqual(
            ["experiments/test/unmerged.json"],
            report["branch_records"][0]["research_head_blobs_absent_in_current_main"])

    def test_changed_head_ref_is_rejected(self):
        p = self.root / "notes.txt"
        p.write_text("new HEAD\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "change branch head")
        self.git("update-ref", "refs/remotes/origin/review/test-branch",
                 self.git("rev-parse", "HEAD"))
        with self.assertRaises(ValueError):
            audit_branches(self.root)

    def test_retention_ledger_cannot_silently_authorize_deletion(self):
        p = self.root / "data/branch_retention_review_20261015.csv"
        p.write_text(p.read_text().replace("retain_pending_owner_approval",
                                           "approved_delete"), encoding="utf-8")
        with self.assertRaises(ValueError):
            audit_branches(self.root)


if __name__ == "__main__":
    unittest.main()
