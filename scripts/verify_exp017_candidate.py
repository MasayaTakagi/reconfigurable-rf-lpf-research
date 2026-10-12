#!/usr/bin/env python3
"""EXP-017: replay an explicitly NON-FORMAL two-variable-C study checkpoint.

The one-grounded plus one-bridge layout is NOT RF-F001 (two grounded) and is
NOT RF-T002 (three tunables). This checks numerical lumped-model behavior.
PYTHONPATH=src python scripts/verify_exp017_candidate.py --samples 7001
"""
import argparse
import json
from pathlib import Path
import numpy as np
from lpf.circuit import Branch, solve
from lpf.independent import solve_gain
from lpf.evaluate import evaluate_settings, CASES, load_bands

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data/validation/exp017_20261012/checkpoints.json"

def build(c, case):
    coils = tuple(Branch(a,b,float(v)*1e-9,float(q))
                  for (a,b),v,q in zip(c["L_edges"],c["L_nH"],c["L_Q"]))
    caps = tuple(Branch(*z["edge"],float(z["C_pf"])*1e-12,float(z["Q"]))
                 for z in c["fixed_C"])
    caps += tuple(Branch(*edge,float(v)*1e-12,80.)
                  for edge,v in zip(c["variable_edges"],c["variable_C_by_case_pf"][case]))
    K=np.eye(len(coils))
    row=c["physical_chip_order"]
    for i,val in enumerate(c["adjacent_k"]):
        a,b=row[i:i+2];K[a,b]=K[b,a]=val
        assert abs(val)<=.4+1e-9
    assert np.linalg.eigvalsh(K).min()>0
    assert all(.4<=float(v)<=27 for v in c["L_nH"])
    assert all(z["kind"]=="GJM01" or
        (z["kind"]=="PCB_PATTERN_C" and .02-1e-12<=z["C_pf"]<=.2+1e-12)
        for z in c["fixed_C"])
    assert sum(z["kind"]=="PCB_PATTERN_C" for z in c["fixed_C"])<=3
    assert all(0<=v<=4 for v in c["variable_C_by_case_pf"][case])
    assert c["variable_edges"]==[[5,0],[2,3]]
    return dict(n_nodes=5,source_node=1,load_node=3,
        inductors=coils,capacitors=caps,coupling=K,
        source_voltage=1.,source_ohms=50.,load_ohms=60-40j)

def verify(samples=51):
    blob=json.loads(PATH.read_text(encoding="utf-8"))
    c=blob["candidate"]
    assert c["constraint_status"]=="NONCANONICAL_UNAPPROVED"
    assert c["phase"]=="Phase 2"
    scored=evaluate_settings(lambda name: build(c,name),samples_per_segment=samples)
    il=scored["worst_il_db"][0]
    h2=scored["min_h2_db"][0]
    h3=scored["min_h3_db"][0]
    mna_delta=0.;balance=0.;points=0
    for name in CASES:
        params=build(c,name)
        for band in load_bands():
            if band["case"]!=name:continue
            lo,hi=float(band["low_mhz"]),float(band["high_mhz"])
            for f in (lo,(lo+hi)/2,hi):
                a=solve(f*1e6,**params)
                independent=solve_gain(f*1e6,**params)
                mna_delta=max(mna_delta,abs(a["il_db"]+10*np.log10(independent)))
                balance=max(balance,abs(a["power_residual"]))
                points+=1
    assert mna_delta<1e-8 and balance<1e-12
    assert h2>=35-1e-5 and h3>=35-1e-5
    if samples==7001:
        ref=c["dense_7001_per_segment"]
        assert abs(il-ref["worst_IL_db"])<1e-7
        assert abs(h2-ref["min_H2_db"])<1e-7
        assert abs(h3-ref["min_H3_db"])<1e-7
    return dict(candidate_id=c["id"],grid_per_interval=samples,
        worst_IL_db=il,min_H2_db=h2,min_H3_db=h3,
        independent_check_points=points,
        independent_max_IL_difference_db=mna_delta,
        max_power_residual_W=balance)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--samples",type=int,default=51)
    a=p.parse_args()
    print(json.dumps(verify(a.samples),indent=2,ensure_ascii=False))
