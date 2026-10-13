"""RF-F002/RF-T004 topology search: placement freedom and current bounds."""
import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))

from lpf.constraint_versions import load_constraint
from lpf.circuit import solve
from lpf.independent import solve_gain
from search_space import enumerate_variable_c_layouts
from p4_batch import bounds_for, layout_candidates, settings_for


class CurrentPolicySearchTests(unittest.TestCase):
    def test_formal_and_trial_enumerate_free_positions_and_variable_counts(self):
        fixed_graph = (5, ((1,3,"LQP02HV"),(3,2,"LQP02HQ"),(3,4,"LQP02HV")))
        for cid, allow, cap in (("RF-F002", False, 2), ("RF-T004", True, 3)):
            policy = load_constraint(cid, allow_trial=allow)
            all_layouts = enumerate_variable_c_layouts(fixed_graph, policy)
            self.assertTrue(all_layouts)
            self.assertTrue(all(1 <= len(a["edges"]) <= cap for a in all_layouts))
            self.assertEqual({len(x["edges"]) for x in all_layouts}, set(range(1,cap+1)))
            self.assertTrue(any("bridge" in x["roles"] for x in all_layouts))
            self.assertTrue(any("series" in x["roles"] for x in all_layouts))
            self.assertTrue(any(0 in edge for x in all_layouts for edge in x["edges"]))
            self.assertTrue(all(a["edges"] for a in enumerate_variable_c_layouts(
                fixed_graph, policy, max_layouts=32)))
            self.assertLessEqual(len(enumerate_variable_c_layouts(
                fixed_graph, policy, max_layouts=32)), 32)

    def test_actual_series_only_path_instantiates_in_six_settings(self):
        # Fixed L path terminates at node 3. Series C completes path 3-to-2.
        graph=(4, ((1,3,"LQP02HV"),))
        for cid, allow in (("RF-F002",False), ("RF-T004",True)):
            policy=load_constraint(cid,allow_trial=allow)
            layouts=enumerate_variable_c_layouts(graph,policy)
            self.assertTrue(any((3,2) in l["edges"] or (2,3) in l["edges"]
                                for l in layouts if "series" in l["roles"]))
            layout={"edges":((3,2),(3,0)), "roles":("series",None)}
            x=np.asarray([2.0]+[.5,.2]*6)
            configs=settings_for(graph,x,np.eye(1),variable_layout=layout,
                                 resolved_policy=policy,require_explicit_series=True)
            for cfg in configs.values():
                self.assertEqual(cfg["capacitors"][0].q, 50)
                self.assertAlmostEqual(cfg["capacitors"][0].value, 0.5e-12)
                primary=solve(700e6,**cfg)
                self.assertAlmostEqual(primary["gain"], solve_gain(700e6,**cfg),
                                       delta=1e-10)

    def test_new_limits_are_applied_to_search_bounds_and_couplings(self):
        graph=(4,((1,3,"PCB_L"),(3,2,"LQP02HV")))
        for cid,allow,cap in (("RF-F002",False,2),("RF-T004",True,3)):
            policy=load_constraint(cid,allow_trial=allow)
            bounds=bounds_for(graph,variable_count=cap,resolved_policy=policy)
            self.assertEqual(bounds[0],(.3,2.0))
            self.assertTrue(all(value==(0.0,1.5) for value in bounds[2:]))
        graph=(3,((1,2,"LQP02HV"),(1,2,"LQP02HV"),
                  (1,2,"PCB_L"),(1,2,"PCB_L")))
        layouts=layout_candidates(graph,20,resolved_policy=load_constraint())
        self.assertGreaterEqual(len(layouts),5)
        self.assertTrue(all(np.linalg.eigvalsh(k).min()>0 for k in layouts))
        self.assertTrue(all(abs(k[0,1]) <= .15+1e-12 and
                            abs(k[2,3]) <= .15+1e-12 for k in layouts))
        self.assertTrue(all(np.allclose(k[:2,2:],0) for k in layouts))


if __name__ == "__main__":
    unittest.main()
