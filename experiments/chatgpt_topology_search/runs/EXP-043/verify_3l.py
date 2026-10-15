#!/usr/bin/env python3
"""Independent explicit branch-current MNA vs EXP-043 four-node 3L model.

Verifies frozen external S2P cascade transducer-power and full power balance.
No optimizer matrices or reduced Y two-port are used in circuit equation.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import search_3l as source
from lpf.constraint_versions import load_constraint

def verify(candidate,points=3):
    assert candidate["experiment"]=="EXP-043"
    cfg=candidate["variant"]
    if cfg not in source.CONFIGS:
        raise ValueError("This checker supports source search_3l variants only")
    p=load_constraint("RF-T005",allow_trial=True)
    ev=source.Evaluator(p,cfg,points)
    x=np.array(candidate["vector"],float)
    assert len(x)==26
    B_L=source.BL; B_C=ev.BC
    predicted=ev.il(x)
    _,M,H=ev.matrices(x)
    assert np.min(np.linalg.eigvalsh(M))>0
    worst=0.
    power_max=0.
    negative=0
    for z,(f,setting) in enumerate(zip(ev.f,ev.setting)):
        w=2*np.pi*f*1e6
        cs=np.r_[x[3:6],x[8+3*setting:11+3*setting]]
        ys=w*1e-12*cs/(1./ev.Q_C-1j)
        t1=ev.pre[z];t2=ev.post[z]
        zsrc=50.;zl=60.-40j
        tin=t1[0,1]+zsrc*t1[1,1]
        ysrc=(t1[0,0]+zsrc*t1[1,0])/tin
        inj=1./tin
        tout=t2[0,0]*zl+t2[0,1]
        yload=(t2[1,0]*zl+t2[1,1])/tout
        # 4 nodal voltages and 3 individual L currents; no Kron reduction.
        A=np.zeros((7,7),complex)
        A[:4,:4]=B_C@np.diag(ys)@B_C.T
        A[0,0]+=ysrc
        A[2,2]+=yload
        A[:4,4:]=B_L
        A[4:,:4]=B_L.T
        A[4:,4:]=-w*1e-9*H
        rhs=np.zeros(7,complex)
        rhs[0]=inj
        sol=np.linalg.solve(A,rhs)
        voltages,currents=sol[:4],sol[4:]
        pout=60*abs(voltages[2]/tout)**2
        il=-10*np.log10(max(200*pout,1e-300))
        worst=max(worst,abs(il-predicted[z]))
        iin=inj-ysrc*voltages[0]
        ie=t1[1,0]*voltages[0]+t1[1,1]*iin
        ve=t1[0,0]*voltages[0]+t1[0,1]*iin
        pref=abs(1-100*ie)**2/200
        plin=np.real(ve*np.conj(ie)-voltages[0]*np.conj(iin))
        plout=np.real(voltages[2]*np.conj(yload*voltages[2]))-pout
        pind=np.real(np.vdot(currents,(w*1e-9*H)@currents))
        pcap=float(np.sum(np.real(ys)*abs(B_C.T@voltages)**2))
        if min(pref,plin,plout,pind,pcap,pout)<-1e-10:negative+=1
        balance=abs(1/200-(pref+plin+plout+pind+pcap+pout))
        power_max=max(power_max,float(balance))
    return {
      "experiment":"EXP-043","variant":cfg,"points":len(ev.f),
      "max_MNA_vs_reduced_Y_IL_delta_db":float(worst),
      "max_absolute_power_balance_error_W":float(power_max),
      "nonpassive_loss_samples":negative,
      "full_L_matrix_positive_definite":True,
      "PASS":bool(worst<1e-8 and power_max<1e-9 and negative==0)
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--checkpoint",type=Path,required=True)
    ap.add_argument("--points",type=int,default=3)
    a=ap.parse_args()
    out=verify(json.loads(a.checkpoint.read_text()),a.points)
    print(json.dumps(out,indent=2),flush=True)
    if not out["PASS"]:raise SystemExit(2)

if __name__=="__main__":main()
