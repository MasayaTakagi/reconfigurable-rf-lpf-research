"""Metadata coverage must not be mistaken for independent RF replay."""
import unittest

from scripts.report_experiment_metadata_gaps import matrix


class MetadataGapTests(unittest.TestCase):
    def test_all_current_cases_and_no_invented_values(self):
        records, summary = matrix()
        historical = [x for x in records if int(x["experiment_id"][4:]) <= 41]
        self.assertEqual(39, len(historical))
        self.assertEqual(len(records), summary["experiments"])
        self.assertGreaterEqual(len(records), len(historical))
        for field, expected in (("unknown_execution_status", 16),
                                ("missing_seed", 25),
                                ("missing_execution_sha", 15),
                                ("missing_environment", 16),
                                ("zero_manifest_evidence", 6)):
            key, check = {
                "unknown_execution_status": ("execution_status", "unknown"),
                "missing_seed": ("seed_recorded", "false"),
                "missing_execution_sha": ("execution_sha_recorded", "false"),
                "missing_environment": ("environment_recorded", "false"),
                "zero_manifest_evidence": ("registered_evidence_count", "0"),
            }[field]
            self.assertEqual(expected, sum(x[key] == check for x in historical))
            self.assertEqual(sum(x[key] == check for x in records), summary[field])
        self.assertEqual({"formal": 19, "historical": 15, "trial": 5},
                         {kind: sum(x["constraint_class"] == kind for x in historical)
                          for kind in ("formal", "historical", "trial")})
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
