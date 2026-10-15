#!/usr/bin/env python3
"""EXP-043 RF-T005 Phase 2 causal diagnosis of k vs three-pF C limits.

Tests the saved, independently validated 3L/single-shunt checkpoint:
(a) change k with all other parts fixed;
(b) re-tune with k clamped at +/-0.10 and IC cap <=3 (COMPLIANT);
(c) repeat with IC cap <=4 solely as an OUT-OF-SPEC diagnostic.
No new EXP reservation: this is a sensitivity extension to existing EXP-043.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

import search_3l as source
from lpf.constraint_versions import load_constraint

FILE=source.HERE/"checkpoints"/"zero_gjm_double.json"
START=np.array(json.loads(FILE.read_text(encoding="utf-8"))["vector"],float)
CFG="zero_gjm_double"
TARGET=30.01

def row(ev,x,label):
    y=ev.summary(x)
    return {"id":label,"k_L0Ls":float(x[6]),"k_LsL1":float(x[7]),
            "worst_IL_db":y["worst_IL_db"],"min_H2_db":y["min_H2_db"],
            "min_H3_db":y["min_H3_db"],
            "pass_H2H3_30":bool(y["min_H2_db"]>=30 and y["min_H3_db"]>=30),
            "critical":y["locations"],
            "max_IC_C_pF":float(np.max(x[8:])),
            "C_above_3_count":int(np.count_nonzero(x[8:]>3+1e-8))}

def fit(policy,seed,tag,kfixed,cap,points=9,iters=180):
    ev=source.Evaluator(policy,CFG,points)
    bounds=ev.bounds.copy()
    bounds[8:,1]=cap
    free=np.array([i for i in range(len(seed)) if (not kfixed or i not in (6,7))])
    x0=np.array(seed,float)
    if kfixed:
        x0[6]=+.1;x0[7]=-.1
    x0=np.clip(x0,bounds[:,0],bounds[:,1])
    active_bounds=[tuple(bounds[i]) for i in free]+[(0.,20.)]
    def build(y):
        x=np.array(x0,copy=True)
        x[free]=y[:-1]
        return x
    def cons(y):
        v=ev.il(build(y))
        return np.where(ev.role==0,y[-1]-v,v-TARGET)
    def obj(y):
        return float(y[-1])
    y0=np.r_[x0[free],ev.summary(x0)["worst_IL_db"]]
    result=minimize(obj,y0,method="SLSQP",bounds=active_bounds,
        constraints={"type":"ineq","fun":cons},
        options={"maxiter":iters,"ftol":1e-8})
    x=build(result.x)
    data={"tag":tag,"k_fixed_at_limits":kfixed,
          "out_of_spec_C_relaxation":cap>3,"IC_C_max_pF":cap,
          "solver_success":bool(result.success),
          "message":str(result.message),
          "nit":int(result.nit),"nfev":int(result.nfev),
          "coarse_min_slack_db":float(np.min(cons(result.x))),
          "coarse":row(ev,x,tag+"_coarse"),
          "vector":x.tolist()}
    print("FIT",tag,"IL",data["coarse"]["worst_IL_db"],
          "H2",data["coarse"]["min_H2_db"],
          "H3",data["coarse"]["min_H3_db"],
          "slack",data["coarse_min_slack_db"],
          "converged",result.success,flush=True)
    return data

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--maxiter",type=int,default=180)
    ap.add_argument("--dense",type=int,default=1001)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    p=load_constraint("RF-T005",allow_trial=True)
    assert (source.HERE/"manifest.json").exists()
    dense=source.Evaluator(p,CFG,args.dense)
    reference=row(dense,START,"saved_at_0p07937_and_minus_0p08430")
    rows=[]
    for label,k1,k2 in (
        ("k_zero",0,0),
        ("k_abs_0p05",.05,-.05),
        ("k_saved",float(START[6]),float(START[7])),
        ("k1_max_only",+.1,float(START[7])),
        ("k2_max_only",float(START[6]),-.1),
        ("both_k_max",+.1,-.1),
        ("k_more_inductive_other_sign",+.1,+.1),
        ("both_k_reversed",-.1,+.1),
    ):
        x=START.copy();x[6:8]=[k1,k2]
        rows.append(row(dense,x,label))
        print("DIRECT",label,"worstIL",rows[-1]["worst_IL_db"],
              "H2",rows[-1]["min_H2_db"],"H3",rows[-1]["min_H3_db"],flush=True)
    fits=[]
    for tag,kfixed,cap in [
       ("original_k_free_C3",False,3.),
       ("k_both_extrema_C3",True,3.),
       ("k_both_extrema_C4_NONCOMPLIANT",True,4.),
       ("k_free_C4_NONCOMPLIANT",False,4.),
    ]:
        fit_result=fit(p,START,tag,kfixed,cap,points=9,iters=args.maxiter)
        fit_result["dense"]=row(dense,fit_result["vector"],tag+"_dense")
        fits.append(fit_result)
        print("DENSE",tag,fit_result["dense"]["worst_IL_db"],
             fit_result["dense"]["min_H2_db"],
             fit_result["dense"]["min_H3_db"],flush=True)
    out={
      "experiment":"EXP-043","constraint_id":"RF-T005","phase":2,
      "question":"Why is k not at +/-0.1 and is 3pF C ceiling causal?",
      "reference_checkpoint":"checkpoints/zero_gjm_double.json",
      "status":"executed_numeric_sensitivity_if_actions_complete",
      "RF_T005_compliance":"Only rows with C_max<=3 and legal k are compliant.",
      "circuit":"3 HV Q25 L0,L1,Ls; 3 PCB Cs 0.2pF Q40; three IC Cv Q35",
      "baseline":reference,"fixed_components_perturbations":rows,
      "reoptimized_cases":fits,
      "band_segments":28,"dense_points_per_segment":args.dense,
      "warning":"Cmax=4pF diagnostic variants are explicitly INVALID as RF-T005 candidates",
      "limitations":["local SLSQP and 9pt coarse fitting","independent MNA of reoptimized vectors not yet done",
                     "finite dense grid not global guarantee",
                     "Q25 assumption and lossless mutual k; no mutual resistance/core loss",
                     "physical coupling and SRF unverified"] }
    target=args.out or source.ROOT/"results"/"EXP-043"/"diagnose_k_vs_C.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print("RESULT",target,flush=True)

if __name__=="__main__":main()
