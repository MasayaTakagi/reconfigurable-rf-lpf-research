"""Phase 2 expanding evidence inventory and source-reported checkpoint checks."""
import csv
import unittest
from pathlib import Path

from scripts.audit_experiment_inventory import ROOT, check_inventory
from scripts.audit_research_catalog import audit_catalog, check_threshold


class ExperimentEvidenceInventoryTests(unittest.TestCase):
    def test_all_manifests_are_indexed_without_state_promotion(self):
        self.assertEqual([], check_inventory())
        with (ROOT / "data/experiment_evidence_inventory.csv").open(
                newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertGreaterEqual(len(rows), 39)
        self.assertEqual(39, sum(int(row['experiment_id'][4:]) <= 41 for row in rows))
        by_id = {row["experiment_id"]: row for row in rows}
        self.assertEqual("unknown", by_id["EXP-016"]["execution_status"])
        self.assertEqual("not_run", by_id["EXP-016"]["independent_validation"])
        self.assertEqual("manifest_vs_report_conflict", by_id["EXP-016"]["review_flag"])
        self.assertEqual("reported_30db_checkpoint_missing", by_id["EXP-017"]["review_flag"])
        self.assertEqual("invalid_warmstart_import_performance", by_id["EXP-037"]["review_flag"])

    def test_reported_checkpoint_catalog_retains_unverified_source_label(self):
        self.assertEqual([], audit_catalog())
        with (ROOT / "data/research_candidate_register.csv").open(
                newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        exp016 = [row for row in rows if row["experiment_id"] == "EXP-016"]
        self.assertEqual(4, len(exp016))
        self.assertTrue(all(x["constraint_id"] == "RF-T004" and
                            x["threshold_classification"] == "reported_finite_grid"
                            for x in exp016))
        self.assertEqual([], check_threshold(
            "reported_finite_grid", 35, 35.1999466, 35.2, "trial"))
        self.assertTrue(check_threshold(
            "reported_finite_grid", 35, 34.99999, 35.2, "trial"))


if __name__ == "__main__":
    unittest.main()
