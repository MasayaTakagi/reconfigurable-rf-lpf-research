import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lpf.circuit import Branch
from lpf.evaluate import CASES
from lpf.configuration import validate_six_settings
from lpf.constraint_versions import load_constraint
class InvarianceTests(unittest.TestCase):
    def setup_cases(self):
        return {case:dict(n_nodes=2,source_node=1,load_node=2,
              inductors=[Branch(1,2,3e-9,25)],
              capacitors=[Branch(1,0,(i+1)*.1e-12,80),Branch(2,0,1e-12,80)],
              coupling=[[1.]]) for i,case in enumerate(CASES)}
    def test_valid(self):
        self.assertTrue(validate_six_settings(self.setup_cases(),[0],resolved_policy=load_constraint('RF-F001')))
    def test_fixed_inductor(self):
        a=self.setup_cases();a['B8']['inductors']=[Branch(1,2,4e-9,25)]
        with self.assertRaises(ValueError):validate_six_settings(a,[0],resolved_policy=load_constraint('RF-F001'))
    def test_fixed_cap(self):
        a=self.setup_cases();a['B8']['capacitors'][1]=Branch(2,0,2e-12,80)
        with self.assertRaises(ValueError):validate_six_settings(a,[0])
    def test_var_cap_range(self):
        a=self.setup_cases();a['B8']['capacitors'][0]=Branch(1,0,4.1e-12,80)
        with self.assertRaises(ValueError):validate_six_settings(a,[0])
    def test_var_cap_ground(self):
        a=self.setup_cases();a['B8']['capacitors'][0]=Branch(1,2,.3e-12,80)
        with self.assertRaises(ValueError):validate_six_settings(a,[0])
