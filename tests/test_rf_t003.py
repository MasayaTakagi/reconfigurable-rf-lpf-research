"""RF-T003: explicit two-C one-ground + non-ground bridge 30dB Phase 2 scope."""
import sys
import unittest
from pathlib import Path
from src.lpf.constraint_versions import (
    load_constraint,validate_registry,validate_variable_c_connections,constraint_fingerprint
)
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_30db import verify

class RFT003Tests(unittest.TestCase):
    def test_registration_and_formal_non_regression(self):
        registry=validate_registry()
        self.assertEqual(registry["active_formal_id"],"RF-F003")
        self.assertEqual(registry["trial"]["RF-T003"]["state"],"study_authorized")
        f=load_constraint("RF-F001")
        self.assertEqual(f["evaluation"]["full_phase2"]["nominal_h2_h3_target_db"],35)
        self.assertEqual(f["components"]["IC_VARIABLE_C"]["positions_allowed_by_default"],["shunt_to_ground"])
        with self.assertRaises(ValueError):
            load_constraint("RF-T003")
        t=load_constraint("RF-T003",allow_trial=True)
        self.assertEqual(t["evaluation"]["full_phase2"]["nominal_h2_h3_target_db"],30)
        self.assertEqual(t["evaluation"]["full_phase2"]["minimum_h2_h3_db"],30)
        self.assertEqual(t["trial_variable_c_layout"],{"branch_count":2,"shunt_to_ground":1,"non_ground_bridge":1})
        self.assertEqual(t["area_budget"],f["area_budget"])
        self.assertEqual(t["coupling_limits"],f["coupling_limits"])
        self.assertEqual(t["phase3"],f["phase3"])
        self.assertEqual(constraint_fingerprint(t),"e0c45f7094ced1ed2ccb91cae474c7c3c1a6af73a495a2a9cf8f512ccb45ab08")
    def test_exact_layout_and_no_series(self):
        p=load_constraint("RF-T003",allow_trial=True)
        correct=[{"a":5,"b":0},{"a":2,"b":3,"role":"bridge"}]
        self.assertTrue(validate_variable_c_connections(correct,p))
        for invalid in [
            [{"a":5,"b":0},{"a":4,"b":0}],
            [{"a":5,"b":0},{"a":2,"b":3}],
            [{"a":5,"b":0},{"a":2,"b":3,"role":"series"}],
            [{"a":5,"b":0}],
            correct+[{"a":1,"b":0}],
        ]:
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                validate_variable_c_connections(invalid,p)
        with self.assertRaises(ValueError):
            validate_variable_c_connections(correct,load_constraint("RF-F001"))
    def test_saved_result_finite_grid_and_independent_mna(self):
        result=verify(5)
        self.assertEqual(result["independent_MNA_points"],84)
        self.assertGreaterEqual(result["min_H2_db"],30)
        self.assertGreaterEqual(result["min_H3_db"],30)
        self.assertLess(result["worst_IL_db"],0.4)
        self.assertLess(result["max_MNA_difference_db"],1e-8)
        self.assertFalse(result["meets_IL_0p30"])

if __name__=="__main__":
    unittest.main()
