#!/usr/bin/env python3
"""Independent 9x9 branch-current MNA validation of RF-T004 EXP-018 checkpoints.
Run at repository root: python experiments/chatgpt_topology_search/runs/EXP-018/verify.py
This verifies the same finite constant-Q lumped model; not SRF/Q(f)/EM.
"""
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BANDS = list(csv.DictReader((ROOT / "data/bands.csv").open(encoding="utf-8", newline="")))
CASES = ("B71", "B12", "B28", "B13+B14", "B26", "B8")


def incidence(edges, n=5):
    a = np.zeros((len(edges), n))
    for i, (u, v) in enumerate(edges):
        if u:
            a[i, u - 1] += 1
        if v:
            a[i, v - 1] -= 1
    return a


def verify(filename):
    d = json.loads(Path(filename).read_text(encoding="utf-8"))
    assert d["constraint_id"] == "RF-T004"
    assert d["series"] == ["HV"] * 4
    assert len(d["Cvar_pF"]) == 6
    assert d["fix_types"].count("GJM") == 3
    assert d["fix_types"].count("PCB") <= 3
    assert d["chip_area_cost"] == 6
    L = np.array(d["L_nH"]) * 1e-9
    k = np.array(d["neighbor_k"])
    assert np.all((L >= .4e-9) & (L <= 27e-9 + 1e-17))
    assert np.all(np.abs(k) <= .15 + 1e-9)
    M = np.diag(L.copy())
    K = np.eye(4)
    for coef, a, b in zip(k, d["row"], d["row"][1:]):
        M[a, b] = M[b, a] = coef * np.sqrt(L[a] * L[b])
        K[a, b] = K[b, a] = coef
    keig = float(np.linalg.eigvalsh(K).min())
    assert keig > 0
    Z = np.diag(L / 25) + 1j * M
    B = incidence(d["L_edges"]).T
    E = incidence(d["fix_edges"] + d["cv_edges"])
    cf = np.array(d["fixed_C_pF"]) * 1e-12
    for c, kind in zip(cf, d["fix_types"]):
        assert (.02e-12 - 1e-22 <= c <= .2e-12 + 1e-22) if kind == "PCB" else (0 <= c <= 100e-12)
    q = np.array([80. if x == "GJM" else 40. for x in d["fix_types"]] + [50.] * 3)
    qfac = 1 / (1 / q - 1j)
    port = np.zeros((5, 5), complex)
    port[0, 0] = 1 / 50
    port[2, 2] = 1 / (60 - 40j)
    src = np.array([1 / 50, 0, 0, 0, 0, 0, 0, 0, 0], complex)
    worst = [-1e6, 1e6, 1e6]
    power_err = 0.
    voltage_err = 0.
    for case in CASES:
        cv = np.array(d["Cvar_pF"][case]) * 1e-12
        assert np.all((cv >= -1e-20) & (cv <= 1.5e-12 + 1e-20))
        C = np.r_[cf, cv]
        Y = E.T @ np.diag(C * qfac) @ E
        for band in BANDS:
            if band["case"] != case:
                continue
            omega = 2e6 * np.pi * np.linspace(float(band["low_mhz"]), float(band["high_mhz"]), 7001)
            A = np.zeros((len(omega), 9, 9), complex)
            A[:, :5, :5] = port[None, :, :] + omega[:, None, None] * Y[None, :, :]
            A[:, :5, 5:] = B[None, :, :]
            A[:, 5:, :5] = B.T[None, :, :]
            A[:, 5:, 5:] = -omega[:, None, None] * Z[None, :, :]
            sol = np.linalg.solve(A, np.broadcast_to(src, (len(omega), 9))[:, :, None])[:, :, 0]
            val = -10 * np.log10(np.maximum(200 * 60 / 5200 * np.abs(sol[:, 2]) ** 2, 1e-290))
            typ = band["region"]
            idx = 0 if typ in ("UL", "DL") else 1 if typ == "H2" else 2
            if idx == 0:
                worst[idx] = max(worst[idx], float(val.max()))
            else:
                worst[idx] = min(worst[idx], float(val.min()))
            for s in [0, len(omega) // 2, len(omega) - 1]:
                v, i = sol[s, :5], sol[s, 5:]
                w = omega[s]
                nodal = port + w * Y + B @ np.linalg.solve(Z, B.T) / w
                vr = np.linalg.solve(nodal, src[:5])
                voltage_err = max(voltage_err, float(np.max(np.abs(v - vr))))
                Psrc = .5 * np.real(np.conj((1 - v[0]) / 50))
                Pload = .5 * abs(v[2]) ** 2 * np.real(1 / (60 - 40j))
                Pind = .5 * np.sum(abs(i) ** 2 * w * L / 25)
                Pcap = .5 * np.sum(abs(E @ v) ** 2 * w * C * np.real(qfac))
                P50 = .5 * abs(1 - v[0]) ** 2 / 50
                power_err = max(power_err, float(abs(Psrc - Pload - Pind - Pcap - P50)))
    return dict(file=Path(filename).name, worst_IL_db=worst[0],
                min_H2_db=worst[1], min_H3_db=worst[2],
                minimum_K_eigenvalue=keig,
                max_voltage_difference_V=voltage_err,
                max_power_residual_W=power_err,
                checks="7001 samples per individual frequency interval; finite grid, not continuous proof")


if __name__ == "__main__":
    for name in ("C6_1PCB_H30p1.json", "C6_2PCB_H30p1.json", "C6_3PCB_H30p1.json"):
        print(json.dumps(verify(HERE / name), indent=2))
