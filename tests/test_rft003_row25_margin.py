"""Numerical-only RF-T003 L<=25nH 30.30/30.35dB margin replay."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from verify_rft003_row25_margin import verify
class TestRFT003Row25Margin(unittest.TestCase):
    def test_two_margin_variants(self):
        data=verify(5)
        self.assertEqual(len(data),2)
        for r in data.values():
            self.assertTrue(r["IL_goal_pass"])
            self.assertEqual(r["independent_MNA_spots"],84)
            self.assertLess(r["IL_db"],.3)
            self.assertLess(r["max_independent_delta_db"],1e-8)
            self.assertGreater(r["K_min_eigenvalue"],0)
            self.assertAlmostEqual(r["chip_cost"],6+2/3)
        self.assertGreaterEqual(data["RFT003-6L-HV25-ROW-MARGIN30.35"]["min_H2_db"],30.34999)
if __name__=="__main__":unittest.main()
