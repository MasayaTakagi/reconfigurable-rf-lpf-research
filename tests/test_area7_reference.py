"""Preserve historical cost-7 references; current formal cost has no hard cap."""
import importlib.util
import json
import unittest
from unittest.mock import patch

from lpf.constraint_versions import load_constraint
from lpf.validate import validate_couplings
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/"experiments/chatgpt_topology_search/runs/EXP-002/verify_area7.py"
spec=importlib.util.spec_from_file_location("area7_reference_verifier",F)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CostSevenReferenceTests(unittest.TestCase):
    def setUp(self):
        # Replay the archived EXP-002 script without editing its hashed evidence.
        legacy = load_constraint("RF-F001")
        a = patch("lpf.configuration.formal_policy", return_value=legacy)
        b = patch.object(
            module, "validate_couplings",
            side_effect=lambda *args, **kwargs: validate_couplings(
                *args, resolved_policy=legacy, **kwargs),
        )
        a.start()
        b.start()
        self.addCleanup(b.stop)
        self.addCleanup(a.stop)

    def test_two_references_have_unchanged_approved_area_policy(self):
        canonical=json.loads((ROOT/"data/design_constraints.json").read_text(encoding="utf-8"))
        self.assertIsNone(canonical["area_budget"]["hard_cap"])
        self.assertEqual(canonical["area_budget"]["historical_hard_cap"],6)
        for name in ("A7-01","A7-02","A7-03","A7-04"):
            obj=module.load_reference(name)
            self.assertEqual(obj["study_override"]["exploratory_cost_cap"],7)
            self.assertFalse(obj["study_override"]["canonical_policy_hard_cap_modified"])
            self.assertAlmostEqual(obj["chip_area_cost_units"],20/3)
            self.assertTrue(module.build_settings(obj))

    def test_both_references_reproduce_sparse_rf_constraints(self):
        for name in ("A7-01","A7-02"):
            with self.subTest(reference=name):
                obj=module.load_reference(name)
                result=module.verify(obj,samples_per_segment=11)
                self.assertLess(result["max_il_db"],.52)
                self.assertGreaterEqual(result["min_h2_db"],35.)
                self.assertGreaterEqual(result["min_h3_db"],35.)
                self.assertLess(result["max_power_balance_residual_W"],1e-10)


if __name__=="__main__":
    unittest.main()
