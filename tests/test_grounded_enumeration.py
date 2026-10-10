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
    def test_ground_return_path_is_valid(self):
        self.assertTrue(active_connected(3,((0,1,'GJM01'),(0,2,'GJM01'))))
    def test_budget(self):
        counts,_=enumerate_grounded(2,4,100)
        self.assertTrue(counts['truncated'])
        self.assertEqual(counts['raw'],100)

class GroundedMnaTests(unittest.TestCase):
    def test_shunt_cap_and_series_inductor(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
        from instantiate_graph import build_grounded_settings
        from lpf.circuit import solve
        settings=build_grounded_settings((3,((1,2,'LQP02'),(2,0,'GJM01'))))
        result=solve(700e6,**settings['B71'])
        self.assertGreater(result['gain'],0)
        self.assertLess(abs(result['power_residual']),1e-10)
