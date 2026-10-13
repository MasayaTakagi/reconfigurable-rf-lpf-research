#!/usr/bin/env python3
"""Audit historical EXP-022 RF-T004 checkpoints against canonical series-ESR model.

This is a reproducibility PASS audit for the archived nominal series-ESR model:
exit 0 means both checkpoints match the saved IL/H2/H3 metrics, with a separate
branch-current MNA check. Neither meets IL<=0.30dB. Physical/EM unverified.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.lpf.circuit import Branch, solve as branch_mna
from src.lpf.constraint_versions import load_constraint, constraint_fingerprint

CASES = ("B71", "B12", "B28", "B13+B14", "B26", "B8")
PAVS = 1 / 200
YL = 1 / (60 - 40j)


def incidence(edges):
    a = np.zeros((5, len(edges)), float)
    for i, (u, v) in enumerate(edges):
        if u != 0:
            a[u - 1, i] += 1
        if v != 0:
            a[v - 1, i] -= 1
    return a


def circuit_parts(candidate, cv):
    inductors = [Branch(u, v, L * 1e-9, 25)
                 for (u, v), L in zip(candidate["L_edges"], candidate["L_nH"])]
    capacitors = [Branch(u, v, C * 1e-12, Q)
                  for (u, v), C, Q in zip(
                      candidate["fixed_C_edges"] + candidate["variable_C_edges"],
                      candidate["fixed_C_pf"] + list(cv),
                      candidate["fixed_C_Q"] + [50] * 3)]
    physical_row = candidate["physical_row"]
    k = np.eye(len(inductors))
    for (u, v), value in zip(zip(physical_row, physical_row[1:]),
                             candidate["neighbor_k"]):
        a = int(u.removeprefix("L"))
        b = int(v.removeprefix("L"))
        k[a, b] = k[b, a] = value
    return inductors, capacitors, k


def vector_grid(f_mhz, inductors, capacitors, K):
    omega = np.asarray(f_mhz) * (2 * np.pi * 1e6)
    L = np.array([s.value for s in inductors])
    M = K * np.sqrt(np.outer(L, L))
    R = np.diag(L / 25)
    Z = omega[:, None, None] * (1j * M + R)[None, :, :]
    BL = incidence([(s.a, s.b) for s in inductors])
    BC = incidence([(s.a, s.b) for s in capacitors])
    cf = np.array([s.value for s in capacitors])
    Q = np.array([s.q for s in capacitors])
    # Canonical model in src/lpf/circuit.py:
    # Zc = (1/Q-j)/(omega*C), series-ESR loss, zero C means open.
    yc = omega[:, None] * cf[None, :] / (1 / Q[None, :] - 1j)
    Y = np.einsum("ia,fab,jb->fij", BL, np.linalg.inv(Z), BL)
    Y += np.einsum("ic,fc,jc->fij", BC, yc, BC)
    Y[:, 0, 0] += 1 / 50
    Y[:, 2, 2] += YL
    rhs = np.zeros((len(omega), 5), complex)
    rhs[:, 0] = 1 / 50
    v = np.linalg.solve(Y, rhs[..., None])[..., 0]
    gt = np.maximum(4 * 50 * YL.real * abs(v[:, 2]) ** 2, 1e-300)
    return -10 * np.log10(gt), v


def audit(candidate, rows):
    assert candidate["constraint_id"] == "RF-T004"
    assert len(candidate["L_edges"]) == 4
    assert len(candidate["variable_C_edges"]) == 3
    assert all(.4 <= value <= 27 for value in candidate["L_nH"])
    assert all(0 < x <= 100 for x in candidate["fixed_C_pf"][:3])
    assert .02 <= candidate["fixed_C_pf"][3] <= .2
    assert all(0 <= x <= 1.5
               for v in candidate["variable_C_pf_by_setting"].values()
               for x in v)
    assert candidate["chip_area_units"] == 6
    assert all(abs(v) <= .15 for v in candidate["neighbor_k"])
    worst, h2, h3 = -np.inf, np.inf, np.inf
    max_mna_error = max_energy_error = 0.
    samples = 0
    for row in rows:
        key = row["case"]
        cv = candidate["variable_C_pf_by_setting"][key]
        inductors, caps, K = circuit_parts(candidate, cv)
        assert np.linalg.eigvalsh(K).min() > 0
        low, high = float(row["low_mhz"]), float(row["high_mhz"])
        il, _ = vector_grid(np.linspace(low, high, 7001), inductors, caps, K)
        if row["type"] == "pass":
            worst = max(worst, float(np.max(il)))
        elif row["region"] == "H2":
            h2 = min(h2, float(np.min(il)))
        else:
            h3 = min(h3, float(np.min(il)))
        for f in (low, (low + high) / 2, high):
            _, v = vector_grid(np.array([f]), inductors, caps, K)
            independent = branch_mna(f * 1e6, 5, 1, 3,
                                      inductors, caps, K)
            max_mna_error = max(
                max_mna_error,
                float(np.max(abs(v[0] - independent["voltage"]))))
            max_energy_error = max(
                max_energy_error, abs(independent["power_residual"]))
            samples += 1
    observed = np.array([worst, h2, h3])
    original = np.array([candidate["worst_IL_db"],
                         candidate["min_H2_db"], candidate["min_H3_db"]])
    assert np.max(np.abs(observed - original)) < 2e-5, (observed, original)
    assert min(h2, h3) >= 30 - 1e-8
    assert worst > 0.30
    assert samples == 84 and max_mna_error < 1e-9
    assert max_energy_error < 1e-11
    return {"checkpoint": candidate["name"],
            "recomputed_max_IL_db": worst, "recomputed_min_H2_db": h2,
            "recomputed_min_H3_db": h3,
            "saved_metrics_match_canonical_model": True,
            "meets_minimum_30dB": min(h2, h3) >= 30,
            "meets_IL_0p30dB": worst <= .30,
            "independent_branch_MNA_points": samples,
            "max_voltage_difference_V": max_mna_error,
            "max_energy_residual_W": max_energy_error}


def main():
    policy = load_constraint("RF-T004", root=ROOT, allow_trial=True)
    actual = constraint_fingerprint(policy)
    required = "c66302a281a1fdb88da355fc44dac1ef3b1c4e18e8ff297db9e842b219b5b0c4"
    assert actual == required, (actual, required)
    with (ROOT / "data/bands.csv").open(encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for name in ("C-H30p0002", "C-H30p02"):
        candidate = json.loads((HERE / (name + ".json")).read_text(encoding="utf-8"))
        print(json.dumps(audit(candidate, rows), indent=2, ensure_ascii=False))
    print("AUDIT PASS: nominal saved metrics reproduce; IL 0.30dB unmet; physical model unverified.")


if __name__ == "__main__":
    main()
