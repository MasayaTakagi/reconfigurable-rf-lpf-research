#!/usr/bin/env python3
"""EXP-045 RF-T005 added PCB pattern capacitor original-S2P plus independent MNA.

Recalculate 3L T-type plus third PCB pattern capacitor, 28 intervals x 1001 points,
then independently check LPF two-port Y and cascaded external IL at 84 probes.
Original S2Ps are hash-verified by lpf.port_parasitics. Phase 2 only.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
from lpf.constraint_versions import load_constraint
from lpf.port_parasitics import external_transducer_gain

CASE_ORDER = ("B71", "B12", "B28", "B13+B14", "B26", "B8")
L_EDGES = ((0, 1), (1, 2), (1, 3))
C_EDGES = ((0, 1), (1, 2), (3, -1), (1, 2), (3, -1), (0, 1), (1, 2))
C_Q = np.array([40., 40., 80., 40., 35., 35., 35.])
PORT = [0, 2]
INNER = [1, 3]


def incidence(edges):
    b = np.zeros((4, len(edges)), dtype=float)
    for j, (p, n) in enumerate(edges):
        b[p, j] = 1.
        if n >= 0:
            b[n, j] = -1.
    return b


BL = incidence(L_EDGES)
BC = incidence(C_EDGES)


def coupled_L_matrix(x):
    L = x[:3]
    mat = np.diag(L.copy())
    mat[0, 2] = mat[2, 0] = x[6] * np.sqrt(L[0] * L[2])
    mat[1, 2] = mat[2, 1] = x[7] * np.sqrt(L[1] * L[2])
    return mat


def capacitor_admittance(x, case_idx, omega):
    cap = np.r_[x[3:6], .2, x[8 + 3 * case_idx:11 + 3 * case_idx]]
    ybranch = omega * (cap * 1.e-12) / (1. / C_Q - 1.j)
    return BC @ np.diag(ybranch) @ BC.T


def port_admittance(x, case_idx, f_mhz, *, explicit_mna=False):
    omega = 2. * np.pi * f_mhz * 1.e6
    zl = omega * 1.e-9 * (np.diag(x[:3] / 25.) + 1j * coupled_L_matrix(x))
    yc = capacitor_admittance(x, case_idx, omega)
    if not explicit_mna:
        yn = yc + BL @ np.linalg.solve(zl, BL.T)
        p = yn[np.ix_(PORT, PORT)]
        u = yn[np.ix_(PORT, INNER)]
        v = yn[np.ix_(INNER, PORT)]
        h = yn[np.ix_(INNER, INNER)]
        return p - u @ np.linalg.solve(h, v)

    # Independent formulation: unknown voltages at interior nodes and
    # all three coupled inductor branch currents (5 unknowns per excitation).
    block = np.block([
        [yc[np.ix_(INNER, INNER)], BL[INNER, :]],
        [BL[INNER, :].T, -zl]
    ])
    port_y = np.zeros((2, 2), dtype=complex)
    for excite in range(2):
        vp = np.zeros(2, dtype=complex)
        vp[excite] = 1.
        rhs = -np.r_[yc[np.ix_(INNER, PORT)] @ vp, BL[PORT, :].T @ vp]
        sol = np.linalg.solve(block, rhs)
        port_y[:, excite] = (
            yc[np.ix_(PORT, PORT)] @ vp
            + yc[np.ix_(PORT, INNER)] @ sol[:2]
            + BL[PORT, :] @ sol[2:]
        )
    return port_y


def port_abcd(y):
    a, b, c, d = y[0, 0], y[0, 1], y[1, 0], y[1, 1]
    if abs(c) < 1.e-20:
        raise ValueError("Singular LPF 2-port")
    return np.array([[-d / c, -1. / c], [-(a * d - b * c) / c, -a / c]])


def total_attenuation(policy, x, case_idx, f_mhz, *, explicit=False):
    y = port_admittance(x, case_idx, f_mhz, explicit_mna=explicit)
    gt = external_transducer_gain(policy, f_mhz * 1.e6, port_abcd(y), root=ROOT)
    if not (np.isfinite(gt) and 0. < gt <= 1. + 1.e-8):
        raise ValueError("Invalid gain, possible passivity or topology failure")
    return -10. * np.log10(gt), y


def check_bounds(x, policy):
    assert x.shape == (26,)
    assert np.all((x[:3] >= .4) & (x[:3] <= 27.))
    assert .02 <= x[3] <= .2 and .02 <= x[4] <= .2
    assert 0. < x[5] <= 100.
    assert policy["components"]["PCB_PATTERN_C"]["max_count"] >= 3
    assert policy["components"]["PCB_PATTERN_C"]["min_pf_per_component"] <= .2 <= policy["components"]["PCB_PATTERN_C"]["max_pf_per_component"]
    assert np.all(np.abs(x[6:8]) <= .1 + 1.e-12)
    assert np.all((x[8:] >= 0) & (x[8:] <= 3. + 1.e-12))
    assert policy["components"]["IC_VARIABLE_C"]["q"] == 35
    assert policy["components"]["IC_VARIABLE_C"]["max_branches_principle"] == 3
    if np.linalg.eigvalsh(coupled_L_matrix(x))[0] <= 0.:
        raise ValueError("Coupled L matrix is not positive definite")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=int, default=1001)
    a = parser.parse_args()
    if a.points < 3:
        raise ValueError("At least 3 samples per CSV segment required")
    policy = load_constraint("RF-T005", root=ROOT, allow_trial=True)
    checkpoint = json.loads((HERE / "checkpoints/t3l_extra_pcb_out_0p2_prelim.json").read_text())
    x = np.asarray(checkpoint["vector"], dtype=float)
    check_bounds(x, policy)

    with (ROOT / "data" / "bands.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 28:
        raise ValueError("Unexpected number of band rows")

    maxima = {"pass": (-np.inf, None), "H2": (np.inf, None), "H3": (np.inf, None)}
    max_y_error = 0.
    max_il_error = 0.
    min_passivity = np.inf
    count = 0
    for band in rows:
        case_idx = CASE_ORDER.index(band["case"])
        low = float(band["low_mhz"])
        high = float(band["high_mhz"])
        role = "pass" if band["type"] == "pass" else band["region"]
        for j, f_mhz in enumerate(np.linspace(low, high, a.points)):
            il, y = total_attenuation(policy, x, case_idx, float(f_mhz))
            value, _ = maxima[role]
            loc = {"case": band["case"], "region": band["region"], "f_mhz": float(f_mhz)}
            if ((role == "pass" and il > value)
                or (role != "pass" and il < value)):
                maxima[role] = (float(il), loc)
            if j in (0, (a.points - 1) // 2, a.points - 1):
                il2, y2 = total_attenuation(policy, x, case_idx, float(f_mhz),
                                            explicit=True)
                max_y_error = max(max_y_error, float(np.max(np.abs(y - y2))))
                max_il_error = max(max_il_error, abs(il - il2))
                min_passivity = min(min_passivity,
                    float(np.linalg.eigvalsh((y2 + y2.conj().T) / 2.)[0]))
                count += 1

    result = {
        "constraint": "RF-T005",
        "source": "two original SHA-verified RF-F003 S2Ps",
        "segments": 28, "samples_per_segment": a.points,
        "worst_IL_dB": maxima["pass"][0],
        "minimum_H2_dB": maxima["H2"][0],
        "minimum_H3_dB": maxima["H3"][0],
        "locations": {key: item[1] for key, item in maxima.items()},
        "independent_MNA_probes": count,
        "maximum_2port_Y_discrepancy_S": max_y_error,
        "maximum_independent_external_IL_discrepancy_dB": max_il_error,
        "minimum_port_Y_dissipation_eigenvalue_S": min_passivity,
        "minimum_L_matrix_eigenvalue_nH": float(
            np.linalg.eigvalsh(coupled_L_matrix(x))[0])
    }
    if a.points == 1001:
        expected = checkpoint["metrics"]
        for observed, required in [
            (result["worst_IL_dB"], expected["worst_IL_db"]),
            (result["minimum_H2_dB"], expected["min_H2_db"]),
            (result["minimum_H3_dB"], expected["min_H3_db"])
        ]:
            if abs(observed - required) > 1.e-7:
                raise AssertionError(f"Failed archived-grid regression: {observed} != {required}")
    assert max_y_error < 1.e-10 and max_il_error < 1.e-8
    assert min_passivity > -1.e-12
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
