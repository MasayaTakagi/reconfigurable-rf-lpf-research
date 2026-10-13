#!/usr/bin/env python3
"""Recheck RF-T003 6L lower-chip-area near-miss, not a passed IL<=0.30 design.

Data are selected from an exploratory finite local cost-reduction screen.
The physical current-augmented MNA and independently assembled nodal solver
come from the repository library.  This does not rerun cost optimization.
PYTHONPATH=src python scripts/verify_rft003_cost_reduction.py --samples 7001
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from lpf.circuit import Branch,solve
from lpf.independent import solve_gain
from lpf.evaluate import CASES,evaluate_settings,load_bands

DATA=ROOT/"data/validation/rft003_20261013/cost_reduction_screening.json"

def run(samples=9):
    record=json.loads(DATA.read_text(encoding="utf-8"))
    c=record["six_L_nearmiss"]
    assert record["phase"]=="Phase 2" and record["trial"]=="RF-T003"
    assert len(c["L_edges"])==6 and len(c["L_nH"])==6
    assert all(.4<=v<=27+1e-10 for v in c["L_nH"])
    assert all(.02<=q["pF"]<=.2 for q in c["fixed_PCB_pattern_Q40"])
    assert len(c["fixed_PCB_pattern_Q40"])==3
    assert len(c["fixed_GJM01_Q80"])==2
    assert all(0<=v<=4 for cv in c["variable_C_pf_by_setting"].values() for v in cv)
    assert c["variable_capacitors"]==[
        {"edge":[5,0],"role":"ground_shunt"},
        {"edge":[2,3],"role":"bridge_parallel_fixed_L3"}]
    assert [2,3] in c["L_edges"]
    K=np.eye(6)
    row=c["physical_row"]
    assert sorted(row)==list(range(6))
    for (a,b),k in zip(zip(row,row[1:]),c["adjacent_signed_k"]):
        assert abs(k)<=.4+1e-9
        K[a,b]=K[b,a]=k
    assert np.linalg.eigvalsh(K).min()>0
    inductors=tuple(Branch(int(a),int(b),L*1e-9,25.0)
        for (a,b),L in zip(c["L_edges"],c["L_nH"]))
    fixed=tuple(Branch(*z["edge"],z["pF"]*1e-12,q)
        for zs,q in ((c["fixed_GJM01_Q80"],80.),(c["fixed_PCB_pattern_Q40"],40.))
        for z in zs)
    def parameters(case):
        cv=tuple(Branch(*z["edge"],v*1e-12,80.)
            for z,v in zip(c["variable_capacitors"],
                c["variable_C_pf_by_setting"][case]))
        return dict(n_nodes=5,source_node=1,load_node=3,
            source_voltage=1.,source_ohms=50.,load_ohms=60-40j,
            inductors=inductors,capacitors=fixed+cv,coupling=K)
    data=evaluate_settings(parameters,samples_per_segment=samples)
    il=data["worst_il_db"][0]
    h2=data["min_h2_db"][0]
    h3=data["min_h3_db"][0]
    maxdelta=maxbalance=0.
    npoints=0
    for case in CASES:
        par=parameters(case)
        for rowband in load_bands():
            if rowband["case"]!=case:continue
            lo=float(rowband["low_mhz"])
            hi=float(rowband["high_mhz"])
            for frequency in (lo,(lo+hi)/2,hi):
                x=solve(frequency*1e6,**par)
                g=solve_gain(frequency*1e6,**par)
                maxdelta=max(maxdelta,abs(x["il_db"]+10*np.log10(g)))
                maxbalance=max(maxbalance,abs(x["power_residual"]))
                npoints+=1
    assert npoints==84 and maxdelta<1e-8 and maxbalance<1e-12
    assert h2>=30-1e-6 and h3>=30-1e-6
    if samples==7001:
        saved=c["validated_7001"]
        assert abs(il-saved["worst_IL_db"])<1e-7
        assert abs(min(h2,h3)-saved["min_H2_H3_db"])<1e-7
        assert il>.30, "This near-miss must not be relabeled passed"
    return dict(trial="RF-T003",chip_area=c["chip_area_units"],
        IL_db=il,min_H2_db=h2,min_H3_db=h3,
        IL_target_pass=il<=.30,independent_MNA_spots=npoints,
        max_independent_diff_db=maxdelta,power_balance_W=maxbalance)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--samples",type=int,default=9)
    args=parser.parse_args()
    print(json.dumps(run(args.samples),indent=2,ensure_ascii=False))
