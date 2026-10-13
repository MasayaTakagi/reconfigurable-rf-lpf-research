"""Do not promote RF-T003 low-area 6L near-miss as a passed <=0.30dB result."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_cost_reduction import run

class TestCostDownTrial(unittest.TestCase):
    def test_independent_six_L_low_chip_cost_still_fails_IL_target(self):
        result=run(samples=5)
        self.assertEqual(result["trial"],"RF-T003")
        self.assertAlmostEqual(result["chip_area"],7+1/3)
        self.assertFalse(result["IL_target_pass"])
        self.assertGreater(result["IL_db"],.3)
        self.assertLess(result["IL_db"],.305)
        self.assertGreaterEqual(result["min_H2_db"],30)
        self.assertGreaterEqual(result["min_H3_db"],30)
        self.assertEqual(result["independent_MNA_spots"],84)
        self.assertLess(result["max_independent_diff_db"],1e-8)
        self.assertLess(result["power_balance_W"],1e-12)

if __name__=="__main__":
    unittest.main()
