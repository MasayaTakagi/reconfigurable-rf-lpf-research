"""Phase 2 EXP-013 regression: preserve validated failed cost-4 IL threshold."""
import unittest,sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]/'experiments/chatgpt_topology_search/runs/EXP-013'
sys.path.insert(0,str(HERE))
from verify013 import check
class TestEXP013(unittest.TestCase):
 def test_row_checkpoint_dense_and_mna(self):
  d=json.loads((HERE/'EXP013-ROW-01.json').read_text())
  self.assertEqual(d['area_cost'],4)
  r=check(d,n=7001)
  self.assertAlmostEqual(r['dense']['IL'],.30481726655771096,places=7)
  self.assertGreaterEqual(min(r['dense']['H2'],r['dense']['H3']),30)
  self.assertFalse(r['meets_target'])
 def test_search_summary_not_a_limit(self):
  d=json.loads((HERE/'screening_summary.json').read_text())
  self.assertEqual(d['screening_attempts_completed'],347)
  self.assertEqual(d['refinement_attempts_completed'],9)
  self.assertFalse(d['new_verified']['meets_IL_le_0.3'])
if __name__=='__main__':unittest.main()