"""RF-T003 Phase 2 low-area numeric near-miss is not a passed trial."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_rft003_5l_1gjm_nearmiss import verify

class TestRFT003FiveLOneGJM(unittest.TestCase):
    def test_candidate_has_valid_attenuation_but_fails_il_target(self):
        v = verify(points=5)
        self.assertAlmostEqual(v["chip_cost"], 5+2/3)
        self.assertFalse(v["IL_goal_pass"])
        self.assertGreater(v["IL_db"], 0.30)
        self.assertLess(v["IL_db"], 0.31)
        self.assertGreaterEqual(v["min_H2_db"], 30)
        self.assertGreaterEqual(v["min_H3_db"], 30)
        self.assertEqual(v["independent_MNA_spots"], 84)
        self.assertLess(v["max_independent_delta_db"], 1e-8)
        self.assertLess(v["max_power_residual_W"], 1e-12)
        self.assertGreater(v["K_min_eigenvalue"], 0)

if __name__ == "__main__":
    unittest.main()
