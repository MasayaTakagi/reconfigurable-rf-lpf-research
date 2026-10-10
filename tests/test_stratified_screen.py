import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'))
from graph_mna_screen import select_stratified
class StratifiedTests(unittest.TestCase):
    def test_bins(self):
        graphs={((0,1,'LQP02'),),((0,1,'LQP02'),)*3,((0,1,'LQP02'),)*5}
        chosen=select_stratified(graphs,3)
        self.assertEqual(len(chosen),3)
        self.assertEqual({len(g[1]) for g in chosen},{1,3,5})
