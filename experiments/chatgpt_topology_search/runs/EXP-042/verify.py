#!/usr/bin/env python3
"""EXP-042: dense RF-T005 check and independent branch-current MNA."""
import json
from pathlib import Path
import numpy as np
from optimize import HERE,ROOT,L_ORDER,BL,BC,Q_C,Evaluator,policy_and_seed
from lpf.port_parasitics import get_two_port_s,s_to_abcd

def independent(x,policy,f,si):
    w=2*np.pi*f*1e6
    L=x[:4]; M=np.diag(L.copy())
    for j,k in enumerate(x[8:11]):
        a,b=L_ORDER[j:j+2];M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
    Z=w*1e-9*(np.diag(L/25)+1j*M)
    cp=np.r_[x[4:8],x[11:].reshape(6,3)[si]]
    yc=w*1e-12*cp/(1/Q_C-1j)
    tin=s_to_abcd(get_two_port_s(policy,"input_parasitic",f*1e6,root=ROOT))
    tout=s_to_abcd(get_two_port_s(policy,"output_parasitic",f*1e6,root=ROOT))
    zs=50;zl=60-40j
    di=tin[0,1]+zs*tin[1,1]
    ys=(tin[0,0]+zs*tin[1,0])/di
    isrc=1/di
    do=tout[0,0]*zl+tout[0,1]
    yl=(tout[1,0]*zl+tout[1,1])/do
    A=np.zeros((9,9),complex); b=np.zeros(9,complex)
    A[:5,:5]=(BC*yc[None,:])@BC.T
    A[0,0]+=ys;A[2,2]+=yl
    A[:5,5:]=BL;A[5:,:5]=BL.T;A[5:,5:]=-Z;b[0]=isrc
    v,i=np.split(np.linalg.solve(A,b),[5])
    pout=zl.real*abs(v[2]/do)**2
    il=-10*np.log10(max(200*pout,1e-300))
    iin=isrc-ys*v[0]
    vext=tin[0,0]*v[0]+tin[0,1]*iin
    iext=tin[1,0]*v[0]+tin[1,1]*iin
    pinpar=np.real(vext*np.conj(iext)-v[0]*np.conj(iin))
    poutpar=np.real(v[2]*np.conj(yl*v[2]))-pout
    pl=np.sum(w*1e-9*L/25*abs(i)**2)
    pc=np.sum(yc.real*abs(BC.T@v)**2)
    prefl=abs(1-100*iext)**2/200
    residual=abs(.005-(prefl+pinpar+poutpar+pl+pc+pout))
    return il,residual,min(prefl,pinpar,poutpar,pl,pc,pout)

def main():
    policy,_=policy_and_seed()
    checkpoints=json.loads((HERE/"selected_checkpoints_rft005.json").read_text())
    fine=Evaluator(policy,7001)
    check=Evaluator(policy,3)
    findings=[]
    for c in checkpoints["candidates"]:
        x=np.asarray(c["params"]["flattened_vector"],float)
        dense=fine.summary(x)
        quick=check.il(x)
        comparisons=[independent(x,policy,float(f),int(si))
                     for f,si in zip(check.f,check.setting)]
        diff=max(abs(a[0]-b) for a,b in zip(comparisons,quick))
        power=max(a[1] for a in comparisons)
        minloss=min(a[2] for a in comparisons)
        assert len(comparisons)==84 and diff<1e-8 and power<1e-10 and minloss>=-1e-10
        report={"id":c["id"],"grid_points_per_segment":7001,"segments":28,
                "dense":dense,"pass30":dense["min_h2_db"]>=30 and dense["min_h3_db"]>=30,
                "pass35":dense["min_h2_db"]>=35 and dense["min_h3_db"]>=35,
                "independent_MNA_points":84,"max_IL_difference_db":diff,
                "max_power_balance_residual_W":power,"min_component_dissipation_W":minloss}
        findings.append(report)
        print(json.dumps(report),flush=True)
    result={"experiment":"EXP-042","condition":"RF-T005",
            "source":"actual frozen two-port Touchstone S2P","verification":findings,
            "continuous_band_proof":False,"Qf_SRF_EM_checked":False}
    out=ROOT/"results/EXP-042/verification_7001.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print("saved",out,flush=True)

if __name__=="__main__":main()
