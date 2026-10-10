import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'))
from enumerate_grounded import canonical,active_connected,enumerate_grounded
class GroundedTests(unittest.TestCase):
    def test_ground_distinct(self):
        self.assertNotEqual(canonical(3,((0,1,'GJM01'),(1,2,'LQP02'))),
                            canonical(3,((0,2,'GJM01'),(1,2,'LQP02'))))
    def test_shunt_allowed(self):
        self.assertTrue(active_connected(3,((1,2,'LQP02'),(1,0,'GJM01'))))
    def test_no_signal_path(self):
        self.assertFalse(active_connected(3,((0,1,'GJM01'),(0,2,'GJM01')))==False)
    def test_budget(self):
        counts,_=enumerate_grounded(2,4,100)
        self.assertTrue(counts['truncated'])
        self.assertEqual(counts['raw'],100)
