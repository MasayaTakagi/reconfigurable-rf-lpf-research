"""RF-T003 saved 5L coupling-row Phase 2 trial: independently recheck power."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
from verify_rft003_coupling_row import verify

class TestRFT003CouplingRow(unittest.TestCase):
    def test_saved_5l_trial_layout_all_settings(self):
        r=verify(5)
        self.assertEqual(r["trial"], "RF-T003")
        self.assertEqual(r["MNA_checked_points"],84)
        self.assertAlmostEqual(r["worst_IL_db"],.3483611879968971,delta=1e-6)
        self.assertGreaterEqual(r["min_H2_db"],30.)
        self.assertGreaterEqual(r["min_H3_db"],30.)
        self.assertLess(r["max_MNA_disagreement_db"],1e-8)
        self.assertLess(r["max_power_balance_residual_W"],1e-12)
        self.assertGreater(r["min_K_eigenvalue"],0)
        self.assertFalse(r["meets_IL_goal_0p30"])

if __name__=="__main__":
    unittest.main()
