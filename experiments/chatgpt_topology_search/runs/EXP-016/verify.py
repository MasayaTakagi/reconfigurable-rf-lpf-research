#!/usr/bin/env python3
"""Independently verify archived EXP-016 RF-T004 Phase-2 checkpoints.

Uses nodal admittance over *each* band segment and a separate branch-current
MNA formulation at segment endpoints and midpoints. Does not perform
optimization or claim physical feasibility, Q(f), SRF or EM verification.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lpf.constraint_versions import load_constraint, constraint_fingerprint

HERE = Path(__file__).resolve().parent
INPUT = json.loads((HERE / "checkpoints.json").read_text(encoding="utf-8"))
BANDS = list(csv.DictReader((ROOT / "data/bands.csv").open(encoding="utf-8")))
CASES = ["B71", "B12", "B28", "B13+B14", "B26", "B8"]
R_SOURCE, Z_LOAD = 50., 60.-40.j
Y_LOAD = 1 / Z_LOAD
P_AVS = 1 / (4 * R_SOURCE)
COM = INPUT["main_circuit_edges"]
N = 5


def edge_matrix(edges):
    out = np.zeros((N, len(edges)))
    for i, (a, b) in enumerate(edges):
        out[a, i] = 1
        if b != -1:
            out[b, i] = -1
    return out


def evaluate_at_frequency(fs_mhz, checkpoint, variable_c):
    fs = np.atleast_1d(np.asarray(fs_mhz, float))
    omega = 2 * np.pi * fs * 1e6
    L = np.asarray(checkpoint["L_nH"], float)
    CF = np.asarray(checkpoint["fixed_C_pF"], float)
    CV = np.asarray(variable_c, float)
    Q = np.asarray(checkpoint["Q_L"], float)
    E = COM["L"] + COM["fixed_C_edges"] + checkpoint["variable_C_edges"]
    B = edge_matrix(E)
    yL = 1 / (omega[:, None] * L[None, :] * 1e-9
              * (1j + 1 / Q[None, :]))
    # ESR model: Z_C = (1/Q - j)/(omega*C), including correct zero-C open.
    yF = omega[:, None] * CF[None, :] * 1e-12 / (1 / 80 - 1j)
    yV = omega[:, None] * CV[None, :] * 1e-12 / (1 / 50 - 1j)
    y = np.concatenate([yL, yF, yV], axis=1)
    Y = np.einsum("fb,ib,jb->fij", y, B, B, optimize=True)
    Y[:, COM["source_node"], COM["source_node"]] += 1 / R_SOURCE
    Y[:, COM["load_node"], COM["load_node"]] += Y_LOAD
    rhs = np.zeros((len(fs), N), complex)
    rhs[:, COM["source_node"]] = 1 / R_SOURCE
    V = np.linalg.solve(Y, rhs)
    gt = np.maximum(4 * R_SOURCE * Y_LOAD.real * abs(V[:, 3])**2, 1e-300)
    return -10 * np.log10(gt), V, y, B


def check_branch_mna(f, checkpoint, cv, v_nodal):
    _, _, y, B = evaluate_at_frequency([f], checkpoint, cv)
    active = abs(y[0]) > 1e-25
    y = y[0, active]
    B = B[:, active]
    z = 1 / y
    m = len(z)
    A = np.zeros((N + m, N + m), complex)
    A[:N, N:] = B
    A[N:, :N] = B.T
    A[N:, N:] = -np.diag(z)
    A[0, 0] = 1 / R_SOURCE
    A[3, 3] = Y_LOAD
    r = np.zeros(N + m, complex)
    r[0] = 1 / R_SOURCE
    sol = np.linalg.solve(A, r)
    vv, ii = sol[:N], sol[N:]
    p_src = np.real((1 - vv[0]) / R_SOURCE)
    p_res_src = abs((1 - vv[0]) / R_SOURCE)**2 * R_SOURCE
    p_branch = float(np.sum(abs(ii)**2 * np.real(z)))
    p_load = abs(vv[3])**2 * Y_LOAD.real
    return (float(np.max(abs(vv - v_nodal))),
            float(abs(p_src - p_res_src - p_branch - p_load)),
            float(max(0, p_load - P_AVS)))


def verify_checkpoint(cp, policy):
    L = np.asarray(cp["L_nH"])
    CF = np.asarray(cp["fixed_C_pF"])
    C = cp["variable_C_pF_by_case"]
    assert len(L) == 4 and len(CF) == 4
    assert len(cp["Q_L"]) == 4
    assert np.all(L > 0) and np.all((CF > 0) & (CF <= 100))
    assert len(cp["variable_C_edges"]) == 3 and set(C) == set(CASES)
    assert all(len(C[c]) == 3 and all(0 <= v <= 1.5 for v in C[c])
               for c in CASES)
    assert all(q in (25, 33) for q in cp["Q_L"])
    assert all(q != 25 or .4 <= l <= 27
               for l, q in zip(L, cp["Q_L"]))
    assert policy["components"]["IC_VARIABLE_C"]["q"] == 50
    assert policy["components"]["IC_VARIABLE_C"]["max_branches_principle"] == 3
    count33 = cp["Q_L"].count(33)
    area = 4 + 2 * count33 + 4 * 2 / 3
    assert abs(area - cp["area_units"]) < 1e-9

    intervals = [r for r in BANDS if r["case"] in CASES]
    summary = {ca: {"worst_il_db": -np.inf, "min_h2_db": np.inf,
                    "min_h3_db": np.inf} for ca in CASES}
    diff = bal = excess = 0.
    mna_count = 0
    for r in intervals:
        ca = r["case"]
        lo, hi = float(r["low_mhz"]), float(r["high_mhz"])
        freqs = np.linspace(lo, hi, 7001)
        il, _, _, _ = evaluate_at_frequency(freqs, cp, C[ca])
        if r["type"] == "pass":
            summary[ca]["worst_il_db"] = max(summary[ca]["worst_il_db"],
                                              float(max(il)))
        else:
            k = "min_" + r["region"].lower() + "_db"
            summary[ca][k] = min(summary[ca][k], float(min(il)))
        for f in [lo, (lo+hi)/2, hi]:
            _, v, _, _ = evaluate_at_frequency([f], cp, C[ca])
            d, p, x = check_branch_mna(f, cp, C[ca], v[0])
            diff, bal, excess = max(diff, d), max(bal, p), max(excess, x)
            mna_count += 1
    worst = max(d["worst_il_db"] for d in summary.values())
    h2 = min(d["min_h2_db"] for d in summary.values())
    h3 = min(d["min_h3_db"] for d in summary.values())
    for key, val in [("worst_IL_db", worst), ("min_H2_db", h2),
                     ("min_H3_db", h3)]:
        assert abs(val - cp["reference_metrics"][key]) < 5e-5, (key, val)
    assert diff < 1e-9 and bal < 1e-11 and excess < 1e-11
    assert min(h2, h3) + 1e-5 >= cp["goal_harmonics_db"]
    return dict(worst_IL_db=worst, min_H2_db=h2, min_H3_db=h3,
                independent_MNA_probes=mna_count, max_voltage_diff=diff,
                max_energy_balance_W=bal, max_passivity_excess_W=excess,
                full_L_matrix_min_eigenvalue_nH=float(min(L)),
                setting_metrics=summary)


def main():
    policy = load_constraint("RF-T004", root=ROOT, allow_trial=True)
    print("Effective RF-T004 constraint SHA256:",
          constraint_fingerprint(policy))
    for cp in INPUT["candidates"]:
        report = verify_checkpoint(cp, policy)
        print(cp["id"], json.dumps(report, ensure_ascii=False))
    print("Numerical checks PASS. Q(f), physical part L range, SRF, "
          "parasitics, layout and EM remain UNVERIFIED.")


if __name__ == "__main__":
    main()
