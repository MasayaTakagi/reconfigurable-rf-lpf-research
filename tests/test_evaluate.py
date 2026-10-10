import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lpf.circuit import Branch,solve
from lpf.independent import solve_gain
from lpf.evaluate import evaluate_settings,load_bands,CASES
class EvaluationTests(unittest.TestCase):
    def test_crosscheck(self):
        args=dict(n_nodes=3,source_node=1,load_node=3,
                  inductors=[Branch(1,2,2e-9,25),Branch(2,3,3e-9,15)],
                  capacitors=[Branch(2,0,1e-12,80)],coupling=[[1,.35],[.35,1]])
        for f in (620e6,750e6,960e6,1800e6,2750e6):
            r=solve(f,**args)
            self.assertAlmostEqual(r['gain'],solve_gain(f,**args),places=11)
            self.assertLess(abs(r['power_residual']),1e-11)
    def test_segments(self):
        self.assertEqual(set(r['case'] for r in load_bands()),set(CASES))
    def test_six_settings(self):
        def circuit(case): return dict(n_nodes=1,source_node=1,load_node=1,load_ohms=50+0j)
        r=evaluate_settings(circuit,samples_per_segment=3)
        self.assertEqual(len(r['per_case']),6)
        self.assertAlmostEqual(r['worst_il_db'][0],0,places=11)
        self.assertTrue(r['grid_only'])
