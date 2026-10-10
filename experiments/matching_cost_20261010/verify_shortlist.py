#!/usr/bin/env python3
"""Recheck eight Phase-2 matching-only solutions (not a global optimizer).

Run from any directory:
    python experiments/matching_cost_20261010/verify_shortlist.py

Requires Python 3 and numpy; no switched-capacitor implementation.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CANDIDATES = json.loads((HERE / "shortlist.json").read_text(encoding="utf-8"))
CASES = CANDIDATES["case_names"]
Q = CANDIDATES["q"]
RS = CANDIDATES["source_ohm"]
LOAD = complex(**dict(zip(("real","imag"),[CANDIDATES["load_ohm"]["real"],CANDIDATES["load_ohm"]["imag"]])))
YLOAD = 1 / LOAD


def passband_grid(step_mhz=0.02):
    out = {case: [] for case in CASES}
    with (ROOT / "data/bands.csv").open(encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            if row["type"] != "pass":
                continue
            lo, hi = float(row["low_mhz"]), float(row["high_mhz"])
            n = max(2, math.ceil((hi - lo) / step_mhz) + 1)
            out[row["case"]].extend(np.linspace(lo, hi, n))
    return out


def Kmatrix(types, k_pcb):
    n = len(types)
    k = np.eye(n)
    chips = [i for i, typ in enumerate(types) if typ != "PCB-L"]
    pcb = [i for i, typ in enumerate(types) if typ == "PCB-L"]
    majors = set(zip(chips, chips[1:3]))
    for ix, i in enumerate(chips):
        for j in chips[ix+1:]:
            k[i,j] = k[j,i] = 0.25 if (i,j) in majors else 0.16
    for ix,i in enumerate(pcb):
        for j in pcb[ix+1:]:
            k[i,j] = k[j,i] = k_pcb
    return k


def evaluate(cand, freq_mhz, case_index):
    names = cand["types"]
    L = np.asarray(cand["L_nH"], dtype=float)
    K = Kmatrix(names, cand["k_pcb"])
    eig = np.linalg.eigvalsh(K)
    assert min(eig) > 0
    effective_L = float(np.sqrt(L) @ K @ np.sqrt(L))
    resistive_L = sum(float(l)/Q[name] for l, name in zip(L,names))
    omega = 2 * math.pi * freq_mhz * 1e6
    zs = omega*1e-9*(resistive_L + 1j*effective_L)
    yseries = 1/zs
    cin, cout = cand["Cvar_pf_by_band"][case_index]
    assert 0 <= cin <= 4 and 0 <= cout <= 4
    yin = omega*cin*1e-12/(1/Q["IC_C"]-1j)
    yout = omega*cout*1e-12/(1/Q["IC_C"]-1j)
    b = YLOAD + yout + yseries
    v0 = (1/RS)/(1/RS + yin + yseries - yseries*yseries/b)
    v1 = yseries*v0/b
    branch_I = (v0-v1)/zs
    p_load_over_p_avs = 4*RS*YLOAD.real*abs(v1)**2
    p_reflect_over_p_avs = abs(1-2*v0)**2
    p_coil_over_p_avs = 4*RS*omega*1e-9*resistive_L*abs(branch_I)**2
    p_cap_over_p_avs = 4*RS*(yin.real*abs(v0)**2+yout.real*abs(v1)**2)
    balance = (p_load_over_p_avs+p_reflect_over_p_avs+
               p_coil_over_p_avs+p_cap_over_p_avs)
    assert abs(balance - 1) < 1e-10
    return -10*math.log10(p_load_over_p_avs)


def main():
    freqs = passband_grid()
    for cand in CANDIDATES["candidates"]:
        max_il, worst = -1, None
        for icase,name in enumerate(CASES):
            for f in freqs[name]:
                il = evaluate(cand,float(f),icase)
                if il > max_il:
                    max_il, worst = il, (name,float(f))
        error = max_il - cand["IL_dB"]
        assert abs(error) < 3e-6, (cand["id"], max_il, error)
        print(f'{cand["id"]}: IL={max_il:.9f} dB; worst={worst}; delta={error:+.2e}')
    print("8/8 shortlist solutions reproduced; continuous-band global optimality NOT proved.")


if __name__ == "__main__":
    main()
