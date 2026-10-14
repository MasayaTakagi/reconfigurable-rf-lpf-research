"""Metadata coverage must not be mistaken for independent RF replay."""
import unittest

from scripts.report_experiment_metadata_gaps import matrix


class MetadataGapTests(unittest.TestCase):
    def test_all_39_cases_and_no_invented_values(self):
        records, summary = matrix()
        self.assertEqual(39, len(records))
        self.assertEqual({"formal": 19, "historical": 15, "trial": 5},
                         summary["constraint_classes"])
        self.assertEqual(16, summary["unknown_execution_status"])
        self.assertEqual(25, summary["missing_seed"])
        self.assertEqual(15, summary["missing_execution_sha"])
        self.assertEqual(16, summary["missing_environment"])
        self.assertEqual(6, summary["zero_manifest_evidence"])
        self.assertEqual(0, summary["rf_runs_reproduced_by_this_report"])
        self.assertEqual(0, summary["missing_values_filled_by_inference"])
        self.assertEqual(0, summary["original_manifest_edits"])

    def test_formal_checkpoint_gap_not_promoted_or_filled(self):
        records, _ = matrix()
        by_id = {x["experiment_id"]: x for x in records}
        self.assertEqual("formal", by_id["EXP-017"]["constraint_class"])
        self.assertEqual("RF-F002", by_id["EXP-017"]["constraint_id"])
        self.assertEqual("false", by_id["EXP-017"]["execution_reproduced_here"])
        self.assertIn("manifest_evidence_empty",
                      by_id["EXP-017"]["missing_metadata"])
        self.assertNotIn("RF-T004", by_id["EXP-017"]["constraint_id"])
        self.assertTrue(all(
            x["execution_reproduced_here"] == "false" for x in records))


if __name__ == "__main__":
    unittest.main()
