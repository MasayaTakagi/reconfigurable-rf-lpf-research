"""Git-only Phase 2 preservation budget applies only to new/changed files."""
import json
import unittest
from pathlib import Path

from scripts.audit_git_storage_budget import _scope, _size_report

ROOT = Path(__file__).resolve().parents[1]


class GitOnlyStorageBudgetTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "data/phase2_git_storage_budget.json")
                                 .read_text(encoding="utf-8"))

    def test_only_github_git_is_a_long_term_store(self):
        self.assertEqual("GitHub Git only", self.policy["storage_backend"])
        self.assertFalse(self.policy["external_archive_required"])
        self.assertTrue(self.policy["rules"]["full_candidate_vectors_required"])
        self.assertTrue(self.policy["rules"]["prior_owner_approval_required_for_deletion"])
        self.assertLess(self.policy["thresholds"]["individual_new_file_hard_bytes"],
                        2 ** 21)

    def test_legacy_blob_over_threshold_does_not_force_deletion(self):
        path = "experiments/chatgpt_topology_search/runs/EXP-013/screening_records_compact.json"
        r = _size_report([path], set(), {path: 288503}, self.policy)
        self.assertEqual([], r["review_items"])
        self.assertEqual([], r["new_file_hard_limit_violations"])
        self.assertEqual(0, r["file_deletions"])

    def test_large_new_run_blob_is_blocked_without_touching_source(self):
        p = "experiments/chatgpt_topology_search/runs/EXP-999/raw.json"
        q = "experiments/chatgpt_topology_search/runs/EXP-999/checkpoints/a.json"
        r = _size_report([p, q], {p, q}, {p: 1048577, q: 2048}, self.policy)
        self.assertEqual([p], r["new_file_hard_limit_violations"])
        self.assertTrue(any(x["severity"] == "group_review" for x in r["review_items"]))
        self.assertEqual(0, r["evidence_edits"])
        self.assertEqual("experiments/EXP-999", _scope(p))

    def test_119k_source_zip_is_below_soft_limit(self):
        p = "experiments/chatgpt_topology_search/runs/EXP-020/RF-T004-EXP017-bundle.zip"
        r = _size_report([p], {p}, {p: 118646}, self.policy)
        self.assertEqual([], r["review_items"])
        self.assertFalse(r["total_over_review_threshold"])
        self.assertEqual(118646, r["added_file_bytes"])


if __name__ == "__main__":
    unittest.main()
