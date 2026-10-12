import json, sys, unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'experiments'/'chatgpt_topology_search'/'runs'/'EXP-015'
sys.path.insert(0,str(BASE))
from verify015 import verify

class TestExp015Series(unittest.TestCase):
 def test_high_frequency_hv_and_hq_physical_bounds(self):
  d=json.loads((BASE/'summary.json').read_text())
  self.assertEqual(len(d['new_candidates']),9)
  for ident,m in d['new_candidates'].items():
   cand=json.loads((BASE/(ident+'.json')).read_text())
   self.assertLessEqual(cand['chip_area_cost_units'],6)
   expected_area = 4 + (2 if m['variable_C_count']==2 else 1)*2/3
   self.assertAlmostEqual(cand['chip_area_cost_units'],expected_area,places=10)
   self.assertGreaterEqual(cand['min_H2_db'],30-1e-7)
   self.assertGreaterEqual(cand['min_H3_db'],30-1e-7)
   for s,L,Q in zip(cand['chip_series'],cand['L_nH'],cand['Q_L']):
    if s=='LQP02HV':self.assertLessEqual(L,27+1e-8);self.assertEqual(Q,25)
    else:self.assertEqual(s,'LQP02HQ');self.assertLessEqual(L,56+1e-8);self.assertEqual(Q,20)
  self.assertLess(d['new_candidates']['EXP015-HQ3C-01']['worst_IL_db'],.303)
  self.assertGreater(d['new_candidates']['EXP015-HQ3C-01']['worst_IL_db'],.30)
 def test_independent_mna_for_two_primary_designs(self):
  for name in ('EXP015-HV3C-01','EXP015-HQ3C-01','EXP015-HV2C-01'):
   out=verify(BASE/(name+'.json'))
   self.assertTrue(out['independent_MNA'])
   self.assertLess(out['max_power_residual_W'],1e-12)

if __name__=='__main__':unittest.main()