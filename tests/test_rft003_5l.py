"""RF-T003 five-HV study checkpoint (not RF-F001 formal proof)."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_rft003_5l import verify

class TestRFT003FiveL(unittest.TestCase):
    def test_coarse_segmented_power_and_independent_MNA(self):
        result = verify(samples=5)
        self.assertEqual(result["constraint_id"], "RF-T003")
        self.assertEqual(result["independent_MNA_spots"], 84)
        self.assertLess(result["worst_IL_db"], 0.37)
        self.assertGreaterEqual(result["min_H2_db"], 30.)
        self.assertGreaterEqual(result["min_H3_db"], 30.)
        self.assertLess(result["max_independent_error_db"], 1e-8)
        self.assertLess(result["max_power_balance_residual_W"], 1e-12)
        self.assertFalse(result["passes_IL_0p30_goal"])

if __name__ == "__main__":
    unittest.main()
