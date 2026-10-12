"""RF-T003 low-area six-L numeric checkpoints, not RF-F001 promotion."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_cost_down_new import verify

class TestRFT003CostDownContinuation(unittest.TestCase):
    def test_passing_and_near_miss_are_separate(self):
        r=verify(5)
        p=r["lower_cost_passing"]
        n=r["lower_cost_nearmiss"]
        self.assertTrue(p["IL_goal_pass"])
        self.assertFalse(n["IL_goal_pass"])
        self.assertLessEqual(p["IL_db"],.30)
        self.assertGreater(n["IL_db"],.30)
        self.assertAlmostEqual(p["chip_cost"],8.)
        self.assertAlmostEqual(n["chip_cost"],7+1/3)
        for candidate in (p,n):
            self.assertGreaterEqual(candidate["min_H2_db"],30.)
            self.assertGreaterEqual(candidate["min_H3_db"],30.)
            self.assertEqual(candidate["independent_MNA_spots"],84)
            self.assertLess(candidate["max_independent_delta_db"],1e-8)
            self.assertLess(candidate["max_power_residual_W"],1e-12)

if __name__=="__main__":
    unittest.main()
