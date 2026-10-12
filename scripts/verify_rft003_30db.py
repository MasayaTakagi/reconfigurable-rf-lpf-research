#!/usr/bin/env python3
"""Re-evaluate a RF-T003 30-dB trial candidate against all six segmented bands.

This does not re-run the nonconvex optimizer. RF-F001 remains unchanged.
Run from repository root:
    PYTHONPATH=src python scripts/verify_rft003_30db.py --samples 51
    PYTHONPATH=src python scripts/verify_rft003_30db.py --samples 7001
"""
import argparse
import json
from pathlib import Path
import numpy as np
from lpf.constraint_versions import (
    load_constraint, constraint_fingerprint, validate_variable_c_connections,
)
from lpf.circuit import Branch, solve
from lpf.independent import solve_gain
from lpf.evaluate import CASES, evaluate_settings, load_bands

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/validation/rft003_20261012/target30_results.json"

def build(candidate, case):
    coils = tuple(Branch(z["nodes"][0],z["nodes"][1],
         float(z["L_nH"])*1e-9,float(z["Q"])) for z in candidate["inductors"])
    caps = tuple(Branch(z["edge"][0],z["edge"][1],
         float(z["C_pf"])*1e-12,float(z["Q"])) for z in candidate["fixed_capacitors"])
    caps += tuple(Branch(z["edge"][0],z["edge"][1],
         float(v)*1e-12,float(z["Q"])) for z,v in zip(
         candidate["variable_capacitors"],candidate["variable_C_pf_by_setting"][case]))
    physical_order=candidate["chip_index_order"]
    K=np.eye(4)
    for i,k in enumerate(candidate["chip_adjacent_k"]):
        a,b=physical_order[i:i+2]
        K[a,b]=K[b,a]=float(k)
    assert np.linalg.eigvalsh(K).min()>0
    assert all(abs(v)<=0.4+1e-9 for v in candidate["chip_adjacent_k"])
    return dict(f_hz=700e6,n_nodes=5,source_node=1,load_node=3,
        inductors=coils,capacitors=caps,coupling=K,
        source_voltage=1.0,source_ohms=50.0,load_ohms=60-40j)

def verify(samples=51):
    saved=json.loads(DATA.read_text(encoding="utf-8"))
    c=saved["best"]
    policy=load_constraint("RF-T003",allow_trial=True)
    assert c["effective_constraint_sha256"]==constraint_fingerprint(policy)
    assert policy["evaluation"]["full_phase2"]["nominal_h2_h3_target_db"]==30
    conns=[]
    for cap in c["variable_capacitors"]:
        a,b=cap["edge"]
        conns.append({"a":a,"b":b,**({"role":"bridge"} if cap["role"]=="bridge" else {})})
    validate_variable_c_connections(conns,policy)
    # Prove this specific bridge is not a main-path series-only capacitor:
    # the fixed L3 edge connects the same two endpoints at variable C=0.
    assert any(z["nodes"]==[2,3] for z in c["inductors"])
    assert c["variable_capacitors"][1]["edge"]==[2,3]
    assert all(x["series"]=="LQP02HV" and 0.4<=x["L_nH"]<=27 and x["Q"]==25
               for x in c["inductors"])
    assert all(0<=v<=4 for case in CASES for v in c["variable_C_pf_by_setting"][case])
    def make(case):
        p=build(c,case)
        p.pop("f_hz")
        return p
    evaluated=evaluate_settings(make,samples_per_segment=samples)
    mna_delta,balance,checks=0.,0.,0
    for case in CASES:
        p=make(case)
        for band in load_bands():
            if band["case"]!=case:continue
            f_lo,f_hi=float(band["low_mhz"]),float(band["high_mhz"])
            for f in (f_lo,(f_lo+f_hi)/2,f_hi):
                x=solve(f*1e6,**p)
                y=solve_gain(f*1e6,**p)
                mna_delta=max(mna_delta,abs(x["il_db"]+10*np.log10(y)))
                balance=max(balance,abs(x["power_residual"]))
                checks+=1
    il=evaluated["worst_il_db"][0]
    h2=evaluated["min_h2_db"][0]
    h3=evaluated["min_h3_db"][0]
    assert mna_delta<1e-8 and balance<1e-12
    assert h2>=30-1e-5 and h3>=30-1e-5
    if samples==7001:
        expected=c["validation"]
        for actual,ref in ((il,expected["worst_IL_db"]),(h2,expected["min_H2_db"]),
                           (h3,expected["min_H3_db"])):
            assert abs(actual-ref)<1e-7,(actual,ref)
    return dict(id=c["id"],constraint_id="RF-T003",samples_per_interval=samples,
        worst_IL_db=il,min_H2_db=h2,min_H3_db=h3,
        independent_MNA_points=checks,max_MNA_difference_db=mna_delta,
        max_power_balance_residual_W=balance,
        numerical_only=True,meets_IL_0p30=il<=0.3)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--samples",type=int,default=51)
    args=p.parse_args()
    if args.samples<2:p.error("samples must be >=2")
    print(json.dumps(verify(args.samples),indent=2,ensure_ascii=False))
