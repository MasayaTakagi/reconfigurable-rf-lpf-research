#!/usr/bin/env python3
"""Recompute new-policy PCB-free LPF-007/008 with the repository's generic MNA.

This verifies finite grids only, NOT continuous-band/global/EM realizability.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lpf.circuit import Branch, solve
from lpf.configuration import validate_six_settings
from lpf.evaluate import CASES, evaluate_settings
from lpf.validate import validate_couplings


def read_candidate(name):
    return json.loads((ROOT / "candidates" / (name + ".json")).read_text(encoding="utf-8"))


def six_circuits(item):
    net = item["topology"]
    lraw = net["inductors"]
    inductors = tuple(Branch(i["a"], i["b"], i["L_nH"] * 1e-9, i["Q"]) for i in lraw)
    n = len(inductors)
    order = [int(v[1:]) for v in item["chip_physical_order"]]
    k = np.eye(n)
    for pos, value in enumerate(item["neighbor_k_values"]):
        i = order[pos]
        j = order[pos + 1]
        k[i,j] = k[j,i] = float(value)
    strong = [tuple(x) for x in item["strong_neighbor_pairs"]]
    errors = validate_couplings(k, ["chip"] * n, order, strong_pairs=strong, nominal=True)
    if errors:
        raise AssertionError((item["candidate_id"],errors))
    fixed_caps = tuple(
        Branch(c["a"], c["b"], c["C_pF"] * 1e-12, c["Q"])
        for c in net["fixed_caps"]
    )
    configs = {}
    for case in CASES:
        cc = list(item["ic_variable_C_pf_by_setting"][case])
        var_caps = [
            Branch(c["a"], c["b"], cv * 1e-12, c["Q"])
            for c,cv in zip(net["variable_caps"],cc)
        ]
        configs[case] = dict(
            n_nodes=net["n_nodes"],
            source_node=net["input_node"],
            load_node=net["output_node"],
            inductors=inductors,
            capacitors=fixed_caps + tuple(var_caps),
            coupling=k.copy(),
            source_voltage=1.0,
            source_ohms=50.0,
            load_ohms=60 - 40j
        )
    validate_six_settings(configs, variable_cap_indices=(len(fixed_caps), len(fixed_caps)+1))
    cost = n + len(fixed_caps)*2/3
    if cost > 6.0 + 1e-10:
        raise AssertionError("Area cost exceeded")
    return configs


def main():
    for name in ("LPF-007", "LPF-008"):
        item = read_candidate(name)
        circuits = six_circuits(item)
        r = evaluate_settings(lambda case: circuits[case], samples_per_segment=401)
        il = r["worst_il_db"][0]
        h2 = r["min_h2_db"][0]
        h3 = r["min_h3_db"][0]
        maxerr = max(v["max_abs_power_residual"]
                     for part in r["per_case"].values() for v in part.values())
        if not (il < 0.55 and h2 >= 35.0 and h3 >= 35.0 and maxerr < 1e-10):
            raise AssertionError((name, il, h2, h3, maxerr))
        print("%s: IL=%.9f dB, H2=%.9f dB, H3=%.9f dB, residual=%.3g W" %
              (name, il, h2, h3, maxerr))
    print("PASS: finite-grid verification only; the IL<=0.30dB objective remains unmet.")


if __name__ == "__main__":
    main()
