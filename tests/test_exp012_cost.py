"""EXP012 finite local cost-minimization checkpoint regression (not a global proof)."""
import json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]/'experiments/chatgpt_topology_search/runs/EXP-012'
sys.path.insert(0,str(R))
from verify import verify

class TestExp012Cost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates={d['id']:d for d in json.loads((R/'independent_shortlist.json').read_text())['verified']}
    def test_cost3_and_cost4_local_not_falsely_claimed_to_pass(self):
        for id in ['3CV_4L_0GJM','3CV_4L_0GJM_1PCB','3CV_3L_1GJM']:
            d=self.candidates[id]
            self.assertFalse(d['meets_IL_le_0.30_and_both_H_ge_30'])
            self.assertGreater(d['refined_full_grid']['IL_db'],.3)
            self.assertGreaterEqual(d['refined_full_grid']['min_H2_db'],30)
            self.assertGreaterEqual(d['refined_full_grid']['min_H3_db'],30)
    def test_two_tunable_does_not_meet_target_in_saved_checkpoint(self):
        d=self.candidates['2CV_4L_1GJM']
        self.assertEqual(d['n_variable_C'],2)
        self.assertGreater(d['refined_full_grid']['IL_db'],.4)
        data=verify(d,pts=101,mna=True)
        self.assertGreater(data['IL'],.4)
    def test_20_percent_cost_tradeoff_independent(self):
        d=self.candidates['3CV_4L_0GJM_1PCB']
        self.assertAlmostEqual(d['chip_cost'],4)
        data=verify(d,pts=101,mna=True)
        self.assertGreater(data['IL'],.3)
        self.assertGreaterEqual(data['H2'],30)
        self.assertGreaterEqual(data['H3'],30)

if __name__=='__main__':unittest.main()