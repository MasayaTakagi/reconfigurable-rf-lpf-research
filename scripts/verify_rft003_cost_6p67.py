#!/usr/bin/env python3
"""RF-T003 6L cost6+2/3: independently validate both 30.003 and 30.10dB variants.
Finite segmented nodal and separate branch-current MNA; no optimizer rerun.
python scripts/verify_rft003_cost_6p67.py --points 7001
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from lpf.circuit import Branch, solve
from lpf.independent import solve_gain
from lpf.evaluate import CASES,load_bands
from lpf.constraint_versions import load_constraint,constraint_fingerprint

DATA=ROOT/"data/validation/rft003_20261013/six_L_one_GJM_cost_6p67.json"
PAVS=.005
ZLOAD=60-40j

def incidence(edges,n=5):
    B=np.zeros((n,len(edges)),float)
    for j,(a,b) in enumerate(edges):
        if a:B[a-1,j]+=1
        if b:B[b-1,j]-=1
    return B

def check(candidate,points):
    assert points>=3 and len(candidate["L_edges"])==6
    assert candidate["L_series"]==["LQP02HV"]*6
    assert candidate["L_Q"]==[25]*6
    assert all(.4<=x<=27+1e-8 for x in candidate["L_nH"])
    assert candidate["variable_C_edges"]==[[5,0],[2,3]]
    assert [2,3] in candidate["L_edges"]  # variable bridge bypasses fixed L3
    assert all(0<=x<=4 for v in candidate["variable_C_by_case_pf"].values() for x in v)
    fixed=candidate["fixed_capacitors"]
    assert sum(z["kind"]=="PCB_PATTERN_C" for z in fixed)==3
    assert sum(z["kind"]=="GJM01" for z in fixed)==1
    assert all(
        (z["kind"]=="PCB_PATTERN_C" and z["Q"]==40 and .02-1e-12<=z["C_pf"]<=.2+1e-12)
        or (z["kind"]=="GJM01" and z["Q"]==80 and z["C_pf"]<=100)
        for z in fixed)
    expected_cost=6+sum(z["kind"]=="GJM01" for z in fixed)*(2/3)
    assert abs(expected_cost-candidate["chip_cost"])<1e-9
    L=np.array(candidate["L_nH"])*1e-9
    Q=np.array(candidate["L_Q"],float)
    row=candidate["physical_chip_row"]
    assert sorted(row)==list(range(6))
    K=np.eye(6)
    for (a,b),k in zip(zip(row,row[1:]),candidate["adjacent_k"]):
        assert abs(k)<=.4+1e-10
        K[a,b]=K[b,a]=k
    assert np.linalg.eigvalsh(K).min()>0
    M=K*np.sqrt(np.outer(L,L))
    assert np.linalg.eigvalsh(M).min()>0
    B=incidence(candidate["L_edges"])
    coil=B@np.linalg.solve(np.diag(L/Q)+1j*M,B.T)
    cap_edges=[z["edge"] for z in fixed]+candidate["variable_C_edges"]
    D=incidence(cap_edges)
    CQ=np.array([z["Q"] for z in fixed]+[80,80])
    port=np.diag(np.array([1/50,0,1/ZLOAD,0,0],complex))
    src=np.array([1/50,0,0,0,0],complex)
    by_case={};max_delta=0.;max_balance=0.;spots=0
    bands=load_bands()
    for case in CASES:
        C=np.r_[[z["C_pf"] for z in fixed],candidate["variable_C_by_case_pf"][case]]*1e-12
        cmat=D@np.diag(C/(1/CQ-1j))@D.T
        regions={"UL":[],"DL":[],"H2":[],"H3":[]}
        inductors=tuple(Branch(int(a),int(b),float(v),float(q))
                        for (a,b),v,q in zip(candidate["L_edges"],L,Q))
        caps=tuple(Branch(int(a),int(b),float(v),float(q))
                   for (a,b),v,q in zip(cap_edges,C,CQ))
        params=dict(n_nodes=5,source_node=1,load_node=3,inductors=inductors,
                    capacitors=caps,coupling=K,source_voltage=1.,
                    source_ohms=50.,load_ohms=ZLOAD)
        for band in bands:
            if band["case"]!=case:continue
            lo,hi=float(band["low_mhz"]),float(band["high_mhz"])
            f=np.linspace(lo,hi,points)
            w=2*np.pi*1e6*f
            Y=port[None,:,:]+coil[None,:,:]/w[:,None,None]+w[:,None,None]*cmat[None,:,:]
            v=np.linalg.solve(Y,np.broadcast_to(src,(points,5))[...,None])[:,:,0]
            loadp=np.abs(v[:,2])**2*(1/ZLOAD).real
            db=-10*np.log10(loadp/PAVS)
            regions[band["region"]].extend(db.tolist())
            for freq in (lo,(lo+hi)*.5,hi):
                x=solve(freq*1e6,**params)
                gain=solve_gain(freq*1e6,**params)
                max_delta=max(max_delta,abs(x["il_db"]+10*np.log10(gain)))
                max_balance=max(max_balance,abs(x["power_residual"]))
                spots+=1
        by_case[case]=[max(regions["UL"]+regions["DL"]),
                       min(regions["H2"]),min(regions["H3"])]
    IL=max(q[0] for q in by_case.values())
    H2=min(q[1] for q in by_case.values())
    H3=min(q[2] for q in by_case.values())
    assert spots==84 and max_delta<1e-8 and max_balance<1e-12
    assert H2>=30-1e-6 and H3>=30-1e-6
    if points==7001:
        expected=candidate["validated_dense"]
        for actual,key in ((IL,"worst_IL_db"),(H2,"min_H2_db"),(H3,"min_H3_db")):
            assert abs(actual-expected[key])<1e-7,(key,actual,expected[key])
    passed=IL<=.30
    if points==7001:
        assert passed==candidate["validated_dense"]["passes_RF_T003_nominal"]
    return dict(id=candidate["candidate_id"],IL_db=IL,min_H2_db=H2,
                min_H3_db=H3,chip_cost=candidate["chip_cost"],
                IL_goal_pass=passed,independent_MNA_spots=spots,
                max_independent_delta_db=max_delta,
                max_power_residual_W=max_balance,
                K_min_eigenvalue=float(np.linalg.eigvalsh(K).min()),
                points_per_segment=points,by_case=by_case)

def verify(points=9):
    saved=json.loads(DATA.read_text(encoding="utf-8"))
    assert saved["constraint_id"]=="RF-T003" and saved["phase"]=="Phase 2"
    policy=load_constraint("RF-T003",allow_trial=True)
    assert constraint_fingerprint(policy)=="e0c45f7094ced1ed2ccb91cae474c7c3c1a6af73a495a2a9cf8f512ccb45ab08"
    trial=json.loads((ROOT/"data/constraints/trial/RF-T003.json").read_text(encoding="utf-8"))
    assert trial["study_variable_c_layout"]=={"branch_count":2,"shunt_to_ground":1,"non_ground_bridge":1}
    t=saved["topology"]
    out={}
    for name in ("nominal","margin"):
        c=saved[name]
        candidate=dict(
          candidate_id=c["id"],L_edges=t["L_edges"],L_series=t["L_series"],
          L_Q=t["L_Q"],L_nH=c["L_nH"],physical_chip_row=t["physical_row"],
          adjacent_k=c["adjacent_signed_k"],
          variable_C_edges=t["variable_edges"],variable_C_by_case_pf=c["Cv_by_setting_pf"],
          fixed_capacitors=[dict(edge=z["edge"],kind=z["part"],Q=z["Q"],C_pf=z["pF"])
                            for z in c["fixed_C"]],
          chip_cost=t["chip_area_cost"],
          validated_dense=dict(worst_IL_db=c["validation"]["worst_IL_db"],
             min_H2_db=c["validation"]["min_UL_H2_db"],
             min_H3_db=c["validation"]["min_UL_H3_db"],
             passes_RF_T003_nominal=True)
        )
        out[name]=check(candidate,points)
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--points",type=int,default=9)
    a=p.parse_args()
    print(json.dumps(verify(a.points),indent=2,ensure_ascii=False))
