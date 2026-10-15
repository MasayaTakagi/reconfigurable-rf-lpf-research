#!/usr/bin/env python3
"""EXP-043: isolate GJM Q improvement from greater permissible fixed C.

Two RF-T005 COMPLIANT "Q-only" GJM cases cap GJM <=0.2 pF (study limit).
Two explicitly INVALID Q40-at-GJM-large-C diagnostics let capacity alone rise.
All other components, Q assumptions, required S2P and k bounds unchanged.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import diagnose_pcb_gjm as base
from lpf.constraint_versions import load_constraint

STUDIES={
    "gjm_cp_Q80_tightC0p2":{
        "parent":"gjm_cp","source":"zero_gjm_double","gjm_max":.2,"q40_diagnostic":False},
    "gjm_cf0_cp_Q80_tightC0p2":{
        "parent":"gjm_cf0_cp","source":"zero_gjm_double","gjm_max":.2,"q40_diagnostic":False},
    "gjm_cp_Q40_highC_OFFSPEC":{
        "parent":"gjm_cp","source":"gjm_cp","gjm_max":3.,"q40_diagnostic":True},
    "gjm_cf0_cp_Q40_highC_OFFSPEC":{
        "parent":"gjm_cf0_cp","source":"gjm_cf0_cp","gjm_max":3.,"q40_diagnostic":True},
}
original_evaluator=base.evaluator
for name,c in STUDIES.items():
    original=base.VARIANTS[c["parent"]]
    base.VARIANTS[name]={
        **original,"gjm_max":c["gjm_max"],
        "q40_diagnostic":c["q40_diagnostic"]}

def modified_evaluator(policy,variant,points):
    e=original_evaluator(policy,variant,points)
    config=STUDIES[variant]
    for j in base.VARIANTS[variant]["gjm"]:
        e.bounds[3+j,1]=config["gjm_max"]
        if config["q40_diagnostic"]:
            e.Q_C[j]=40. # does not represent an approved GJM part
    return e
base.evaluator=modified_evaluator

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",choices=STUDIES,required=True)
    ap.add_argument("--starts",type=int,default=4)
    ap.add_argument("--maxiter",type=int,default=220)
    ap.add_argument("--coarse",type=int,default=9)
    ap.add_argument("--dense",type=int,default=1001)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    p=load_constraint("RF-T005",allow_trial=True)
    config=STUDIES[a.variant]
    ck=base.HERE/"checkpoints"/(config["source"]+".json")
    base.SEED=np.array(json.loads(ck.read_text())["vector"],float)
    assert len(base.SEED)==26
    # In Q80 tight case fixed C <= 0.2. Avoid capacity "giveback" from
    # GJM local starts, which are still clipped to valid [0.02,0.2].
    r=base.fit(p,a.variant,a.starts,a.maxiter,a.coarse,a.dense,20261019)
    valid=not config["q40_diagnostic"]
    r["eligibility"]="RF-T005_compliant" if valid else \
          "OFF_SPEC_GJM_Q40_unapproved_Q_assumption"
    r["comparison_experiment"]="EXP-043 fixed capacitor capacity vs Q, continuation"
    r["model_intervention"]={
        "category":"GJM01 but artificially set Q40" if not valid else "GJM01 Q80 capped at 0.2pF",
        "Q_GJM":40 if not valid else 80,
        "GJM_max_pF_for_this_study":config["gjm_max"],
        "formal_GJM_max_pF":100,
        "note":"Q40 GJM unapproved; simulated solely to isolate capacity from component quality"
             if not valid else
             "Compliant subset of GJM allowed C: Q80, study-specific upper .2pF"
    }
    out=a.out or base.ROOT/"results"/"EXP-043"/("capacity_vs_q_"+a.variant+".json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n")
    print("DONE",a.variant,r["eligibility"],"area",r["area_cost"],
          "IL",r["dense_validation"]["worst_IL_db"],"H2",r["dense_validation"]["min_H2_db"],
          "H3",r["dense_validation"]["min_H3_db"],
          "MNA",r["independent_7x7_MNA"]["passed"],flush=True)

if __name__=="__main__":main()
