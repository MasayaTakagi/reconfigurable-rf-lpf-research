"""Non-destructive reverse references and condition-isolated Pareto tests."""
import unittest

from scripts.build_reference_inventory import (
    ROOT, _classify, _safe_reference, create_inventory,
)
from scripts.report_research_pareto import dominates, make_report


class StorageReferenceTests(unittest.TestCase):
    def test_referenced_runtime_lock_is_preserved(self):
        p = "data/validation/example/run/locks/foo.lock"
        self.assertEqual(
            ("registered_runtime_evidence", "preserve_referenced"),
            _classify(p, {"manifest_sha256"}))
        self.assertEqual(
            ("unlinked_runtime_diagnostic", "review_only_no_deletion"),
            _classify(p, set()))

    def test_source_path_escape_is_rejected(self):
        for path in ("/etc/passwd", "../README.md", "data/../README.md",
                     "data\\validation\\abc.json", ""):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    _safe_reference(ROOT, path)

    def test_existing_catalog_and_manifest_links_are_preserved(self):
        entries, summary = create_inventory()
        self.assertGreaterEqual(summary["classified_files"], 300)
        self.assertGreater(summary["manifest_referenced_files"], 0)
        self.assertEqual(0, summary["deletions_performed"])
        self.assertGreaterEqual(summary["identical_content_blob_groups"], 0)
        self.assertTrue(summary["duplicate_paths_also_require_independent_review"])
        self.assertEqual(
            sum(summary["retention_decisions"].values()), len(entries))
        self.assertTrue(all(r["review_decision"] == "review_only_no_deletion"
                            for r in entries if r["path"] in
                            summary["review_only_example_paths"]))
        by_path = {r["path"]: r for r in entries}
        p = "data/validation/rf_f002_unscaled_followup_20261014/run/results/6acd4f80fcd682902c52c999.json"
        self.assertEqual("preserve_referenced", by_path[p]["review_decision"])
        self.assertIn("EXP-041", by_path[p]["manifest_experiments"])
        p2 = "experiments/chatgpt_topology_search/runs/EXP-016/checkpoints.json"
        self.assertIn("EXP-016", by_path[p2]["supplemental_experiments"])


class ParetoRegressions(unittest.TestCase):
    def test_domination_requires_no_worse_area_and_il(self):
        a = {"chip_area_units": 6, "worst_il_db": 0.4}
        b = {"chip_area_units": 6, "worst_il_db": 0.5}
        c = {"chip_area_units": 8, "worst_il_db": 0.3}
        self.assertTrue(dominates(a, b))
        self.assertFalse(dominates(a, c))
        self.assertFalse(dominates(c, a))
        self.assertFalse(dominates(a, a))

    def test_register_groups_cannot_promote_trial_to_formal(self):
        view, summary = make_report()
        self.assertEqual(13, summary["candidate_count"])
        self.assertEqual(8, summary["comparison_group_count"])
        self.assertFalse(summary["formal_strict_rf_f002_il0p3_met"])
        by_id = {r["catalog_id"]: r for r in view}
        trial = by_id["EXP018-C13.667"]
        self.assertEqual("trial", trial["constraint_class"])
        self.assertEqual("RF-T004", trial["constraint_id"])
        self.assertEqual("true", trial["il_0p30_met_on_recorded_grid"])
        nominal = by_id["EXP-041-35DB-STAGE"]
        self.assertEqual("tolerance_only", nominal["threshold_classification"])
        self.assertEqual("false", nominal["il_0p30_met_on_recorded_grid"])
        same_group = [r for r in view if r["comparison_key"] ==
                      "RF-F002_full_lpf_35_strict_finite_grid"]
        self.assertEqual(2, len(same_group))
        self.assertTrue(all(r["pareto_within_group"] == "true" for r in same_group))
        old = [r for r in view if r["constraint_class"] == "historical"]
        self.assertEqual(1, sum(r["pareto_within_group"] == "true" for r in old))


if __name__ == "__main__":
    unittest.main()
