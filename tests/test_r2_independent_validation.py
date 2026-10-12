import sys
import unittest
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from lpf.circuit import Branch,solve
from lpf.independent import solve_state
from lpf.validation import (solve_branch_current,validate_circuit,
                           validate_connection_map,validate_inductor_coupling)


def multi_inductor_bridge():
    inductors=(Branch(1,3,1.8e-9,25),Branch(3,2,2.4e-9,20),
               Branch(3,4,1.2e-9,25))
    capacitors=(Branch(3,0,.7e-12,80),Branch(4,0,0.0,80),
                Branch(1,4,.15e-12,80))
    coupling=np.eye(3)
    coupling[0,1]=coupling[1,0]=.22
    coupling[1,2]=coupling[2,1]=-.08
    return dict(n_nodes=4,source_node=1,load_node=2,
                inductors=inductors,capacitors=capacitors,coupling=coupling)


class IndependentFormulationTests(unittest.TestCase):
    def test_three_formulations_coupled_l_internal_zero_c_and_bridge(self):
        params=multi_inductor_bridge()
        report=validate_circuit(
            params,[617e6,703e6,1.5e9,2.5e9],
            expected_inductor_edges=[(1,3),(3,2),(3,4)],
            expected_capacitor_edges=[(3,0),(4,0),(1,4)],
            inductor_types=['LQP02HV','LQP02HQ','LQP02HV'],
            physical_order=[0,1,2])
        self.assertEqual(report['frequency_count'],4)
        self.assertLess(report['max_gain_discrepancy'],1e-10)
        self.assertGreater(report['min_inductance_eigenvalue'],0)
        self.assertLess(report['max_power_residual_w'],1e-12)
        primary=solve(703e6,**params)
        independent=solve_state(703e6,**params)
        third=solve_branch_current(703e6,**params)
        self.assertEqual(independent['capacitor_current'][1],0j)
        self.assertEqual(third['capacitor_current'][1],0j)
        self.assertLess(abs(primary['power_residual']),1e-12)
        self.assertAlmostEqual(primary['gain'],independent['gain'],delta=1e-10)

    def test_source_topology_map_is_checked_separately(self):
        params=multi_inductor_bridge()
        self.assertTrue(validate_connection_map(
            params,expected_inductor_edges=[(1,3),(3,2),(3,4)],
            expected_capacitor_edges=[(3,0),(4,0),(1,4)]))
        with self.assertRaisesRegex(ValueError,'connection map'):
            validate_connection_map(params,expected_inductor_edges=[(1,2),(2,3),(3,4)])

    def test_nonpositive_and_near_singular_full_l_matrix_rejected(self):
        params=multi_inductor_bridge()
        k=np.eye(3);k[0,2]=k[2,0]=.2
        with self.assertRaisesRegex(ValueError,'nonadjacent'):
            validate_inductor_coupling(['LQP02HV']*3,[1e-9]*3,k)
        near=np.eye(3);near[0,1]=near[1,0]=1-1e-13
        params['coupling']=near
        with self.assertRaisesRegex(ValueError,'ill-conditioned'):
            solve(700e6,**params)
        with self.assertRaisesRegex(ValueError,'ill-conditioned'):
            solve_state(700e6,**params)
        with self.assertRaisesRegex(ValueError,'ill-conditioned'):
            solve_branch_current(700e6,**params)

    def test_floating_internal_node_rejected_by_all_methods(self):
        params=dict(n_nodes=3,source_node=1,load_node=2,
                    inductors=(),capacitors=(),coupling=None)
        for method in (solve,solve_state,solve_branch_current):
            with self.subTest(method=method.__name__),self.assertRaisesRegex(
                    ValueError,'singular or ill-conditioned|ill-conditioned'):
                method(900e6,**params)

    def test_nonfinite_and_invalid_branches_are_rejected(self):
        params=multi_inductor_bridge()
        params['capacitors']=(Branch(4,4,.1e-12,80),)
        for method in (solve,solve_state,solve_branch_current):
            with self.subTest(method=method.__name__),self.assertRaises(ValueError):
                method(900e6,**params)
        with self.assertRaises(ValueError):
            solve(float('nan'),**multi_inductor_bridge())


if __name__=='__main__':
    unittest.main()
