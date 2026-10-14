#!/usr/bin/env python3
"""Independent Phase-2 RF-T004 14,001-point and current-MNA replay for C13.667.

Models constant Q only. No SRF, electromagnetic parasitics, tolerance or hardware proof.
"""
import csv
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def incidence(edges):
    b = np.zeros((len(edges), 5))
    for i, (a, c) in enumerate(edges):
        if a:
            b[i, a - 1] += 1
        if c:
            b[i, c - 1] -= 1
    return b

def verify(path=HERE / "EXP018-C13.667.json", points=14001):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    assert d["constraint_id"] == "RF-T004"
    L = np.array(d["L_nH"]) * 1e-9
    Q = np.array([33 if s == "LQW04" else 25 for s in d["L_series"]])
    n = len(L)
    assert len(d["Cv_edges"]) <= 3 and len(d["PCB_edges"]) <= 3
    assert all(.02 - 1e-8 <= x <= .2 + 1e-8 for x in d["PCB_pF"])
    assert all(0 <= x <= 1.5 + 1e-8 for vals in d["Cv_by_setting"].values() for x in vals)
    area = 3 * d["L_series"].count("LQW04") + d["L_series"].count("LQP02HV") + 2 * len(d["G_edges"]) / 3
    assert abs(area - d["area"]) < 1e-9

    K = np.eye(n)
    M = np.diag(L)
    assert sorted(d["row"]) == list(range(n))
    for idx, k in enumerate(d["k"]):
        assert abs(k) <= .15000001
        i, j = d["row"][idx:idx+2]
        K[i, j] = K[j, i] = k
        M[i, j] = M[j, i] = k * np.sqrt(L[i] * L[j])
    mineig = np.linalg.eigvalsh(K).min()
    assert mineig > 0

    B = incidence(d["L_edges"]).T
    D = incidence(d["G_edges"] + d["PCB_edges"] + d["Cv_edges"])
    qcap = np.array([80] * len(d["G_edges"]) + [40] * len(d["PCB_edges"]) + [50] * len(d["Cv_edges"]))
    source = np.array([.02, 0, 0, 0, 0], dtype=complex)
    ports = np.zeros((5, 5), dtype=complex)
    ports[0, 0] = 1 / 50
    ports[2, 2] = 1 / (60 - 40j)
    Z0 = np.diag(L / Q) + 1j * M
    Yin = B @ np.linalg.solve(Z0, B.T)
    bands = list(csv.DictReader((ROOT / "data/bands.csv").open(encoding="utf-8")))
    all_cases = ["B71", "B12", "B28", "B13+B14", "B26", "B8"]
    results = {}
    max_v_err = max_p_err = 0.
    nchecks = 0

    for case in all_cases:
        cap = np.array(d["G_pF"] + d["PCB_pF"] + d["Cv_by_setting"][case]) * 1e-12
        y0 = cap / (1 / qcap - 1j)
        Ycap = D.T @ np.diag(y0) @ D
        local = {"pass": [], "H2": [], "H3": []}
        for band in (b for b in bands if b["case"] == case):
            freqs = np.linspace(float(band["low_mhz"]), float(band["high_mhz"]), points)
            w = 2 * np.pi * 1e6 * freqs
            An = ports[None] + w[:, None, None] * Ycap[None] + Yin[None] / w[:, None, None]
            vv = np.linalg.solve(An, np.broadcast_to(source, (len(w), 5))[..., None])[..., 0]
            il = -10 * np.log10(np.maximum(200 * 60 / 5200 * np.abs(vv[:, 2])**2, 1e-300))
            metric = "pass" if band["region"] in ("UL", "DL") else band["region"]
            local[metric].append(float(il.max() if metric == "pass" else il.min()))
            for f in np.linspace(float(band["low_mhz"]), float(band["high_mhz"]), 3):
                omega = 2 * np.pi * 1e6 * f
                yc = omega * y0
                Ys = ports + D.T @ np.diag(yc) @ D
                Zl = omega * Z0
                full = np.block([[Ys, B], [B.T, -Zl]])
                solution = np.linalg.solve(full, np.r_[source, np.zeros(n)])
                V, I = solution[:5], solution[5:]
                Vref = np.linalg.solve(Ys + B @ np.linalg.solve(Zl, B.T), source)
                max_v_err = max(max_v_err, float(np.max(np.abs(V - Vref))))
                Pav = 1 / 200
                Pref = abs(V[0] - .5)**2 / 50
                Pload = abs(V[2])**2 * 60 / 5200
                Pl = float(np.sum(omega * L / Q * abs(I)**2))
                Pc = float(np.sum(yc.real * abs(D @ V)**2))
                max_p_err = max(max_p_err, float(abs(Pav - Pref - Pload - Pl - Pc)))
                nchecks += 1
        results[case] = [max(local["pass"]), min(local["H2"]), min(local["H3"])]

    metrics = [max(z[0] for z in results.values()),
               min(z[1] for z in results.values()),
               min(z[2] for z in results.values())]
    assert np.allclose(metrics, [d["IL"], d["H2"], d["H3"]], rtol=0, atol=1e-6)
    assert nchecks == 84 and max_v_err < 1e-10 and max_p_err < 1e-11
    assert metrics[0] <= .3 and min(metrics[1:]) >= 35
    print("PASS", d["candidate_id"], "IL/H2/H3", metrics, "K_eigmin", float(mineig),
          "independent_MNA_checks", nchecks, "dV", max_v_err, "power_residual_W", max_p_err)
    print("NOTE: constant-Q numerical Phase 2 result, physical EM/SRF/Q(f) unverified.")

if __name__ == "__main__":
    verify()
