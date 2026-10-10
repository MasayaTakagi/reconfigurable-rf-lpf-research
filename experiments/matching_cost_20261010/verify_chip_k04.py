#!/usr/bin/env python3
"""Verify chip-chip k=0.4 matching-only shortlist; no stopband/Phase 3 work.

Run from repository root:
    python experiments/matching_cost_20261010/verify_chip_k04.py
Requires numpy. The 0.02 MHz frequency grid is not a mathematical continuum proof.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = json.loads((HERE / "chip_k04_shortlist.json").read_text(encoding="utf-8"))
NAMES = DATA["case_names"]
RS, ZLOAD = 50.0, 60.0 - 40.0j
Q_L, Q_C = 25.0, 80.0
KPAIR = 0.4

def grid():
    ranges = {name: [] for name in NAMES}
    with (ROOT / "data/bands.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"] != "pass":
                continue
            lo = float(row["low_mhz"])
            hi = float(row["high_mhz"])
            n = max(2, math.ceil((hi-lo)/0.02)+1)
            ranges[row["case"]].append(np.linspace(lo, hi, n))
    return {name: np.unique(np.concatenate(rr)) for name,rr in ranges.items()}

def cap_y(w, c_pf):
    return w*c_pf*1e-12/(1/Q_C-1j)

def scalar_equivalent_il(c, f_mhz, case_idx):
    n = c["n_chip_LQP02"]
    l_one = c["each_L_nH"]*1e-9
    leq = n*l_one*(1+(n-1)*KPAIR)
    series_r = 2*math.pi*f_mhz*1e6*n*l_one/Q_L
    w = 2*math.pi*f_mhz*1e6
    yseries = 1/(series_r+1j*w*leq)
    cin, cout = c["Cvar_pf_by_case"][case_idx]
    yin, yout = cap_y(w,cin), cap_y(w,cout)
    yload = 1/ZLOAD
    b = yseries+yout+yload
    v0 = (1/RS)/(1/RS+yin+yseries-yseries*yseries/b)
    v1 = yseries*v0/b
    return -10*np.log10(4*RS*yload.real*np.abs(v1)**2)

def mna_windings_il(c, f_mhz, case_idx):
    n = c["n_chip_LQP02"]
    l = c["each_L_nH"]*1e-9
    K = np.full((n,n),KPAIR)
    np.fill_diagonal(K,1)
    assert float(np.linalg.eigvalsh(K).min()) > 0
    w = 2*math.pi*f_mhz*1e6
    Z = 1j*w*l*K+np.eye(n)*(w*l/Q_L)
    B = np.zeros((n,n+1),dtype=complex)
    for i in range(n):
        B[i,i] = 1.0
        B[i,i+1] = -1.0
    cin,cout = c["Cvar_pf_by_case"][case_idx]
    Y = np.zeros((n+1,n+1),dtype=complex)
    yin, yout = cap_y(w,cin),cap_y(w,cout)
    Y[0,0] = 1/RS+yin
    Y[n,n] = 1/ZLOAD+yout
    system = np.block([[Y,B.T],[B,-Z]])
    b = np.zeros(2*n+1,dtype=complex)
    b[0] = 1/RS
    sol = np.linalg.solve(system,b)
    volt,curr = sol[:n+1],sol[n+1:]
    p_load = 4*RS*(1/ZLOAD).real*abs(volt[n])**2
    p_ref = abs(1-2*volt[0])**2
    p_L = 4*RS*(w*l/Q_L)*float(np.sum(abs(curr)**2))
    p_C = 4*RS*(yin.real*abs(volt[0])**2+yout.real*abs(volt[n])**2)
    assert abs(p_load+p_ref+p_L+p_C-1) < 1e-10
    return -10*math.log10(p_load)

def main():
    groups = grid()
    for c in DATA["candidates"]:
        n = c["n_chip_LQP02"]
        assert 1 <= n <= 6 and c["area_cost"] == n
        assert c["all_chip_pair_k"] <= 0.4
        assert c["each_L_nH"] >= 0.4 and c["each_L_nH"] <= 27
        assert len(c["Cvar_pf_by_case"]) == len(NAMES)
        assert all(0 <= x <= 4 for pair in c["Cvar_pf_by_case"] for x in pair)
        worst = (-1.0, "", -1.0)
        for i,name in enumerate(NAMES):
            f = groups[name]
            y = scalar_equivalent_il(c,f,i)
            j = int(y.argmax())
            if float(y[j]) > worst[0]: worst = (float(y[j]),name,float(f[j]))
            for ff in (float(f[0]),float(f[-1]),float(f[len(f)//2])):
                mna = mna_windings_il(c,ff,i)
                eq = float(scalar_equivalent_il(c,ff,i))
                assert abs(mna-eq)<1e-10
        assert abs(worst[0]-c["max_IL_dB"])<2e-6, (n,worst,c["max_IL_dB"])
        print(f'LQP02*{n}: ILmax={worst[0]:.9f}dB, {worst[1]} {worst[2]:.2f}MHz, passivity/energy/MNA OK')
    print("5/5 candidates pass. Physical mutual realizability NOT verified.")

if __name__ == "__main__":
    main()
