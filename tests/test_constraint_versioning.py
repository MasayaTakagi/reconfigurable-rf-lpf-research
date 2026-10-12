"""Formal/trial constraint identity, immutable snapshots and cost Pareto guardrails."""
import json
import unittest
from pathlib import Path

from src.lpf.constraint_versions import load_constraint, constraint_fingerprint
from src.lpf.constraints import check_counts, chip_area

ROOT = Path(__file__).resolve().parents[1]


class VersionedConstraintsTests(unittest.TestCase):
    def test_formal_snapshot_matches_compatibility_file(self):
        active = load_constraint()
        legacy_access = json.loads((ROOT / "data/design_constraints.json").read_text())
        self.assertEqual(active, legacy_access)
        self.assertEqual(active["active_constraint_id"], "RF-F001")
        self.assertEqual(active["active_constraint_status"], "formal")
        self.assertIsNone(active["area_budget"]["hard_cap"])
        self.assertEqual(len(constraint_fingerprint(active)), 64)

    def test_cost_is_not_an_rf_feasibility_limit(self):
        self.assertGreater(chip_area(n_lqp02=8), 6)
        self.assertTrue(check_counts(n_lqp02=8))
        self.assertFalse(check_counts(n_pcb=4))
        self.assertFalse(check_counts(n_var=3))

    def test_trials_are_not_automatically_adopted(self):
        with self.assertRaises(ValueError):
            load_constraint("RF-T001", allow_trial=True)
        with self.assertRaises(ValueError):
            load_constraint("RF-F000")
        self.assertEqual(load_constraint()["active_constraint_id"], "RF-F001")


if __name__ == "__main__":
    unittest.main()
