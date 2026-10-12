#!/usr/bin/env python3
"""Reproduce EXP-016 selected numerical candidate metrics under main RF-F001.

Phase 2 lumped constant-Q model; this does not rerun local multistart search.
Each disconnected B13+B14 frequency interval is evaluated separately.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from lpf.circuit import Branch, solve
from lpf.independent import solve_gain
from lpf.evaluate import CASES, evaluate_settings

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "validation" / "exp016_20261012" / "candidates.json"

def parameters(candidate, case):
    ind = tuple(Branch(int(a), int(b), float(L)*1e-9, float(q))
        for (a,b), L, q in zip(candidate["inductor_edges"],
            candidate["L_nH"], candidate["inductor_Q"]))
    edges = candidate["fixed_C_edges"] + candidate["variable_C_edges"]
    values = candidate["fixed_C_pf"] + candidate["variable_C_pf_by_setting"][case]
    caps = tuple(Branch(int(a), int(b), float(v)*1e-12, 80.0)
        for (a,b),v in zip(edges,values))
    k = np.eye(len(ind))
    row = candidate["chip_physical_order"]
    for index, val in enumerate(candidate["neighbor_k"]):
        a,b = row[index:index+2]
        k[a,b] = k[b,a] = float(val)
    if np.linalg.eigvalsh(k).min() <= 0:
        raise ValueError("Non-SPD coupling")
    return dict(n_nodes=5, source_node=1, load_node=3,
        inductors=ind, capacitors=caps, coupling=k,
        source_voltage=1.0, source_ohms=50.0, load_ohms=60-40j)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=201)
    options = parser.parse_args()
    for c in json.loads(DATA.read_text())["results"]:
        def make(case): return parameters(c,case)
        evaluated = evaluate_settings(make, samples_per_segment=options.samples)
        worst = evaluated["worst_il_db"][0]
        h2, h3 = evaluated["min_h2_db"][0], evaluated["min_h3_db"][0]
        largest_mna_delta, largest_balance = 0.0, 0.0
        for case in CASES:
            pars = make(case)
            for f_mhz in (698.0, 803.0, 960.0, 1450.0, 2100.0, 2700.0):
                main_result = solve(f_mhz*1e6, **pars)
                independent_gain = solve_gain(f_mhz*1e6, **pars)
                difference = abs(main_result["il_db"]+10*np.log10(independent_gain))
                largest_mna_delta = max(largest_mna_delta, difference)
                largest_balance = max(largest_balance, abs(main_result["power_residual"]))
        assert largest_mna_delta < 1e-8
        assert largest_balance < 1e-12
        assert h2 >= 35-1e-6 and h3 >= 35-1e-6
        print(json.dumps({"candidate_id":c["id"],"samples":options.samples,
            "worst_IL_db":worst,"min_H2_db":h2,"min_H3_db":h3,
            "max_independent_difference_db":largest_mna_delta,
            "max_power_residual_W":largest_balance},ensure_ascii=False))

if __name__ == "__main__":
    main()
