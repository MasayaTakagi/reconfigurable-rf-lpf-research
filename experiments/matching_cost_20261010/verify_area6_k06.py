#!/usr/bin/env python3
"""Recheck new 2026-10-10 Phase-2 matching-only, area<=6 / PCB |k|<=0.6 candidates.

Run from repository root:
    python experiments/matching_cost_20261010/verify_area6_k06.py

NumPy only. This is *not* a topology search or a global lower-bound proof.
"""
import json
from pathlib import Path
import numpy as np
from verify_shortlist import passband_grid, Kmatrix, evaluate

HERE = Path(__file__).resolve().parent
DB = json.loads((HERE / "area6_k06_shortlist.json").read_text())
NAMES = DB["case_names"]
Q = DB["q"]
ZL = 60 - 40j
RS = 50.0

def independent_winding_mna(cand, f_mhz, icase):
    """Solve full (N+1 node voltage + N winding current) block MNA, no series shortcut."""
    L = np.array(cand["L_nH"], dtype=float)
    names = cand["types"]
    n = len(L)
    w = 2 * np.pi * f_mhz * 1e6
    K = Kmatrix(names, cand["k_pcb"])
    assert float(np.linalg.eigvalsh(K).min()) > 0
    M = np.sqrt(L[:, None] * L[None, :]) * K * 1e-9
    Z = 1j * w * M + np.diag(w * L * 1e-9 / [Q[t] for t in names])
    B = np.zeros((n, n + 1))
    for j in range(n):
        B[j, j] = 1.0
        B[j, j+1] = -1.0
    ci, co = cand["Cvar_pf_by_band"][icase]
    assert 0 <= ci <= 4 and 0 <= co <= 4
    ycap = lambda x: w * x * 1e-12 / (1 / Q["IC_C"] - 1j)
    Y = np.zeros((n+1, n+1), dtype=complex)
    Y[0, 0] = 1 / RS + ycap(ci)
    Y[-1, -1] += 1 / ZL + ycap(co)
    A = np.block([[Y, B.T], [B, -Z]])
    rhs = np.zeros(2*n+1, dtype=complex)
    rhs[0] = 1/RS
    state = np.linalg.solve(A, rhs)
    v, curr = state[:n+1], state[n+1:]
    Pload = 4*RS*(1/ZL).real*abs(v[-1])**2
    Pref = abs(1 - 2*v[0])**2
    Pcoils = 4*RS*w*1e-9*sum(L[k]/Q[t]*abs(curr[k])**2 for k,t in enumerate(names))
    Pcaps = 4*RS*(ycap(ci).real*abs(v[0])**2+ycap(co).real*abs(v[-1])**2)
    assert abs(Pload+Pref+Pcoils+Pcaps-1.0)<1e-10
    return -10*np.log10(Pload)

def main():
    freqs = passband_grid(step_mhz=0.02)
    for d in DB["candidates"]:
        nPCB = d["types"].count("PCB-L")
        nChip = sum(t != "PCB-L" for t in d["types"])
        area = d["types"].count("LQP02") + 2*d["types"].count("LQP01")/3
        assert nPCB<=3 and nChip<=6 and area<=6+1e-8
        assert d["k_pcb"]<=0.6 and abs(area-d["A_chip"])<1e-7
        best = (-1.0, "", 0.0)
        for j, name in enumerate(NAMES):
            for f in freqs[name]:
                il = evaluate(d, float(f), j)
                if il > best[0]: best = (il, name, float(f))
        assert abs(best[0]-d["IL_dB"])<2e-6, (d["name"], best, d["IL_dB"])
        for name, f in [(best[1],best[2]),("B71",617.0),("B8",960.0)]:
            icase=NAMES.index(name)
            x = independent_winding_mna(d, f, icase)
            y = evaluate(d, f, icase)
            assert abs(x-y)<1e-9, (d["name"], f, x, y)
        print(f'{d["name"]}: {best[0]:.9f} dB, worst {best[1]} {best[2]:.3f} MHz; full MNA/passivity OK')
    print("7/7 verified on 0.02MHz passband mesh (NOT a mathematical continuous-band certificate).")

if __name__=="__main__":
    main()
