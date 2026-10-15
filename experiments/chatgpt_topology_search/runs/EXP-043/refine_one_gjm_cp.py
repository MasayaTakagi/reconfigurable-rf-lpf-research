#!/usr/bin/env python3
"""EXP-043 RF-T005 Phase2: one GJM Cp, two PCB, one shunt L topology/refinement.

Authorized continuation of reserved EXP-043, not a new phase/constraint.
Mandatory external S2Ps, Rsource 50, Zload=60-j40, H2/H3 >=30.0dB,
3 tuning C 0..3pF Q35, 2 PCB C 0.02..0.2pF Q40,
one GJM Cp Q80, exactly three LQP02HV Q25, neighboring |k|<=0.10.
All components and magnetic k shared across 6 band settings.
No global optimality or SRF/EM claims.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
import search_3l as source
from lpf.constraint_versions import load_constraint

HERE=Path(__file__).resolve().parent
# each item is (Cf0 edge, Cf1 edge), (Cv0 edge, Cv1 edge, Cv2 edge)
CIRCUITS={
 "baseline": (((0,1),(1,2)),((3,-1),(0,1),(1,2))),
 "cv0_bridge_input": (((0,1),(1,2)),((0,3),(0,1),(1,2))),
 "cv0_bridge_output": (((0,1),(1,2)),((2,3),(0,1),(1,2))),
 "cv0_tap_ground": (((0,1),(1,2)),((1,-1),(0,1),(1,2))),
 "cv1_bridge_input": (((0,1),(1,2)),((3,-1),(0,3),(1,2))),
 "cv1_shunt_inductor": (((0,1),(1,2)),((3,-1),(1,3),(1,2))),
 "cv2_bridge_output": (((0,1),(1,2)),((3,-1),(0,1),(2,3))),
 "cv2_input_output": (((0,1),(1,2)),((3,-1),(0,1),(0,2))),
 "cv2_shunt_inductor": (((0,1),(1,2)),((3,-1),(0,1),(1,3))),
 "cf0_input_to_tip": (((0,3),(1,2)),((3,-1),(0,1),(1,2))),
 "cf1_output_to_tip": (((0,1),(2,3)),((3,-1),(0,1),(1,2))),
 "cf0_input_to_output": (((0,2),(1,2)),((3,-1),(0,1),(1,2))),
 "cf1_input_to_output": (((0,1),(0,2)),((3,-1),(0,1),(1,2))),
 "cf0_tap_ground": (((1,-1),(1,2)),((3,-1),(0,1),(1,2))),
 "cf1_out_ground": (((0,1),(2,-1)),((3,-1),(0,1),(1,2)))
}
BASE_VECTOR=np.array(json.loads((HERE/"checkpoints"/"gjm_cp.json").read_text())["vector"],float)
BASE_VARIANT="EXP043_area3p667"
SOURCE_CB=source.CF_EDGES

def make_ev(policy,name,points):
    cf,cv=CIRCUITS[name]
    # Assign only approved topological positions; shunt Cp GJM is unchanged.
    source.CF_EDGES=(cf[0],cf[1],(3,-1))
    source.CONFIGS[BASE_VARIANT]=(("PCB","PCB","GJM"),cv)
    ev=source.Evaluator(policy,BASE_VARIANT,points)
    assert abs(ev.area-(3+2/3))<1e-8
    assert np.allclose(ev.Q_C[:3],[40,40,80])
    assert np.max(ev.bounds[3:5,1])<=.2
    assert ev.bounds[5,1]>=3 and np.max(ev.bounds[8:,1])==3
    return ev

def summary(e,x):
    s=e.summary(x)
    return {**s,"k":np.array(x[6:8]).tolist(),
        "L_nH":np.array(x[:3]).tolist(),"fixed_C_pF":np.array(x[3:6]).tolist(),
        "max_Cv_pF":float(np.max(x[8:])),
        "PCB_C_at_max":int(np.sum(np.array(x[3:5])>=.2-1e-8)),
        "tune_C_at_max":int(np.sum(np.array(x[8:])>=3-1e-8))}
def report_pass(s):return bool(s["min_H2_db"]>=30 and s["min_H3_db"]>=30)

def loss_at(e,x,idx):
    w=e.omega[idx]
    y=np.r_[x[3:6],x[8+3*e.setting[idx]:11+3*e.setting[idx]]]
    adm=w*1e-12*y/(1/e.Q_C-1j)
    ti,to=e.pre[idx],e.post[idx]
    zload=60-40j
    di=ti[0,1]+50*ti[1,1]
    ys=(ti[0,0]+50*ti[1,0])/di
    src=1/di
    do=to[0,0]*zload+to[0,1]
    yl=(to[1,0]*zload+to[1,1])/do
    _,lm,H=e.matrices(x)
    A=np.zeros((7,7),complex)
    A[:4,:4]=e.BC@np.diag(adm)@e.BC.T
    A[0,0]+=ys
    A[2,2]+=yl
    A[:4,4:]=source.BL
    A[4:,:4]=source.BL.T
    A[4:,4:]=-w*1e-9*H
    rhs=np.zeros(7,complex);rhs[0]=src
    sol=np.linalg.solve(A,rhs)
    V,I=sol[:4],sol[4:]
    loadP=60*abs(V[2]/do)**2
    il=-10*np.log10(max(200*loadP,1e-300))
    indP=float(w*1e-9*np.sum(x[:3]*abs(I)**2)/25)
    Qmag=25*float(np.real(np.vdot(I,lm@I)))/float(np.sum(x[:3]*abs(I)**2))
    iin=src-ys*V[0]
    ve=ti[0,0]*V[0]+ti[0,1]*iin
    ie=ti[1,0]*V[0]+ti[1,1]*iin
    pref=abs(1-100*ie)**2/200
    pin=float(np.real(ve*np.conj(ie)-V[0]*np.conj(iin)))
    pout=float(np.real(V[2]*np.conj(yl*V[2]))-loadP)
    pc=adm.real*abs(e.BC.T@V)**2
    fixP=float(pc[:3].sum());varP=float(pc[3:].sum())
    residual=float(.005-(pref+pin+pout+indP+fixP+varP+loadP))
    if abs(residual)>1e-10 or min(pref,pin,pout,indP,fixP,varP,loadP)<-1e-10:
        raise AssertionError("invalid passive power balance")
    return il,Qmag,indP*1000,abs(residual)

def verify(e,x):
    abc=e.il(x)
    max_d=0; max_r=0
    qvals=[]
    for idx in range(len(e.f)):
        a,b,c,r=loss_at(e,x,idx)
        max_d=max(max_d,abs(a-abc[idx]));max_r=max(max_r,r)
        if e.role[idx]==0:
            qvals.append([float(e.f[idx]),float(b),float(c)])
    return {"independent_7x7_points":len(e.f),
        "max_IL_error_db":float(max_d),"max_power_residual_W":float(max_r),
        "pass":bool(max_d<1e-8 and max_r<1e-9),
        "passband_Q_L_and_coil_loss_selected_probes":qvals[:15]}

def fit(policy,name,starts,coarse_points,refine_points,dense_points,maxiter,seed,target):
    coarse=make_ev(policy,name,coarse_points)
    dense=make_ev(policy,name,dense_points)
    fine=make_ev(policy,name,refine_points)
    rng=np.random.default_rng(seed+sum(ord(c) for c in name))
    allruns=[]
    bounds=[tuple(v) for v in coarse.bounds]
    for run in range(starts):
        x0=BASE_VECTOR.copy()
        if run:
            x0[:3]*=np.exp(rng.normal(0,.07 if run%3 else .15,3))
            x0[3:6]*=np.exp(rng.normal(0,.12 if run%2 else .35,3))
            x0[6:8]+=rng.normal(0,.01 if run%2 else .025,2)
            x0[8:]+=rng.normal(0,.1 if run%2 else .25,18)
        x0=np.clip(x0,coarse.bounds[:,0],coarse.bounds[:,1])
        if name!="baseline":
            def penalty(z):
                try:
                    vals=coarse.il(z)
                    harmonic=np.maximum(target-vals[coarse.role>0],0)
                    return float(logsumexp(5*vals[coarse.role==0])/5+
                        3*np.max(harmonic)**2+20*np.mean(harmonic**2))
                except (ValueError,np.linalg.LinAlgError):
                    return 1e6
            # Short feasibility warmup on changed circuit connections.
            if run<3:
                try:
                    opt=minimize(penalty,x0,method="L-BFGS-B",bounds=bounds,
                        options={"maxiter":80,"maxfun":8000,"ftol":1e-8})
                    if np.isfinite(opt.fun):x0=np.clip(opt.x,coarse.bounds[:,0],coarse.bounds[:,1])
                except (ValueError,np.linalg.LinAlgError):
                    pass
        def epigraph(y,e):
            vals=e.il(y[:-1])
            return np.where(e.role==0,y[-1]-vals,vals-target)
        def opt_stage(e,x,steps):
            v=np.r_[x,e.summary(x)["worst_IL_db"]]
            return minimize(lambda z:float(z[-1]),v,method="SLSQP",
                 constraints={"type":"ineq","fun":lambda z:epigraph(z,e)},
                 bounds=[tuple(v) for v in e.bounds]+[(0,10)],
                 options={"maxiter":steps,"ftol":2e-9})
        try:
            csol=opt_stage(coarse,x0,maxiter)
            xc=np.clip(csol.x[:-1],coarse.bounds[:,0],coarse.bounds[:,1])
            fc=summary(coarse,xc)
            rsol=opt_stage(fine,xc,max(80,maxiter//2))
            xx=np.clip(rsol.x[:-1],coarse.bounds[:,0],coarse.bounds[:,1])
            fs=summary(fine,xx)
            ds=summary(dense,xx)
            rec={"start":run,"seed":int(seed),"coarse_success":bool(csol.success),
                "refine_success":bool(rsol.success),
                "coarse_solver_message":str(csol.message),
                "refine_solver_message":str(rsol.message),
                "coarse":fc,"fine":fs,"dense":ds,"vector":xx.tolist(),
                "dense_strict_30db":report_pass(ds)}
        except (ValueError,np.linalg.LinAlgError) as err:
            rec={"start":run,"solver_error":str(err),"dense_strict_30db":False}
        allruns.append(rec)
        print("TRY",name,run,"IL",rec.get("dense",{}).get("worst_IL_db"),
              "H2",rec.get("dense",{}).get("min_H2_db"),
              "H3",rec.get("dense",{}).get("min_H3_db"),
              "PASS",rec["dense_strict_30db"],flush=True)
    valid=[r for r in allruns if r["dense_strict_30db"]]
    best=min(valid,key=lambda q:q["dense"]["worst_IL_db"]) if valid else None
    if name=="baseline":
        orig=summary(dense,BASE_VECTOR)
        old={"start":"preserved_original","dense":orig,
             "vector":BASE_VECTOR.tolist(),"dense_strict_30db":report_pass(orig)}
        if old["dense_strict_30db"] and (
            best is None or orig["worst_IL_db"]<best["dense"]["worst_IL_db"]
        ):
            best=old
    independent=None
    if best:
        e=make_ev(policy,name,3)
        independent=verify(e,np.array(best["vector"]))
        assert independent["pass"],"independent branch-current MNA failed"
    return {
        "experiment":"EXP-043","continuation":"one-GJM-CP 3L IL minimax search",
        "variant":name,"phase":"Phase 2","constraint_id":"RF-T005",
        "L_edges":source.L_EDGES,
        "fixed_C_edges":(*CIRCUITS[name][0],(3,-1)),
        "fixed_C_types":["PCB","PCB","GJM"],
        "variable_C_edges":CIRCUITS[name][1],
        "physical_chip_L_order":["L0","Ls","L1"],
        "area":3+2/3,"iterations_max":maxiter,"starts":starts,
        "harmonic_target_with_margin":target,
        "frequency_grid":{"coarse":coarse_points,"refine":refine_points,
                          "verification":dense_points,"segments":28},
        "reference_original_0p896103794db":"checkpoints/gjm_cp.json",
        "settings":source.CASES,
        "runs":allruns,"best":best,"independent_MNA":independent,
        "note":"Valid minima require 30dB H2/H3 over finite dense mesh; not continuous proof/global bound"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",choices=CIRCUITS,required=True)
    ap.add_argument("--starts",type=int,default=4)
    ap.add_argument("--coarse",type=int,default=9)
    ap.add_argument("--refine",type=int,default=31)
    ap.add_argument("--dense",type=int,default=1001)
    ap.add_argument("--maxiter",type=int,default=180)
    ap.add_argument("--target",type=float,default=30.02)
    ap.add_argument("--seed",type=int,default=20261017)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    p=load_constraint("RF-T005",allow_trial=True)
    assert (HERE/"manifest.json").exists()
    assert not a.target<30.0
    result=fit(p,a.variant,a.starts,a.coarse,a.refine,a.dense,
               a.maxiter,a.seed,a.target)
    path=a.out or source.ROOT/"results"/"EXP-043"/("low_loss_"+a.variant+".json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    q=result["best"]
    print("FINAL",a.variant,"best",q["dense"] if q else None,
          "MNA",result["independent_MNA"]["pass"] if q else None,
          "OUTPUT",path,flush=True)
if __name__=="__main__":
    main()
