import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'))
from enumerate_graphs import canonical,enumerate_graphs
class GraphTests(unittest.TestCase):
    def test_terminal_fixed(self):
        a=((0,2,'LQP02'),(2,1,'GJM01'))
        b=((0,1,'LQP02'),(1,2,'GJM01'))
        self.assertNotEqual(canonical(3,a),canonical(3,b))
    def test_internal_permutation(self):
        a=((0,2,'LQP02'),(2,3,'GJM01'),(3,1,'PCB_L'))
        b=((0,3,'LQP02'),(3,2,'GJM01'),(2,1,'PCB_L'))
        self.assertEqual(canonical(4,a),canonical(4,b))
    def test_counts(self):
        c,_=enumerate_graphs(2,2)
        self.assertGreater(c['P2'],0)
        self.assertEqual(c['unique'],c['P2']+c['P3']+c['P4'])
