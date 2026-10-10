import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lpf.circuit import Branch,solve
from lpf.independent import solve_gain
class ZeroCapTests(unittest.TestCase):
    def test_zero_cap_open_circuit(self):
        kw=dict(n_nodes=2,source_node=1,load_node=2,inductors=[Branch(1,2,2e-9,25)])
        a=solve(800e6,**kw)
        b=solve(800e6,capacitors=[Branch(1,0,0,80)],**kw)
        self.assertAlmostEqual(a['gain'],b['gain'],places=12)
        self.assertAlmostEqual(b['gain'],solve_gain(800e6,capacitors=[Branch(1,0,0,80)],**kw),places=12)
        self.assertAlmostEqual(b['p_capacitor'],0,places=14)
