#!/usr/bin/env python3
"""RF-T004 Phase-2 SLSQP epigraph refinement and independent MNA spot checks.
Run beside search_t004.py. Input JSON files are created by search_t004.py.
No assertion of global optimality or hardware/EM verification.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from search_t004 import Network


def refine(name, initial_values, stop_floor, grid=31, verify_grid=2001, iterations=300):
    net = Network(name, grid)
    x0 = np.asarray(initial_values, dtype=float)
    worst = net.metrics(x0, 31)['worst_il_db']
    x = np.r_[x0, worst + 0.10]
    cached = [None, None, None]

    def ensure(z):
        if cached[0] is None or not np.array_equal(cached[0], z):
            cached[0] = z.copy()
            cached[1:] = net.calculate(z[:-1], grad=True)

    def constraints(z):
        ensure(z)
        il = cached[1]
        return np.r_[z[-1] - il[net.passmask], il[net.stopmask] - stop_floor]

    def jacobian(z):
        ensure(z)
        j = cached[2]
        return np.vstack((
            np.c_[-j[net.passmask, :], np.ones(net.passmask.sum())],
            np.c_[j[net.stopmask, :], np.zeros(net.stopmask.sum())],
        ))

    optimized = minimize(
        lambda z: z[-1], x, method='SLSQP',
        jac=lambda z: np.r_[np.zeros(len(z) - 1), 1.0],
        bounds=net.bounds + [(0, 100)],
        constraints=[{'type': 'ineq', 'fun': constraints, 'jac': jacobian}],
        options={'maxiter': iterations, 'ftol': 1e-9},
    )
    final = optimized.x[:-1]
    metrics = net.metrics(final, verify_grid)
    validated = net.validate(final)
    return {
        'success_optimizer': bool(optimized.success),
        'status': str(optimized.message),
        'iterations': int(optimized.nit),
        'narrow_grid_points_per_interval': grid,
        'dense_grid_points_per_interval': verify_grid,
        'meets_stop_on_dense_grid': min(metrics['min_h2_db'], metrics['min_h3_db']) >= stop_floor - 0.025,
        'maximum_IL_db': metrics['worst_il_db'],
        'minimum_H2_db': metrics['min_h2_db'],
        'minimum_H3_db': metrics['min_h3_db'],
        'per_setting': metrics['per_setting'],
        'independent_checks': validated,
        'values': final.tolist(),
        'component_values': {
            'LQP02HV_nH': final[:net.nl].tolist(),
            'GJM01_or_PCB_pattern_C_pF': final[net.nl:net.nl + net.nf].tolist(),
            'IC_C_pF_by_setting': {
                case: final[net.nl + net.nf + 3 * i:net.nl + net.nf + 3 * (i + 1)].tolist()
                for i, case in enumerate(['B71', 'B12', 'B28', 'B13+B14', 'B26', 'B8'])
            },
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', nargs='+', required=True, help='Screen-result JSON files')
    ap.add_argument('--out', required=True, help='Refinement results JSON')
    ap.add_argument('--all-starts', action='store_true', help='Refine each recorded seed when available')
    ap.add_argument('--grid', type=int, default=31)
    ap.add_argument('--verify-grid', type=int, default=2001)
    ap.add_argument('--maxiter', type=int, default=300)
    args = ap.parse_args()
    allresults = {}
    for filepath in args.inputs:
        data = json.loads(Path(filepath).read_text())
        for name, info in data['results'].items():
            seeds = [(None, info['best']['x'])]
            if args.all_starts:
                seeds = [(q['start'], q['x']) for q in info['all_trial_summaries'] if 'x' in q] or seeds
            out = []
            for start, init in seeds:
                stages = {}
                x = init
                for target in (30.025, 35.025):
                    r = refine(name, x, target, args.grid, args.verify_grid, args.maxiter)
                    stages[f'{target:.3f}dB'] = r
                    x = r['values']
                out.append({'start': start, 'stages': stages})
                print(name, start,
                      [(x, round(v['maximum_IL_db'], 6), bool(v['success_optimizer']))
                       for x, v in stages.items()], flush=True)
            allresults[name] = {'topology': info['topology'], 'seeds': out}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(allresults, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
