import hashlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

from audit_exp015_common_model import PRIORITY,RUN,audit_candidate


class Exp015CommonModelTests(unittest.TestCase):
    def test_saved_values_replay_and_policy_fit_are_separate(self):
        digests={name:hashlib.sha256((RUN/(name+'.json')).read_bytes()).hexdigest()
                 for name in PRIORITY}
        for name in PRIORITY:
            with self.subTest(candidate=name):
                result=audit_candidate(name,replay_points=7001)
                replay=result['old_model_numerical_replay']
                self.assertEqual(replay['max_summary_metric_delta_db'],0.0)
                self.assertTrue(replay['matches_saved_within_tolerance'])
                independent=result['new_model_independent_spot_checks']
                self.assertEqual(independent['frequency_count'],72)
                self.assertLess(independent['max_gain_discrepancy'],1e-10)
                self.assertLess(independent['max_power_residual_w'],1e-12)
                self.assertGreater(independent['min_inductance_eigenvalue'],0)
                self.assertTrue(result['saved_candidate_values_unchanged'])
                self.assertGreaterEqual(result['performance_snapshot']['min_H2_db'],30)
                self.assertGreaterEqual(result['performance_snapshot']['min_H3_db'],30)
                self.assertLess(result['performance_snapshot']['min_H2_db'],35)
                self.assertLess(result['performance_snapshot']['min_H3_db'],35)
                policy=result['policy_fit']
                if '3C' in name:
                    self.assertTrue(policy['RF-T002']['topology_compliant'])
                    self.assertFalse(policy['RF-F001']['topology_compliant'])
                    self.assertFalse(policy['RF-T001']['topology_compliant'])
                else:
                    self.assertFalse(policy['RF-F001']['topology_compliant'])
                    self.assertFalse(policy['RF-T001']['topology_compliant'])
                    self.assertFalse(policy['RF-T002']['topology_compliant'])
                self.assertFalse(policy['RF-T002']['saved_worst_il_0p30db_pass'])
        for name,digest in digests.items():
            self.assertEqual(hashlib.sha256((RUN/(name+'.json')).read_bytes()).hexdigest(),digest)


if __name__=='__main__':
    unittest.main()
