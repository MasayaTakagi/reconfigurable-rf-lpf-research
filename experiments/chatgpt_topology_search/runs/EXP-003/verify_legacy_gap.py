#!/usr/bin/env python3
"""Independent MNA cross-check: legacy 4 tunable C versus cost-7 A7-01.

Historical CP07 and its row-coupling variant are intentionally noncompliant
with current two-grounded-tunable-C rules. This is a controlled sensitivity
study, NOT an approved new LPF or a proof of optimality.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/"src"))
from lpf.circuit import Branch,solve
from lpf.evaluate import CASES,evaluate_settings

DATA=json.loads((HERE/"legacy_cp07_comparison.json").read_text(encoding="utf-8"))


def legacy_case(d,band):
    # Original nodes: IN=0,n1=1,n2=2,OUT=3,shunt-tip=4,GND=-1
    # Common MNA nodes: IN=1,n1=2,n2=3,OUT=4,shunt-tip=5,GND=0
    k=np.eye(4)
    for (a,b),v in zip(d["k_order"],d["full_pairwise_signed_k"]):
        k[a,b]=k[b,a]=v
    L=tuple(Branch(a,b,v*1e-9,25) for (a,b),v in zip(
       [(1,2),(3,5),(3,4),(2,3)],d["fixed_chip_inductor_L_nH"]))
    C=tuple(Branch(a,b,v*1e-12,80) for (a,b),v in zip(
       [(1,2),(5,0),(3,4),(2,3)],d["case_map"][band]))
    return dict(f_hz=960e6,n_nodes=5,source_node=1,load_node=4,
                inductors=L,capacitors=C,coupling=k,
                source_voltage=1.0,source_ohms=50.0,load_ohms=60-40j)


def area7_case(d,band):
    net=d["topology"]
    L=tuple(Branch(v["a"],v["b"],v["L_nH"]*1e-9,v["Q"])
             for v in net["inductors"])
    C=tuple(Branch(v["a"],v["b"],v["C_pF"]*1e-12,v["Q"])
             for v in net["fixed_caps"])
    C+=tuple(Branch(v["a"],v["b"],c*1e-12,v["Q"])
             for v,c in zip(net["variable_caps"],d["variable_C_pf_by_setting"][band]))
    k=np.eye(4)
    ids=[v["id"] for v in net["inductors"]]
    order=[ids.index(x) for x in d["physical_chip_row"]]
    for i,v in enumerate(d["nominal_adjacent_k"]):
        a,b=order[i:i+2];k[a,b]=k[b,a]=v
    return dict(f_hz=960e6,n_nodes=5,source_node=1,load_node=3,
                inductors=L,capacitors=C,coupling=k,
                source_voltage=1.,source_ohms=50.,load_ohms=60-40j)


def compute():
    current=json.loads((HERE.parent/"EXP-002/A7-01.json").read_text(encoding="utf-8"))
    cases={"legacy_CP07":legacy_case(DATA["legacy_CP07"],"B8"),
           "legacy_row_reoptimized":legacy_case(DATA["legacy_with_2026_10_11_row_coupling"],"B8"),
           "area7_A7_01":area7_case(current,"B8")}
    expected={"legacy_CP07":0.3289240193235216,
              "legacy_row_reoptimized":0.3376603645361489,
              "area7_A7_01":0.5083889589116496}
    records={}
    for name,params in cases.items():
        out=solve(**params)
        if abs(out["il_db"]-expected[name])>1e-7:
            raise AssertionError(f"{name}: mismatched independent MNA: {out['il_db']}")
        if abs(out["power_residual"])>1e-12:
            raise AssertionError(f"{name}: power balance failed")
        records[name]={
            "il_db":float(out["il_db"]),
            "p_load_mw_at_1W_Pavs":float(out["p_load"]*200000),
            "p_reflected_mw_at_1W_Pavs":float(out["p_reflected"]*200000),
            "p_inductor_mw_at_1W_Pavs":float(out["p_inductor"]*200000),
            "p_capacitor_mw_at_1W_Pavs":float(out["p_capacitor"]*200000),
            "power_balance_residual_W_at_1V_RMS":float(out["power_residual"]),
        }
    return records


def main():
    d=compute()
    for name,item in d.items():
        print(name,item)
    target=HERE/"independent_point_power.json"
    target.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("PASS; standalone common-MNA operating-point check only:",target)


if __name__=="__main__":
    main()
