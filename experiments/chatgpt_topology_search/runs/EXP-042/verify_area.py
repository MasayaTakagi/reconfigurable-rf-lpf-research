#!/usr/bin/env python3
"""Independent external-port 9x9 branch-current MNA for EXP-042 area candidates."""
import argparse,json
from pathlib import Path
import numpy as np
import optimize as base
from optimize import BL,BC,L_ORDER,Evaluator,policy_and_seed

def verify(candidate):
    policy,_ = policy_and_seed()
    for idx in candidate.get("replaced_GJM_with_PCB_fixed_cap_indices", []):
        base.Q_C[idx-4] = 40.
    x = np.array(candidate["selected"]["vector"],float)
    assert x.size==29
    assert np.all((x[11:]>=0)&(x[11:]<=3))
    assert np.all((x[:4]>=.4)&(x[:4]<=27))
    assert np.max(np.abs(x[8:11]))<=.100000001
    L=x[:4]
    M=np.diag(L)
    for n,k in enumerate(x[8:11]):
        a,b=L_ORDER[n:n+2]
        M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
    eig=float(np.min(np.linalg.eigvalsh(M)))
    assert eig>0.
    H=np.diag(L/25)+1j*M
    ev=Evaluator(policy,3)
    eval_il=ev.il(x)
    worst=0.
    power_residual=0.
    for p,(f,si) in enumerate(zip(ev.f,ev.setting)):
        w=2*np.pi*f*1e6
        cap=np.r_[x[4:8],x[11+si*3:14+si*3]]
        yc=w*1e-12*cap/(1/base.Q_C-1j)
        t1=ev.pre[p]
        t2=ev.post[p]
        zin=50.;zl=60-40j
        term1=t1[0,1]+zin*t1[1,1]
        ys=(t1[0,0]+zin*t1[1,0])/term1
        src=1/term1
        term2=t2[0,0]*zl+t2[0,1]
        yl=(t2[1,0]*zl+t2[1,1])/term2
        zL=w*1e-9*H
        A=np.zeros((9,9),complex)
        A[:5,:5]=BC@np.diag(yc)@BC.T
        A[0,0]+=ys
        A[2,2]+=yl
        A[:5,5:]=BL
        A[5:,:5]=BL.T
        A[5:,5:]=-zL
        rhs=np.zeros(9,complex);rhs[0]=src
        sol=np.linalg.solve(A,rhs)
        V,I=sol[:5],sol[5:]
        pout=60*abs(V[2]/term2)**2
        il=-10*np.log10(max(pout*200,1e-300))
        worst=max(worst,abs(il-eval_il[p]))
        i_in=src-ys*V[0]
        i_out=yl*V[2]
        ve=t1[0,0]*V[0]+t1[0,1]*i_in
        ie=t1[1,0]*V[0]+t1[1,1]*i_in
        pref=abs(1-100*ie)**2/200
        p1=np.real(ve*np.conj(ie)-V[0]*np.conj(i_in))
        p2=np.real(V[2]*np.conj(i_out))-pout
        pl=np.real(np.vdot(I,zL@I))
        pc=np.sum(yc.real*abs(BC.T@V)**2)
        residual=abs(1/200-(pref+p1+p2+pl+pc+pout))
        power_residual=max(power_residual,residual)
        assert min(pref,p1,p2,pl,pc,pout)>-1e-10
    report={"experiment":"EXP-042","variant":candidate["variant"],
            "independent_MNA_points":int(len(ev.f)),
            "maximum_IL_difference_db":float(worst),
            "max_power_balance_residual_W":float(power_residual),
            "min_L_eigenvalue_nH":eig,
            "pass":bool(worst<1e-8 and power_residual<1e-9)}
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--result",type=Path,required=True)
    a=ap.parse_args()
    doc=json.loads(a.result.read_text())
    v=verify(doc)
    print(json.dumps(v,ensure_ascii=False),flush=True)
    a.result.with_name(a.result.stem+"_independent.json").write_text(json.dumps(v,indent=2)+"\n")
    if not v["pass"]:
        raise SystemExit(2)

if __name__=="__main__":main()
