import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'))
from instantiate_graph import build_settings,check_graph
from lpf.circuit import solve
from lpf.evaluate import CASES
class InstantiationTests(unittest.TestCase):
    def test_all_six_same_fixed(self):
        g=(3,((0,2,'LQP02'),(2,1,'GJM01')))
        settings=build_settings(g,caps=[[0,0]]*6)
        self.assertEqual(set(settings),set(CASES))
        self.assertGreater(solve(700e6,**settings['B71'])['gain'],0)
    def test_area(self):
        self.assertEqual(check_graph((2,((0,1,'LQP02'),(0,1,'PCB_L')))),1)
    def test_invalid(self):
        with self.assertRaises(ValueError):check_graph((2,((0,0,'LQP02'),)))
