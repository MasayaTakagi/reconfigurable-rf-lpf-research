#!/usr/bin/env python3
"""Independent finite-grid baseline regression for current-policy LPF-007/008.

Recomputes coupled-inductor MNA and checks immutable reference metrics and
current component policy. This is NOT interval, optimizer-convergence, or EM
verification; the 0.30 dB design objective remains unmet.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lpf.circuit import Branch, solve
from lpf.configuration import validate_six_settings
from lpf.evaluate import CASES, evaluate_settings, load_bands
from lpf.independent import solve_gain
from lpf.validate import validate_couplings

# Intentionally independent of candidate JSON and candidate_index.csv. A
# modified baseline needs explicit review, not an automatically relaxed test.
BASELINE_PERFORMANCE = {
    "LPF-007": (0.5131684137962829, 35.06996955649531, 35.06999621989002),
    "LPF-008": (0.5185871257221822, 35.09999878063199, 35.09999507979744),
}
REGRESSION_TOL_DB = 1e-5  # finite-grid discretization and numeric BLAS tolerance


def read_candidate(name):
    return json.loads((ROOT / "candidates" / (name + ".json")).read_text(encoding="utf-8"))


def read_policy():
    return json.loads((ROOT / "data" / "design_constraints.json").read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def checked_number(value, name, lower=None, upper=None, strict_lower=False):
    number = float(value)
    require(math.isfinite(number), f"{name}: nonfinite")
    if lower is not None:
        require(number > lower if strict_lower else number >= lower, f"{name}: below lower limit")
    if upper is not None:
        require(number <= upper, f"{name}: above upper limit")
    return number


def check_baseline_metadata(item, policy):
    name = item["candidate_id"]
    require(name in BASELINE_PERFORMANCE, f"Unexpected baseline: {name}")
    require(item["spec_id"] == policy["policy_version"], f"{name}: outdated specification")
    require(item["objective"] == "full_lpf", f"{name}: not full_lpf")
    require(item["validation"]["global_optimality_proven"] is False,
            f"{name}: unsupported global optimality claim")
    require(item["validation"]["phase3_authorized"] is False, f"{name}: Phase 3 must stay paused")
    require(policy["phase3"] == "paused_until_explicit_owner_approval",
            "Phase 3 unexpectedly enabled")

    net = item["topology"]
    n_nodes = int(net["n_nodes"])
    require(n_nodes >= 2 and net["ground"] == 0, f"{name}: invalid nodes")
    require(1 <= net["input_node"] <= n_nodes and
            1 <= net["output_node"] <= n_nodes, f"{name}: invalid terminals")
    ls = net["inductors"]
    fs = net["fixed_caps"]
    vs = net["variable_caps"]
    counts = item["part_counts"]
    # LPF-007/008 specifically consist of four LQP02, three GJM01, zero
    # PCB-L and two ground-connected IC variable-C branches.
    require(counts == {"LQP02": 4, "LQP01": 0, "GJM01_fixed": 3,
                       "IC_variable_branches": 2, "PCB_L": 0},
            f"{name}: reference part counts changed")
    require(len(ls) == 4 and len(fs) == 3 and len(vs) == 2,
            f"{name}: reference branch count changed")
    require(len(set(x["id"] for x in ls + fs + vs)) == 9, f"{name}: duplicate branch IDs")
    for edge in ls + fs + vs:
        a, b = edge["a"], edge["b"]
        require(isinstance(a, int) and isinstance(b, int) and
                0 <= a <= n_nodes and 0 <= b <= n_nodes and a != b,
                f"{name}: invalid branch endpoints")
    ql = policy["components"]["LQP02"]["q"]
    qf = policy["components"]["GJM01"]["q"]
    qv = policy["components"]["IC_VARIABLE_C"]["q"]
    for v in ls:
        require(v["Q"] == ql, f"{name}: chip inductor Q changed")
        checked_number(v["L_nH"], name + ": L_nH", lower=0, strict_lower=True)
    for v in fs:
        require(v["Q"] == qf, f"{name}: fixed capacitor Q changed")
        checked_number(v["C_pF"], name + ": fixed C_pF", lower=0,
                       upper=policy["components"]["GJM01"]["max_pf_per_component"],
                       strict_lower=True)
    cpolicy = policy["components"]["IC_VARIABLE_C"]
    require(cpolicy["max_branches_principle"] == 2 and
            cpolicy["positions_allowed_by_default"] == ["shunt_to_ground"],
            "Variable-C policy changed")
    for v in vs:
        require(v["b"] == 0, f"{name}: variable capacitor not grounded")
        require(v["Q"] == qv and v["min_pF"] == cpolicy["min_total_variable_pf_per_branch"]
                and v["max_pF"] == cpolicy["max_total_variable_pf_per_branch"],
                f"{name}: variable capacitor specification changed")
    require(item["all_nonlisted_chip_couplings_zero"] is True,
            f"{name}: non-neighbor coupling claim changed")
    cap_values = item["ic_variable_C_pf_by_setting"]
    require(set(cap_values) == set(CASES), f"{name}: wrong six-setting mapping")
    for case, values in cap_values.items():
        require(len(values) == len(vs), f"{name}: {case} variable-C count changed")
        for v in values:
            checked_number(v, f"{name}/{case}: variable C",
                           lower=cpolicy["min_total_variable_pf_per_branch"],
                           upper=cpolicy["max_total_variable_pf_per_branch"])
    area = len(ls) * float(policy["components"]["LQP02"]["area_units"]) + (
        len(fs) * (2 / 3))
    require(abs(float(item["area_units"]) - area) < 1e-9 and
            area <= policy["area_budget"]["hard_cap"], f"{name}: area is inconsistent")
    for actual, expected in zip(
            (item["performance"]["worst_IL_db"], item["performance"]["min_H2_db"],
             item["performance"]["min_H3_db"]), BASELINE_PERFORMANCE[name]):
        require(abs(float(actual) - expected) <= REGRESSION_TOL_DB,
                f"{name}: saved reference metric changed")


def six_circuits(item, policy=None):
    policy = read_policy() if policy is None else policy
    check_baseline_metadata(item, policy)
    net = item["topology"]
    ls = net["inductors"]
    inductors = tuple(Branch(i["a"], i["b"], i["L_nH"] * 1e-9, i["Q"]) for i in ls)
    n = len(inductors)
    order = [int(v[1:]) for v in item["chip_physical_order"]]
    require(len(order) == n and sorted(order) == list(range(n)),
            f"{item['candidate_id']}: invalid chip row order")
    coupling_values = item["neighbor_k_values"]
    require(len(coupling_values) == n - 1, "Missing adjacent chip coupling")
    k = np.eye(n)
    for pos, value in enumerate(coupling_values):
        i, j = order[pos], order[pos + 1]
        k[i, j] = k[j, i] = checked_number(
            value, "k", lower=-policy["coupling_limits"]["chip_chip_strong_adjacent_abs_k_max"],
            upper=policy["coupling_limits"]["chip_chip_strong_adjacent_abs_k_max"])
    strong = [tuple(x) for x in item["strong_neighbor_pairs"]]
    errors = validate_couplings(k, ["chip"] * n, order, strong_pairs=strong, nominal=True)
    require(not errors, f"{item['candidate_id']}: invalid coupling: {errors}")
    require(float(np.linalg.eigvalsh(k).min()) > 0, "Coupling not positive definite")

    fixed_caps = tuple(Branch(c["a"], c["b"], c["C_pF"] * 1e-12, c["Q"])
                       for c in net["fixed_caps"])
    configs = {}
    for case in CASES:
        values = item["ic_variable_C_pf_by_setting"][case]
        var_caps = tuple(Branch(c["a"], c["b"], cv * 1e-12, c["Q"])
                         for c, cv in zip(net["variable_caps"], values))
        configs[case] = dict(
            n_nodes=net["n_nodes"], source_node=net["input_node"],
            load_node=net["output_node"], inductors=inductors,
            capacitors=fixed_caps + var_caps, coupling=k.copy(),
            source_voltage=1.0, source_ohms=float(policy["source_ohms"]["real"]),
            load_ohms=complex(policy["load_ohms"]["real"], policy["load_ohms"]["imag"]))
    require(policy["source_ohms"]["imag"] == 0 and
            policy["load_ohms"]["frequency_dependent"] is False,
            "Reference port convention changed")
    validate_six_settings(configs, variable_cap_indices=(len(fixed_caps), len(fixed_caps) + 1))
    return configs


def verify_baseline(name, samples_per_segment=401):
    policy = read_policy()
    item = read_candidate(name)
    require(item["candidate_id"] == name, f"{name}: candidate name mismatch")
    circuits = six_circuits(item, policy)
    result = evaluate_settings(lambda case: circuits[case],
                               samples_per_segment=samples_per_segment)
    observed = (result["worst_il_db"][0], result["min_h2_db"][0], result["min_h3_db"][0])
    expected = BASELINE_PERFORMANCE[name]
    for label, got, want in zip(("IL", "H2", "H3"), observed, expected):
        require(math.isfinite(got) and abs(got - want) <= REGRESSION_TOL_DB,
                f"{name}: {label} regression: calculated={got:.9f} reference={want:.9f}")
    require(observed[1] >= policy["evaluation"]["full_phase2"]["minimum_h2_h3_db"] and
            observed[2] >= policy["evaluation"]["full_phase2"]["minimum_h2_h3_db"],
            f"{name}: mandatory harmonic rejection failed")

    # Independently assembled nodal-admittance equation at one UL frequency
    # per setting: reject MNA sign/normalization regressions.
    bands = load_bands()
    mismatch = 0.0
    for case in CASES:
        ul = next(x for x in bands if x["case"] == case and x["region"] == "UL")
        f_hz = (float(ul["low_mhz"]) + float(ul["high_mhz"])) * 5e5
        cfg = circuits[case]
        a = solve(f_hz, **cfg)["gain"]
        b = solve_gain(f_hz, **cfg)
        mismatch = max(mismatch, abs(a - b))
    require(mismatch < 1e-9, f"{name}: independent nodal/MNA discrepancy")
    residual = max(v["max_abs_power_residual"]
                   for parts in result["per_case"].values() for v in parts.values())
    require(residual < 1e-10, f"{name}: power balance regression")
    return observed, mismatch, residual


def main():
    for name in BASELINE_PERFORMANCE:
        (il, h2, h3), mismatch, residual = verify_baseline(name)
        print(f"{name}: IL={il:.9f} dB, H2={h2:.9f} dB, H3={h3:.9f} dB, "
              f"independent gain mismatch={mismatch:.3g}, power residual={residual:.3g} W")
    print("PASS: reference-locked finite-grid regression; IL<=0.30dB remains unmet.")


if __name__ == "__main__":
    main()
