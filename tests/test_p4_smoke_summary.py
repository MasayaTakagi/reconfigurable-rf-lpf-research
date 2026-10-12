import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from summarize_p4_smoke import summarize


class P4SmokeSummaryTests(unittest.TestCase):
    def test_candidate_outcomes_and_runtime_provenance(self):
        payload={
            'run_config':{
                'analysis_mode':'matching_only',
                'p4_a_limits':{'constraint_id':'RF-T002',
                               'effective_constraint_sha256':'abc123'},
                'topology_search':{'seed':17},
                'numeric_environment':{'python_version':'3.12','numpy':'2.0',
                    'scipy':'1.14','blas_lapack':{'blas':'openblas'},
                    'thread_environment':{'OPENBLAS_NUM_THREADS':'1'}},
                'frequency_grid_mhz':{'B71':[617.0,698.0]},
                'rf_design_constraints':{'evaluation':{'full_phase2':{
                    'minimum_h2_h3_db':30,'nominal_h2_h3_target_db':35}}},
                'optimization':{'method':'SLSQP','iterations':2,
                    'coarse_points_per_band_segment':2,
                    'validation_points_per_band_segment':3},
            },
            'expected_graph_ids':['g1','g2'],
            'completed_graph_ids':['g1'],
            'unit_execution_log':[{'graph_id':'g2','status':'failed'}],
            'results':[{'graph':[3,[[1,2,'LQP02HV']]],
                        'validation':{'min_h2_db':29.0,'min_h3_db':36.0},
                        'optimization_runs':[{'candidate_key':'c1',
                            'objective_evaluation_count':8,'converged':True,
                            'variable_cap_edges':[[1,0],[2,0]]},
                            {'candidate_key':'c2','objective_evaluation_count':5,
                             'converged':False,'variable_cap_edges':[[1,0],[2,0]]}]}],
            'candidate_execution_log':[{'candidate_key':'c1','status':'completed',
                                          'objective_evaluation_count':8},
                                       {'candidate_key':'c2','status':'completed',
                                          'objective_evaluation_count':5}],
            'interrupted_candidate_attempts':[{'candidate_key':'c3',
                'status':'failed_will_replay','objective_evaluation_count':4}],
            'partial_optimization_runs':{},
            'planned_optimizer_candidates':4,
            'completed_optimizer_candidates':2,
            'source_commit':'feedface','status':'failed','resume_count':1,
        }
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'checkpoint.json'
            path.write_text(json.dumps(payload),encoding='utf-8')
            result=summarize(path,'smoke-checkpoint')
        self.assertEqual(result['source_commit_sha'],'feedface')
        self.assertEqual(result['effective_constraint_sha256'],'abc123')
        self.assertEqual(result['inductor_series'],['LQP02HV'])
        self.assertEqual(result['optimization']['successful_optimizer_candidates'],2)
        self.assertEqual(result['optimization']['failed_optimizer_candidates'],1)
        self.assertEqual(result['optimization']['unrun_optimizer_candidates'],1)
        self.assertEqual(result['optimization']['optimizer_converged_candidates'],1)
        self.assertEqual(result['optimization']['optimizer_nonconverged_candidates'],1)
        self.assertEqual(result['optimization']['objective_evaluations_including_interrupted_attempts'],17)
        self.assertEqual(result['optimization']['failed_graphs'],1)
        self.assertEqual(result['optimization']['unrun_graphs'],0)
        self.assertEqual(result['performance_observation']['minimum_h2_h3_db'],30)
        self.assertEqual(result['performance_observation']['nominal_h2_h3_target_db'],35)
        self.assertEqual(result['performance_observation']['observed_minimum_h2_db'],29.0)
        self.assertFalse(result['performance_observation']['full_phase2_pass_claimed'])


if __name__=='__main__':
    unittest.main()
