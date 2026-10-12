#!/usr/bin/env python3
"""RF-T003 seven-L candidate: finite segmented nodal vs separate full current MNA.

Usage from repository root:
  python scripts/verify_rft003_7l_best.py --points 9
  python scripts/verify_rft003_7l_best.py --points 7001

Only the stored circuit is re-evaluated.  Optimization, EM, Q(f), SRF,
physical coupling feasibility, switch losses, tolerances and continuous-
interval certification are not performed.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/validation/rft003_20261013/seven_L_3PCB_best.json"
BANDS=ROOT/"data/bands.csv"
CASES=("B71","B12","B28","B13+B14","B26","B8")
ZL=60-40j
PAVS=.005

def incidence(edges,n=5):
    A=np.zeros((n,len(edges)))
    for j,(a,b) in enumerate(edges):
        if a:A[a-1,j]+=1
        if b:A[b-1,j]-=1
    return A

def independently_stamped_full_mna(f_mhz,L,Q,M,edges,C,CQ,cap_edges):
    """No reused nodal-admittance or incidence matrices."""
    w=2*np.pi*f_mhz*1e6
    y=np.diag(np.array([1/50,0,1/ZL,0,0],complex))
    for (a,b),cap,q in zip(cap_edges,C,CQ):
        if cap==0:continue
        adm=w*cap/(1/q-1j)
        if a:y[a-1,a-1]+=adm
        if b:y[b-1,b-1]+=adm
        if a and b:y[a-1,b-1]-=adm;y[b-1,a-1]-=adm
    E=np.zeros((5,len(L)))
    for j,(a,b) in enumerate(edges):
        if a:E[a-1,j]+=1
        if b:E[b-1,j]-=1
    Z=np.diag(w*L/Q)+1j*w*M
    state=np.linalg.solve(np.block([[y,E],[-E.T,Z]]),
         np.r_[np.array([1/50,0,0,0,0],complex),np.zeros(len(L),complex)])
    v,i=state[:5],state[5:]
    load=abs(v[2])**2*(1/ZL).real
    pref=PAVS*abs(1-2*v[0])**2
    pl=float(np.sum(abs(i)**2*w*L/Q))
    pc=0.
    for (a,b),cap,q in zip(cap_edges,C,CQ):
        delta=(v[a-1] if a else 0)-(v[b-1] if b else 0)
        pc+=abs(delta)**2*(w*cap/(1/q-1j)).real
    return float(-10*np.log10(load/PAVS)),float(PAVS-load-pref-pl-pc)

def verify(points=9):
    assert points>=3
    saved=json.loads(DATA.read_text(encoding="utf-8"))
    trial=json.loads((ROOT/"data/constraints/trial/RF-T003.json").read_text(encoding="utf-8"))
    registry=json.loads((ROOT/"data/constraints/registry.json").read_text(encoding="utf-8"))
    c=saved["circuit"]
    assert saved["constraint_id"]=="RF-T003" and saved["phase"]=="Phase 2"
    assert registry["active_formal_id"]=="RF-F001"
    assert registry["trial"]["RF-T003"]["state"]=="study_authorized"
    assert trial["study_variable_c_layout"]==dict(branch_count=2,shunt_to_ground=1,non_ground_bridge=1)
    assert trial["overrides"]["evaluation"]["full_phase2"]["nominal_h2_h3_target_db"]==30
    assert len(c["L_edges"])==7 and c["L_series"]==["LQP02HV"]*7
    assert c["L_Q"]==[25]*7
    assert all(.4<=x<=27+1e-9 for x in c["L_nH"])
    assert sorted(c["physical_chip_row"])==list(range(7))
    assert len(c["adjacent_k"])==6 and all(abs(x)<=.4+1e-10 for x in c["adjacent_k"])
    fixed=c["fixed_capacitors"]
    assert sum(x["kind"]=="GJM01" and x["Q"]==80 for x in fixed)==2
    assert sum(x["kind"]=="PCB_PATTERN_C" and x["Q"]==40 and .02<=x["C_pf"]<=.2 for x in fixed)==3
    assert c["variable_C_edges"]==[[5,0],[2,3]] and [2,3] in c["L_edges"]
    assert all(0<=v<=4 for z in c["variable_C_by_case_pf"].values() for v in z)
    assert abs(c["area_cost"]-(7+4/3))<1e-9
    K=np.eye(7)
    row=c["physical_chip_row"]
    for j,k in enumerate(c["adjacent_k"]):
        a,b=row[j:j+2];K[a,b]=K[b,a]=k
    assert np.linalg.eigvalsh(K).min()>0
    L=np.asarray(c["L_nH"])*1e-9
    Q=np.asarray(c["L_Q"])
    M=K*np.sqrt(np.outer(L,L))
    assert np.linalg.eigvalsh(M).min()>0
    B=incidence(c["L_edges"])
    Yn0=B@np.linalg.solve(np.diag(L/Q)+1j*M,B.T)
    ce=[z["edge"] for z in fixed]+c["variable_C_edges"]
    D=incidence(ce)
    CQ=np.asarray([z["Q"] for z in fixed]+[80,80])
    port=np.diag(np.array([1/50,0,1/ZL,0,0],complex))
    rhs=np.array([1/50,0,0,0,0],complex)
    bands=list(csv.DictReader(BANDS.open(encoding="utf-8",newline="")))
    assert len(bands)==28
    per_case={}
    max_delta=max_residual=0.
    checked=0
    for case in CASES:
        C=np.r_[[z["C_pf"] for z in fixed],c["variable_C_by_case_pf"][case]]*1e-12
        Yc0=D@np.diag(C/(1/CQ-1j))@D.T
        regions={"UL":[],"DL":[],"H2":[],"H3":[]}
        for band in bands:
            if band["case"]!=case:continue
            f=np.linspace(float(band["low_mhz"]),float(band["high_mhz"]),points)
            w=f*2*np.pi*1e6
            Y=port[None,:,:]+Yn0[None,:,:]/w[:,None,None]+w[:,None,None]*Yc0[None,:,:]
            v=np.linalg.solve(Y,np.broadcast_to(rhs,(len(f),5))[...,None])[:,:,0]
            g=abs(v[:,2])**2*(1/ZL).real/PAVS
            db=-10*np.log10(np.maximum(g,1e-300))
            regions[band["region"]].extend(db.tolist())
            for h in (f[0],f[len(f)//2],f[-1]):
                x,balance=independently_stamped_full_mna(h,L,Q,M,c["L_edges"],C,CQ,ce)
                yh=port+Yn0/(h*2*np.pi*1e6)+(h*2*np.pi*1e6)*Yc0
                vv=np.linalg.solve(yh,rhs)
                nodal_db=-10*np.log10(abs(vv[2])**2*(1/ZL).real/PAVS)
                max_delta=max(max_delta,abs(x-nodal_db))
                max_residual=max(max_residual,abs(balance))
                checked+=1
        per_case[case]=[max(regions["UL"]+regions["DL"]),min(regions["H2"]),min(regions["H3"])]
    il=max(x[0] for x in per_case.values())
    h2=min(x[1] for x in per_case.values())
    h3=min(x[2] for x in per_case.values())
    assert checked==84 and max_delta<1e-8 and max_residual<1e-12
    assert h2>=30-1e-7 and h3>=30-1e-7
    if points==7001:
        official=saved["results"]
        assert abs(il-official["worst_passband_IL_db"])<1e-7
        assert abs(h2-official["min_UL_H2_db"])<1e-7
        assert abs(h3-official["min_UL_H3_db"])<1e-7
    return dict(candidate=saved["candidate_id"],constraint_id="RF-T003",
         points_per_segment=points,worst_IL_db=il,min_H2_db=h2,min_H3_db=h3,
         augmented_MNA_dimension=12,independent_MNA_points=checked,
         max_MNA_difference_db=max_delta,max_power_balance_residual_W=max_residual,
         K_min_eigenvalue=float(np.linalg.eigvalsh(K).min()),
         chip_area=c["area_cost"],meets_trial_IL_0p30=il<=.30,per_setting=per_case)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--points",type=int,default=9)
    args=p.parse_args()
    print(json.dumps(verify(args.points),indent=2,ensure_ascii=False))
