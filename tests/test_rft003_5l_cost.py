"""RF-T003 5L/2GJM/3PCB cost6+1/3: verified finite independent numerical checks."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_5l_cost import verify

class TestRFT003FiveLCostReduction(unittest.TestCase):
    def test_five_chip_L_numeric_trial_and_attenuation_margin(self):
        actual=verify(points=5)
        self.assertEqual(len(actual),4)
        self.assertIn("LOW_IL_30p01",actual)
        self.assertIn("MARGIN_30p100",actual)
        self.assertIn("MARGIN_30p200",actual)
        self.assertIn("MARGIN_30p300",actual)
        for name,z in actual.items():
            self.assertTrue(z["IL_goal_pass"],name)
            self.assertAlmostEqual(z["chip_cost"],5+4/3)
            self.assertLess(z["IL_db"],0.30)
            self.assertGreaterEqual(z["min_H2_db"],30-1e-7)
            self.assertGreaterEqual(z["min_H3_db"],30-1e-7)
            self.assertEqual(z["independent_MNA_spots"],84)
            self.assertLess(z["max_independent_delta_db"],1e-8)
            self.assertLess(z["max_power_residual_W"],1e-12)
        self.assertLess(actual["LOW_IL_30p01"]["IL_db"],0.297)
        self.assertLess(actual["MARGIN_30p100"]["IL_db"],0.299)
        self.assertGreater(actual["MARGIN_30p300"]["min_H2_db"],30.29999)
        self.assertGreater(actual["MARGIN_30p300"]["min_H3_db"],30.29999)

if __name__=="__main__":
    unittest.main()
