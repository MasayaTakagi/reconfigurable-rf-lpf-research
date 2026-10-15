import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'))
from p4_batch import layout_candidates
class LayoutPilotTests(unittest.TestCase):
    def test_chip_and_pcb_patterns_spd(self):
        graph=(3,((1,2,'LQP02'),(1,2,'LQP02'),(1,2,'PCB_L'),(1,2,'PCB_L')))
        matrices=layout_candidates(graph,20)
        self.assertGreaterEqual(len(matrices),5)
        self.assertTrue(all(np.linalg.eigvalsh(k).min()>0 for k in matrices))
        self.assertTrue(any(abs(k[0,1])==.10 for k in matrices))
        self.assertTrue(any(abs(k[2,3])==.10 for k in matrices))
    def test_one_chip_nominal(self):
        self.assertEqual(len(layout_candidates((3,((1,2,'LQP02'),)),20)),1)
