"""A full-history backup must be restorable, not just a git bundle verify log."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.backup_complete_git_history import write_bundle


class BranchBundleRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        self.git("config", "user.name", "Evidence Tester")
        self.git("config", "user.email", "evidence@example.invalid")
        p = self.repo / "data/validation/candidate.json"
        p.parent.mkdir(parents=True)
        p.write_text('{"strict": true}\n', encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "initial")
        base = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", base)
        for i in range(6):
            self.git("update-ref", "refs/remotes/origin/old/" + str(i), base)
        self.git("checkout", "-q", "-b", "draft")
        (self.repo / "new.txt").write_text("unmerged review\n", encoding="utf-8")
        self.git("add", "new.txt")
        self.git("commit", "-qm", "draft")
        self.git("update-ref", "refs/remotes/origin/draft", self.git("rev-parse", "HEAD"))

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo,
                                       stderr=subprocess.PIPE).decode().strip()

    def test_bundle_can_restore_all_eight_branch_refs(self):
        out = Path(self.temp.name) / "archive.bundle"
        result = write_bundle(self.repo, out)
        self.assertEqual(8, result["branch_ref_count"])
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), result["sha256"])
        self.assertTrue(result["verification"]["restored_all_branch_tips_exactly"])
        self.assertTrue(result["verification"]["restored_git_fsck_full"])
        self.assertFalse(result["durable_offsite_copy_verified"])
        self.assertEqual(0, result["remote_ref_changes"])
        self.assertEqual(0, result["remote_ref_deletions"])

    def test_incomplete_remote_branch_set_rejected(self):
        self.git("update-ref", "-d", "refs/remotes/origin/old/0")
        with self.assertRaises(ValueError):
            write_bundle(self.repo, Path(self.temp.name) / "invalid.bundle")


if __name__ == "__main__":
    unittest.main()
