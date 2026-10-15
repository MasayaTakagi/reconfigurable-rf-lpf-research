#!/usr/bin/env python3
"""EXP-043 Phase2 RF-T005: isolate fixed PCB C ceiling and GJM substitution.

Keep three HV Q25 chip L, three tuneable IC Q35 branches [0,3]pF, physical
k(L0,Ls),k(Ls,L1) within |k|<=0.1, and required external S2P/load.
For "pcb_0p3" etc, deliberately modify approved PCB 0.2pF upper bound ONLY
in an out-of-spec diagnostic. For GJM variants, model specified Q80 and
area=+2/3 per GJM, with formal GJM max100pF (search cap <=3 pF).
Retune all L, fixed Cs, k, and 6*3 IC Cs together from previous best.
Provide internal 0.02dB H2/H3 margin, full 28-band dense reevaluation,
and independent 7x7 explicit branch-current MNA/power balance.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
import search_3l as base
from lpf.constraint_versions import load_constraint

HERE=Path(__file__).resolve().parent
REF=HERE/"checkpoints"/"zero_gjm_double.json"
SEED=np.array(json.loads(REF.read_text(encoding="utf-8"))["vector"],float)
VARIANTS={
    "baseline": {"gjm":(),"pcbmax":0.2},
    "pcb_0p3_OFFSPEC": {"gjm":(),"pcbmax":0.3},
    "pcb_0p5_OFFSPEC": {"gjm":(),"pcbmax":0.5},
    "gjm_cf0": {"gjm":(0,),"pcbmax":0.2},
    "gjm_cf1": {"gjm":(1,),"pcbmax":0.2},
    "gjm_cp": {"gjm":(2,),"pcbmax":0.2},
    "gjm_cf0_cf1": {"gjm":(0,1),"pcbmax":0.2},
    "gjm_cf0_cp": {"gjm":(0,2),"pcbmax":0.2},
    "gjm_cf1_cp": {"gjm":(1,2),"pcbmax":0.2},
}
CF_LABELS=("Cf0 across L0","Cf1 across L1","Cp shunt to ground")

def evaluator(policy,variant,points):
    e=base.Evaluator(policy,"zero_gjm_double",points)
    cfg=VARIANTS[variant]
    upper=cfg["pcbmax"]
    assert upper in (0.2,0.3,0.5)
    e.bounds[3:6,1]=upper
    for j in cfg["gjm"]:
        e.Q_C[j]=80
        e.bounds[3+j,1]=3.0  # study-specific GJM sweep limit; formal max=100
    e.area=3+2*len(cfg["gjm"])/3
    return e

def metrics(e,x):
    x=np.asarray(x,float)
    m=e.summary(x)
    return {"worst_IL_db":m["worst_IL_db"],
            "min_H2_db":m["min_H2_db"],"min_H3_db":m["min_H3_db"],
            "critical":m["locations"],
            "min_M_eig_nH":m["L_matrix_min_eig_nH"],
            "k":x[6:8].tolist(),"fixed_C_pF":x[3:6].tolist(),
            "max_variable_C_pF":float(np.max(x[8:])),
            "variable_C_saturated_3pF":int(np.sum(x[8:]>=3.-1e-6))}

def calc_ref(policy,variant):
    ev=evaluator(policy,variant,101)
    return metrics(ev,SEED)

def mna_verify(policy,variant,vector,points=3):
    # Independent 7x7 KCL + inductor KVL direct linear solve; no reduced Y
    ev=evaluator(policy,variant,points)
    x=np.asarray(vector,float)
    Ytest=ev.il(x)
    _,M,H=ev.matrices(x)
    maxdiff=0.
    maxbalance=0.
    mincomponentloss=1e6
    for q,(f,si) in enumerate(zip(ev.f,ev.setting)):
        w=2*np.pi*f*1e6
        caps=np.r_[x[3:6],x[8+3*si:11+3*si]]
        capad=w*1e-12*caps/(1/ev.Q_C-1j)
        tin,tout=ev.pre[q],ev.post[q]
        zs=50.;zl=60.-40j
        denin=tin[0,1]+zs*tin[1,1]
        ys=(tin[0,0]+zs*tin[1,0])/denin
        src=1./denin
        denout=tout[0,0]*zl+tout[0,1]
        yl=(tout[1,0]*zl+tout[1,1])/denout
        A=np.zeros((7,7),complex)
        A[:4,:4]=ev.BC@np.diag(capad)@ev.BC.T
        A[0,0]+=ys;A[2,2]+=yl
        A[:4,4:]=base.BL
        A[4:,:4]=base.BL.T
        A[4:,4:]=-w*1e-9*H
        rhs=np.zeros(7,complex);rhs[0]=src
        sol=np.linalg.solve(A,rhs)
        v=sol[:4];i=sol[4:]
        pload=60*abs(v[2]/denout)**2
        actual=-10*np.log10(max(200*pload,1e-300))
        maxdiff=max(maxdiff,abs(actual-Ytest[q]))
        i_in=src-ys*v[0]
        ve=tin[0,0]*v[0]+tin[0,1]*i_in
        ie=tin[1,0]*v[0]+tin[1,1]*i_in
        p_ref=abs(1.-100*ie)**2/200
        p_in=np.real(ve*np.conj(ie)-v[0]*np.conj(i_in))
        p_out=np.real(v[2]*np.conj(yl*v[2]))-pload
        p_l=np.real(np.vdot(i,w*1e-9*H@i))
        p_c=float(np.sum(capad.real*np.abs(ev.BC.T@v)**2))
        maxbalance=max(maxbalance,abs(1/200-(p_ref+p_in+p_out+p_l+p_c+pload)))
        mincomponentloss=min(mincomponentloss,p_ref,p_in,p_out,p_l,p_c,pload)
    return {"sample_points":points*28,"max_IL_difference_db":float(maxdiff),
            "max_power_residual_W":float(maxbalance),
            "min_partial_passive_dissipation_W":float(mincomponentloss),
            "passed":bool(maxdiff<1e-8 and maxbalance<1e-9 and mincomponentloss>-1e-10)}

def fit(policy,variant,starts,maxiter,coarse,dense,seed):
    E=evaluator(policy,variant,coarse)
    rng=np.random.default_rng(seed+sum(ord(c) for c in variant))
    cfg=VARIANTS[variant]
    reference=calc_ref(policy,variant)
    results=[]
    for j in range(starts):
        x0=SEED.copy()
        if j:
            x0[:3]*=np.exp(rng.normal(0,.07,3))
            x0[6:8]+=rng.normal(0,.008,2)
            x0[8:]+=rng.normal(0,.07,18)
        if cfg["gjm"]:
            for idx in cfg["gjm"]:
                # additional starts explore larger fixed capacitance; variable C
                # on same edge loses some capacitance to preserve total
                if j>0 and idx in (0,1):
                    delta=[0.,.2,.6,1.2][j%4]
                    x0[3+idx]+=delta
                    cidx=8+idx+1 # Cv1 parallel Cf0; Cv2 parallel Cf1
                    # n-th setting by stride
                    cv_index=9+idx
                    x0[cv_index::3]-=delta
        x0=np.clip(x0,E.bounds[:,0],E.bounds[:,1])
        def constr(v):
            vals=E.il(v[:-1])
            return np.where(E.role==0,v[-1]-vals,vals-30.02)
        ini=np.r_[x0,max(.01,E.summary(x0)["worst_IL_db"])]
        try:
            sol=minimize(lambda z:z[-1],ini,bounds=[tuple(b) for b in E.bounds]+[(0.,10.)],
                         method="SLSQP",constraints={"type":"ineq","fun":constr},
                         options={"maxiter":maxiter,"ftol":5e-9})
            x=np.clip(sol.x[:-1],E.bounds[:,0],E.bounds[:,1])
            rr={"start":j,"success":bool(sol.success),"message":str(sol.message),
                "iterations":int(sol.nit),"evals":int(sol.nfev),
                "constraint_slack_db":float(np.min(constr(sol.x))),
                "coarse":metrics(E,x),"vector":x.tolist()}
        except (ValueError,np.linalg.LinAlgError) as err:
            rr={"start":j,"success":False,"message":"exception "+str(err),
                "constraint_slack_db":-100,
                "coarse":metrics(E,x0),"vector":x0.tolist()}
        results.append(rr)
        print("FIT",variant,j,"IL",rr["coarse"]["worst_IL_db"],
              "H2",rr["coarse"]["min_H2_db"],"H3",rr["coarse"]["min_H3_db"],
              "k",rr["coarse"]["k"],"Cfix",rr["coarse"]["fixed_C_pF"],
              "success",rr["success"],flush=True)
    def score(r):
        s=r["coarse"]
        fail=max(0,30.-s["min_H2_db"],30.-s["min_H3_db"])
        return (fail>1e-7,fail,s["worst_IL_db"])
    winner=min(results,key=score)
    ed=evaluator(policy,variant,dense)
    final=metrics(ed,winner["vector"])
    check=mna_verify(policy,variant,winner["vector"])
    eligible=cfg["pcbmax"]<=.2
    return {
        "experiment":"EXP-043","condition_id":"RF-T005",
        "phase":2,"variant":variant,
        "eligibility":"RF-T005_compliant" if eligible else "OFF_SPEC_PCB_cap_diagnostic",
        "PCB_max_pF":cfg["pcbmax"],"replaced_fixed_C_index_with_GJM":cfg["gjm"],
        "GJM_Q":80,"PCB_Q":40,"variable_C_Q":35,"variable_C_max_pF":3.,
        "L_Q":25,"k_adjacent_max_abs":.1,"area_cost":E.area,
        "fixed_C_nodes":base.CF_EDGES,
        "reference_same_vector_Q_adjusted":reference,
        "SLSQP_results":results,"selected":winner,
        "verification_grid_points_per_segment":dense,
        "dense_validation":final,
        "dense_30db_PASS":bool(final["min_H2_db"]>=30 and final["min_H3_db"]>=30),
        "interim_0p8db_PASS":bool(final["worst_IL_db"]<=.8),
        "independent_7x7_MNA":check,
        "conclusions_not_yet_global":True,
        "limitations":["local SLSQP 4 starts and finite frequency grid",
                       "PCB 0.3,0.5pF outside RF-T005 regardless of good results",
                       "GJM case physical part parasitics, SRF, PCB EM, Q(f) not checked",
                       "no full 7001-point/segment verification",
                       "constant Q model and assumed mutuals"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--variant",choices=VARIANTS,required=True)
    parser.add_argument("--starts",type=int,default=4)
    parser.add_argument("--maxiter",type=int,default=220)
    parser.add_argument("--coarse",type=int,default=9)
    parser.add_argument("--dense",type=int,default=1001)
    parser.add_argument("--seed",type=int,default=20261016)
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    policy=load_constraint("RF-T005",allow_trial=True)
    reg=json.loads((base.ROOT/"data/constraints/registry.json").read_text())
    assert reg["active_formal_id"]=="RF-F003"
    assert policy["components"]["IC_VARIABLE_C"]["max_branches_principle"]==3
    assert (HERE/"manifest.json").exists()
    result=fit(policy,a.variant,a.starts,a.maxiter,a.coarse,a.dense,a.seed)
    target=a.out or base.ROOT/"results"/"EXP-043"/("pcb_vs_gjm_"+a.variant+".json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("FINAL",a.variant,"eligible",result["eligibility"],
          "area",result["area_cost"],"IL",result["dense_validation"]["worst_IL_db"],
          "H2",result["dense_validation"]["min_H2_db"],
          "H3",result["dense_validation"]["min_H3_db"],
          "MNA",result["independent_7x7_MNA"]["passed"],
          "joint_PASS",result["dense_30db_PASS"] and result["interim_0p8db_PASS"],
          flush=True)
    print("OUTPUT",target,flush=True)

if __name__=="__main__":
    main()
