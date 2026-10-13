"""RF-T003 25nH 6L physical-row optimization regression: numerical only."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from verify_rft003_new_row import verify
class TestRFT003NewRow25(unittest.TestCase):
    def test_25nH_30p101dB_independent(self):
        x=verify(5)
        self.assertEqual(x["independent_MNA_spots"],84)
        self.assertAlmostEqual(x["chip_cost"],6+2/3)
        self.assertTrue(x["IL_goal_pass"])
        self.assertLess(x["IL_db"],.296)
        self.assertGreaterEqual(x["min_H2_db"],30.10099)
        self.assertGreaterEqual(x["min_H3_db"],30.10099)
        self.assertLess(x["max_independent_delta_db"],1e-8)
        self.assertLess(x["max_power_residual_W"],1e-12)
        self.assertGreater(x["K_min_eigenvalue"],0)
if __name__=="__main__":unittest.main()
