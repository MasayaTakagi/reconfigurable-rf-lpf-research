"""Strictly scoped original-preserving EXP-047 provenance compatibility tests."""
import csv
import json
import unittest
from unittest.mock import patch

from src.lpf import experiment_manifest
from src.lpf import legacy_manifest_adapter as legacy


class LegacyExp047AdapterTests(unittest.TestCase):
    def test_source_is_pinned_and_normalized_only_for_index(self):
        view = legacy.legacy_exp047_index_view()
        with (legacy.ROOT / "data/experiment_index.csv").open(
                newline="", encoding="utf-8") as f:
            matching = [r for r in csv.DictReader(f) if r["experiment_id"] == "EXP-047"]
        self.assertEqual(1, len(matching))
        row = matching[0]
        self.assertEqual("EXP-047", view["experiment_id"])
        self.assertEqual("RF-F003", view["constraints"]["constraint_id"])
        self.assertEqual("formal", view["constraints"]["class"])
        self.assertEqual(row["effective_constraint_sha256"],
                         view["constraints"]["effective_constraint_sha256"])
        self.assertEqual(row["purpose"], view["purpose"])
        self.assertEqual(row["execution_status"], view["execution"]["status"])
        self.assertEqual(row["numerical_validation"], view["validation"]["numerical"])
        self.assertEqual(row["independent_validation"], view["validation"]["independent"])

    def test_original_is_still_not_canonical_manifest(self):
        original = json.loads((legacy.ROOT / legacy.ORIGINAL).read_text(encoding="utf-8"))
        self.assertNotIn("code", original)
        self.assertNotIn("random_seed", original)
        self.assertNotIn("environment", original)
        self.assertEqual("partial_local_best_found", original["execution"]["status"])
        self.assertFalse(original["execution"]["github_actions_search_executed"])
        with self.assertRaisesRegex(ValueError, "Missing manifest fields"):
            experiment_manifest.validate_manifest(original, root=legacy.ROOT)

    def test_mutating_original_source_is_rejected(self):
        with patch.object(legacy, "_blob_sha", return_value="0" * 40):
            with self.assertRaisesRegex(ValueError, "source identity changed"):
                legacy.legacy_exp047_index_view()

    def test_all_legacy_index_validation_is_explicit_and_unchanged(self):
        self.assertEqual([], experiment_manifest.audit_provenance(root=legacy.ROOT))


if __name__ == "__main__":
    unittest.main()
