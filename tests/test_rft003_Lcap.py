"""RF-T003 lower-Lcap Phase2 regressions, not RF-F001 formal release."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_Lcap import verify

class TestRFT003HVInductanceCaps(unittest.TestCase):
    def test_independent_six_HV_caps_24_25_26(self):
        result=verify(5)
        self.assertEqual(len(result),3)
        for name,r in result.items():
            self.assertTrue(r["IL_goal_pass"],name)
            self.assertLess(r["IL_db"],.3)
            self.assertGreaterEqual(r["min_H2_db"],30.)
            self.assertGreaterEqual(r["min_H3_db"],30.)
            self.assertEqual(r["independent_MNA_spots"],84)
            self.assertAlmostEqual(r["chip_cost"],6+2/3)
            self.assertLess(r["max_independent_delta_db"],1e-8)
            self.assertGreater(r["K_min_eigenvalue"],0)
        self.assertGreaterEqual(result["RFT003-6L-1GJM-HV26_30p100"]["min_H2_db"],30.099)
if __name__=="__main__":unittest.main()
