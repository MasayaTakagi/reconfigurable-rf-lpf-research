#!/usr/bin/env python3
"""RF-T003 continued 5L result: dense separate-interval nodal + independent MNA.

Replays a saved Phase 2 *trial* candidate only; it does not rerun the
nonconvex optimizer, check physical RF layout, or certify continuous intervals.

From repository root:
  python scripts/verify_rft003_coupling_row.py --samples 51
  python scripts/verify_rft003_coupling_row.py --samples 7001
"""
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.lpf.circuit import Branch, solve
from src.lpf.constraint_versions import (
    load_constraint, constraint_fingerprint, validate_variable_c_connections,
)

FILE = ROOT / "data/validation/rft003_20261013/continued_5l_coupling_row.json"
BANDS = ROOT / "data/bands.csv"
CASES = ("B71", "B12", "B28", "B13+B14", "B26", "B8")
PAVS = 0.005
ZLOAD = 60-40j

def incidence(edges, n=5):
    B = np.zeros((n, len(edges)), float)
    for i, (a,b) in enumerate(edges):
        if a: B[a-1,i] += 1
        if b: B[b-1,i] -= 1
    return B

def verify(samples=51):
    if samples < 3: raise ValueError("samples>=3")
    z = json.loads(FILE.read_text(encoding="utf-8"))
    p = load_constraint("RF-T003", allow_trial=True)
    assert z["constraint_id"] == "RF-T003"
    assert constraint_fingerprint(p) == z["constraint_sha256"]
    assert p["evaluation"]["full_phase2"]["nominal_h2_h3_target_db"] == 30
    v_edges = z["variable_C_edges"]
    validate_variable_c_connections([
        {"a":5,"b":0}, {"a":2,"b":3,"role":"bridge"}],p)
    assert v_edges == [[5,0],[2,3]] and [2,3] in z["L_edges"]
    assert all(t == "LQP02HV" for t in z["L_series"])
    assert all(float(q) == 25 for q in z["L_Q"])
    assert all(.4 <= t <= 27 for t in z["L_nH"])
    assert len(z["L_edges"]) == 5 and len(z["fixed_C"]) == 2
    assert all(c["kind"]=="GJM01" and c["Q"]==80 for c in z["fixed_C"])
    assert all(0<=u<=4 for vs in z["variable_C_setting_pf"].values() for u in vs)
    L = np.asarray(z["L_nH"]) * 1e-9
    Q = np.asarray(z["L_Q"])
    K = np.eye(len(L))
    row = z["physical_row_inductor_indices"]
    for i,k in enumerate(z["adjacent_signed_k"]):
        a,b = row[i:i+2]
        assert abs(k) <= .4 + 1e-10
        K[a,b] = K[b,a] = k
    assert sorted(row) == list(range(len(L)))
    assert np.linalg.eigvalsh(K).min() > 0
    M = np.sqrt(np.outer(L,L))*K
    edges = z["L_edges"]
    B = incidence(edges)
    Y_L0 = B @ np.linalg.solve(np.diag(L/Q)+1j*M,B.T)
    all_C_edges = [c["edge"] for c in z["fixed_C"]] + v_edges
    D = incidence(all_C_edges)
    qC = np.asarray([c["Q"] for c in z["fixed_C"]]+[z["variable_C_Q"]]*2)
    port = np.diag([1/50,0,1/ZLOAD,0,0]).astype(complex)
    source = np.array([1/50,0,0,0,0], complex)
    with BANDS.open(encoding="utf-8", newline="") as band_file:
        rows = list(csv.DictReader(band_file))
    assert len(rows) == 28
    results={}
    checked=0
    delta=0.
    residual=0.
    for case in CASES:
        c = np.r_[[t["pF"] for t in z["fixed_C"]],
                  z["variable_C_setting_pf"][case]]*1e-12
        Ym = D @ np.diag(c/(1/qC-1j)) @ D.T
        metrics = {"IL":-float("inf"),"H2":float("inf"),"H3":float("inf")}
        physical = dict(
            n_nodes=5, source_node=1, load_node=3,
            source_voltage=1., source_ohms=50., load_ohms=ZLOAD,
            coupling=K,
            inductors=tuple(Branch(int(a),int(b),float(t),float(q))
                            for (a,b),t,q in zip(edges,L,Q)),
            capacitors=tuple(Branch(int(a),int(b),float(t),float(q))
                             for (a,b),t,q in zip(all_C_edges,c,qC)))
        for band in rows:
            if band["case"] != case: continue
            lo,hi=map(float,(band["low_mhz"],band["high_mhz"]))
            freqs=np.linspace(lo,hi,samples)
            w=freqs * (2*np.pi*1e6)
            Y=port[None,:,:]+Y_L0[None,:,:]/w[:,None,None]+w[:,None,None]*Ym[None,:,:]
            vec=np.linalg.solve(
                Y, np.broadcast_to(source,(samples,5))[...,None])[:,:,0]
            load_power=abs(vec[:,2])**2*(1/ZLOAD).real
            il=-10*np.log10(load_power/PAVS)
            region=band["region"]
            if region in ("UL","DL"):metrics["IL"]=max(metrics["IL"],float(il.max()))
            else:metrics[region]=min(metrics[region],float(il.min()))
            for freq in (lo,(lo+hi)*0.5,hi):
                r=solve(freq*1e6,**physical)
                yy=port+Y_L0/(freq*1e6*2*np.pi)+(freq*1e6*2*np.pi)*Ym
                vv=np.linalg.solve(yy,source)
                direct_il=-10*np.log10(abs(vv[2])**2*(1/ZLOAD).real/PAVS)
                delta=max(delta,abs(r["il_db"]-direct_il))
                residual=max(residual,abs(r["power_residual"]))
                checked+=1
        results[case]=metrics
    worst=max(t["IL"] for t in results.values())
    h2=min(t["H2"] for t in results.values())
    h3=min(t["H3"] for t in results.values())
    assert checked==84 and delta<1e-8 and residual<1e-12
    assert h2>=30-1e-7 and h3>=30-1e-7
    if samples==7001:
        d=z["dense"]
        assert abs(worst-d["worst_IL_db"])<1e-7
        assert abs(h2-d["min_H2_db"])<1e-7
        assert abs(h3-d["min_H3_db"])<1e-7
    return dict(
        candidate=z["candidate_id"],trial="RF-T003",
        samples_per_individual_segment=samples,worst_IL_db=worst,
        min_H2_db=h2,min_H3_db=h3,
        MNA_checked_points=checked,max_MNA_disagreement_db=delta,
        max_power_balance_residual_W=residual,
        min_K_eigenvalue=float(np.linalg.eigvalsh(K).min()),
        meets_IL_goal_0p30=worst<=.30,
        per_setting=results)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--samples",type=int,default=51)
    args=parser.parse_args()
    print(json.dumps(verify(args.samples),indent=2,ensure_ascii=False))
