#!/usr/bin/env python3
"""Replay a saved RF-T003 five-HV-inductor 30dB Phase-2 candidate.

Dense 5x5 nodal analysis is separately checked by full 10x10 branch-current
MNA at each separate band interval's endpoints and midpoint, including
power accounting. This is finite-grid numeric validation, NOT an EM check,
an exact extremum certificate, or a rerun of nonlinear optimization.

Example: python scripts/verify_rft003_5l.py --samples 7001
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from src.lpf.constraint_versions import (load_constraint, constraint_fingerprint,
                                          validate_variable_c_connections)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/validation/rft003_20261013/phase2_5l_results.json"
BANDS = ROOT / "data/bands.csv"
Z_LOAD = 60 - 40j
P_AVS = .005

def incidence(edges):
    B = np.zeros((5, len(edges)))
    for j, (a, b) in enumerate(edges):
        if a: B[a - 1, j] += 1
        if b: B[b - 1, j] -= 1
    return B

def verify(samples=51):
    assert samples >= 2
    record = json.loads(DATA.read_text(encoding="utf-8"))
    c = record["configuration"]
    p = load_constraint("RF-T003", allow_trial=True)
    assert record["constraint_class"] == "trial"
    assert constraint_fingerprint(p) == record["effective_constraint_sha256"]
    assert p["evaluation"]["full_phase2"]["nominal_h2_h3_target_db"] == 30
    assert c["variable_C_edges"] == [[5, 0], [2, 3]]
    assert [2, 3] in c["L_edges"]   # bridge shunts existing L3; not series
    validate_variable_c_connections(
        [{"a":5,"b":0},{"a":2,"b":3,"role":"bridge"}], p)
    assert len(c["L_nH"]) == 5
    assert all(s == "LQP02HV" for s in c["L_series"])
    assert all(q == 25 for q in c["L_Q"])
    assert all(.4 <= x <= 27 for x in c["L_nH"])
    assert len(c["fixed_capacitors"]) == 2
    assert all(z["kind"]=="GJM01" and z["Q"]==80 for z in c["fixed_capacitors"])
    assert all(0 <= x <= 4 for v in c["variable_C_by_case_pf"].values() for x in v)
    L = np.array(c["L_nH"]) * 1e-9
    Q = np.array(c["L_Q"])
    K = np.eye(5)
    order = c["physical_chip_row"]
    for j, k in enumerate(c["adjacent_k"]):
        assert abs(k) <= .4 + 1e-10
        a, b = order[j:j+2]
        K[a,b] = K[b,a] = k
    assert np.linalg.eigvalsh(K).min() > 0
    M = K * np.sqrt(np.outer(L, L))
    B = incidence(c["L_edges"])
    D = incidence([z["edge"] for z in c["fixed_capacitors"]]
                  + c["variable_C_edges"]).T
    CQ = np.array([z["Q"] for z in c["fixed_capacitors"]] + [80.,80.])
    coil = B @ np.linalg.inv(np.diag(L/Q) + 1j*M) @ B.T
    port = np.diag(np.array([1/50, 0, 1/Z_LOAD, 0, 0], complex))
    src = np.array([1/50,0,0,0,0], complex)
    bands = list(csv.DictReader(BANDS.open(newline="", encoding="utf-8")))
    assert len(bands) == 28
    worst = -float("inf")
    h2, h3 = float("inf"), float("inf")
    per_case = {}
    max_diff = max_balance = 0.
    spot_count = 0
    for case in ("B71","B12","B28","B13+B14","B26","B8"):
        C = np.r_[[z["C_pf"] for z in c["fixed_capacitors"]],
                  c["variable_C_by_case_pf"][case]] * 1e-12
        chi = C / (1/CQ - 1j)
        Cmat = np.einsum("i,ij,ik->jk", chi, D, D)
        scores = {"IL":-float("inf"),"H2":float("inf"),"H3":float("inf")}
        for band in bands:
            if band["case"] != case: continue
            lo, hi = float(band["low_mhz"]), float(band["high_mhz"])
            region = band["region"]
            w = 2*np.pi*1e6*np.linspace(lo, hi, samples)
            Y = (port[None,:,:] + coil[None,:,:]/w[:,None,None]
                 + w[:,None,None]*Cmat[None,:,:])
            v = np.linalg.solve(
                Y, np.broadcast_to(src, (len(w),5))[...,None])[...,0]
            gain = abs(v[:,2])**2 * (1/Z_LOAD).real / P_AVS
            db = -10*np.log10(np.maximum(gain, 1e-300))
            if region in ("UL","DL"):scores["IL"] = max(scores["IL"], float(db.max()))
            else:scores[region] = min(scores[region], float(db.min()))
            for f_mhz in (lo,(lo+hi)/2,hi):
                omega = 2*np.pi*1e6*f_mhz
                Z = np.diag(omega*L/Q) + 1j*omega*M
                Ycap = omega*Cmat
                V = np.linalg.solve(
                    np.block([[port+Ycap, B],[-B.T,Z]]),
                    np.r_[src,np.zeros(5,complex)])
                voltage, iL = V[:5], V[5:]
                Pload = abs(voltage[2])**2*(1/Z_LOAD).real
                Pref = P_AVS*abs(2*voltage[0]-1)**2
                PL = abs(iL)**2*omega*L/Q
                PC = np.array([
                  abs(D[j]@voltage)**2*omega*C[j]/(CQ[j]*(1+1/CQ[j]**2))
                  for j in range(len(C))])
                max_balance = max(max_balance,
                                  abs(P_AVS-Pload-Pref-sum(PL)-sum(PC)))
                nodal = np.linalg.solve(port+coil/omega+Ycap,src)
                g2 = abs(nodal[2])**2*(1/Z_LOAD).real/P_AVS
                max_diff = max(max_diff,
                               abs(-10*np.log10(Pload/P_AVS)+10*np.log10(g2)))
                spot_count += 1
        per_case[case] = [scores["IL"],scores["H2"],scores["H3"]]
        worst = max(worst,scores["IL"])
        h2, h3 = min(h2,scores["H2"]),min(h3,scores["H3"])
    assert spot_count == 84 and max_diff < 1e-8 and max_balance < 1e-12
    assert h2 >= 30-1e-6 and h3 >= 30-1e-6
    if samples == 7001:
        verified = record["validation"]
        for actual, reference in (
             (worst,verified["worst_IL_db"]),(h2,verified["min_H2_db"]),
             (h3,verified["min_H3_db"])):
             assert abs(actual-reference) < 1e-7, (actual,reference)
    return {
       "id":record["id"],"constraint_id":"RF-T003",
       "samples_per_separate_interval":samples,
       "worst_IL_db":worst,"min_H2_db":h2,"min_H3_db":h3,
       "per_setting":per_case,"independent_MNA_spots":spot_count,
       "max_independent_error_db":max_diff,"max_power_balance_residual_W":max_balance,
       "min_K_eigenvalue":float(np.linalg.eigvalsh(K).min()),
       "chip_area":c["chip_area_cost"],"passes_IL_0p30_goal":worst<=.3
    }

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--samples",type=int,default=51)
    opts = argp.parse_args()
    print(json.dumps(verify(opts.samples),indent=2,ensure_ascii=False))
