"""EX-014 2-tunable Phase2 candidate full-band independent verification regression."""
import unittest,json,math,importlib.util
from pathlib import Path
import numpy as np
_HERE=Path(__file__).resolve().parent
HERE=_HERE if (_HERE/'EXP014-01.json').exists() else _HERE.parent/'experiments/chatgpt_topology_search/runs/EXP-014'
# Load this experiment's independent verifier under a unique module name.
# Bare `import verify` may resolve to a different EXP-0xx module loaded by
# unittest discover, silently invalidating the regression.
_spec=importlib.util.spec_from_file_location('lpf_exp014_independent_verify',HERE/'verify.py')
verify=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify)

class TestEXP014(unittest.TestCase):
 def test_all_saved_candidates_independent_mna_dense(self):
  for name in ('EXP014-01','EXP014-02','EXP014-03','EXP014-C4-01'):
   d=json.loads((HERE/(name+'.json')).read_text())
   with self.subTest(name=name):
    v=verify.check(d)
    saved=d['verification']
    for key in ('worst_IL_db','min_H2_db','min_H3_db'):
     self.assertAlmostEqual(v[key],saved[key],delta=1e-8)
    self.assertEqual(v['independent_9x9_MNA_points'],72)
    self.assertLess(v['max_power_balance_residual_W'],1e-12)
    self.assertGreaterEqual(min(v['min_H2_db'],v['min_H3_db']),30)
    self.assertEqual(d['components']['IC_VARIABLE_C']['count'],2)
    self.assertFalse(v['meets_IL_0p3_and_H2H3_30'])
 def test_exact_Q80_parallel_fixed_cap_merge(self):
  trial=[json.loads(s) for s in (HERE/'row_addC.jsonl').read_text().splitlines() if s]
  orig=next(z for z in trial if z['idx']==2)
  x=np.array(orig['x']);merged=json.loads((HERE/'EXP014-01.json').read_text())
  lhs=math.exp(x[4])+math.exp(x[6]);rhs=merged['topology']['fixed_capacitors'][0]['C_pF']
  self.assertAlmostEqual(lhs,rhs,places=12)
  for f in (663.,960.,2745.):
   y=lambda c:2*math.pi*f*1e6*c*1e-12/(1/80-1j)
   self.assertLess(abs(y(math.exp(x[4]))+y(math.exp(x[6]))-y(rhs)),1e-14)
 def test_study_overrides_and_physical_row(self):
  for cid in ('EXP014-01','EXP014-02','EXP014-03'):
   d=json.loads((HERE/(cid+'.json')).read_text());c=d['components']
   self.assertEqual(c['LQP02']['Q'],25)
   self.assertAlmostEqual(d['chip_area_cost_units'],16/3,places=10)
   self.assertEqual(d['topology']['physical_chip_row'],['L0','L1','L2','L3'])
   self.assertFalse(d['study_constraints']['canonical_two_grounded_C_policy_compliant'])
   self.assertTrue(all(abs(k)<=.4 for k in d['topology']['signed_adjacent_k']))
if __name__=='__main__':unittest.main()