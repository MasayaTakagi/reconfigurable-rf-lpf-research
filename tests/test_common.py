import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lpf.constraints import chip_area,check_counts,load_policy
from lpf.metrics import insertion_loss_db

class CommonTests(unittest.TestCase):
    def test_policy(self):
        self.assertIsNone(load_policy()['area_budget']['hard_cap'])
    def test_area(self):
        self.assertAlmostEqual(chip_area(2,1,0,2),4)
        self.assertTrue(check_counts(2,1,0,2,3,2))
        self.assertTrue(check_counts(7))
        self.assertFalse(check_counts(2,0,0,0,4,0))
    def test_il(self):
        self.assertAlmostEqual(insertion_loss_db(0.5,1),3.01029995664)
