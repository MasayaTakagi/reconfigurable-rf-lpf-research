"""RF-T003 Phase 2: 6L/Q25, one fixed GJM and three PCB-C; two tunables."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_cost_6p67 import verify

class TestRFT003CostSixAndTwoThirds(unittest.TestCase):
    def test_both_low_loss_and_higher_attenuation_margin_variants(self):
        results=verify(5)
        self.assertEqual(set(results),{"nominal","margin"})
        for name,value in results.items():
            self.assertTrue(value["IL_goal_pass"])
            self.assertEqual(value["independent_MNA_spots"],84)
            self.assertAlmostEqual(value["chip_cost"],6+2/3)
            self.assertGreaterEqual(value["min_H2_db"],30)
            self.assertGreaterEqual(value["min_H3_db"],30)
            self.assertLess(value["max_independent_delta_db"],1e-8)
            self.assertLess(value["max_power_residual_W"],1e-12)
        self.assertLess(results["nominal"]["IL_db"],.298)
        self.assertLess(results["margin"]["IL_db"],.3)
        self.assertGreaterEqual(results["margin"]["min_H2_db"],30.09999)
        self.assertGreaterEqual(results["margin"]["min_H3_db"],30.09999)

if __name__=="__main__":
    unittest.main()
