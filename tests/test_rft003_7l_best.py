"""RF-T003 7L/3-PCB checkpoint; prevents accidental formal-policy promotion."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_7l_best import verify

class TestRFT003SevenL(unittest.TestCase):
    def test_stored_trial_has_two_variable_c_and_independent_mna_power(self):
        data=verify(7)
        self.assertEqual(data["constraint_id"],"RF-T003")
        self.assertEqual(data["augmented_MNA_dimension"],12)
        self.assertEqual(data["independent_MNA_points"],84)
        self.assertTrue(data["meets_trial_IL_0p30"])
        self.assertAlmostEqual(data["worst_IL_db"],.29984526946634216,delta=2e-6)
        self.assertGreaterEqual(data["min_H2_db"],30)
        self.assertGreaterEqual(data["min_H3_db"],30)
        self.assertLess(data["max_MNA_difference_db"],1e-8)
        self.assertLess(data["max_power_balance_residual_W"],1e-12)
        self.assertGreater(data["K_min_eigenvalue"],0)

if __name__=="__main__":
    unittest.main()
