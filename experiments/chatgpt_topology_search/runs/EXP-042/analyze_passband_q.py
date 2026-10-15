#!/usr/bin/env python3
"""EXP-042 RF-T005 4L driven-band coupled magnetic Q vs actual resistor loss.

The RF-T005 4L pcb_cf1 circuit uses:
L0=(0,1), L1=(1,3), L2=(1,4), L3=(1,2);
physical chip row L0-L1-L3-L2, mutual k indices 0-1,1-3,3-2;
7 C branches Cf0,Cf1,Cf2,Cp,Cv0,Cv1,Cv2.
Computes passband Q=ω I^H Lmat I/(I^H R I) and 9x9 power flow
under actual frozen input/output S2P, source 50ohm, load 60-j40ohm.
Whole-band H2/H3 check uses independent 4L reduced-Y/ABCD evaluator;
the primary Q/IL point-frequency budget uses separate branch-current MNA.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import optimize as base
from optimize import BL,BC,L_ORDER,CASES,Evaluator,policy_and_seed

HERE=Path(__file__).resolve().parent
INPUT=HERE/"checkpoints"/"pcb_cf1.json"
VARIANTS={
    "saved_optimum":lambda s:s,
    "k_L1L3_to_positive_max":lambda s:np.array([s[0],.1,s[2]]),
    "k_L1L3_zero":lambda s:np.array([s[0],0.,s[2]]),
    "k_L1L3_negative_max":lambda s:np.array([s[0],-.1,s[2]]),
    "all_mutual_zero":lambda s:np.zeros(3),
}
PROBES=[("B71",698.),("B28",803.),("B26",894.),("B8",960.)]
P_AVS=1/(4*50.) # 1Vrms source and 50ohm internal R

def circuit_at(ev,idx,x):
    f=ev.f[idx]
    si=ev.setting[idx]
    w=2*np.pi*f*1e6
    L=x[:4]
    M=np.diag(L.copy())
    for n,k in enumerate(x[8:11]):
        a,b=L_ORDER[n:n+2]
        M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
    assert np.linalg.eigvalsh(M)[0]>0.
    H=np.diag(L/25.)+1j*M
    c=np.r_[x[4:8],x[11+3*si:14+3*si]]
    y=w*1e-12*c/(1/base.Q_C-1j)
    ain,aout=ev.pre[idx],ev.post[idx]
    srcz=50.;loadz=60-40j
    denom_in=ain[0,1]+srcz*ain[1,1]
    ysrc=(ain[0,0]+srcz*ain[1,0])/denom_in
    injection=1/denom_in
    denom_out=aout[0,0]*loadz+aout[0,1]
    yout=(aout[1,0]*loadz+aout[1,1])/denom_out
    A=np.zeros((9,9),complex)
    A[:5,:5]=BC@np.diag(y)@BC.T
    A[0,0]+=ysrc
    A[2,2]+=yout
    A[:5,5:]=BL
    A[5:,:5]=BL.T
    A[5:,5:]=-w*1e-9*H
    rhs=np.zeros(9,complex);rhs[0]=injection
    vi=np.linalg.solve(A,rhs)
    voltage,I=vi[:5],vi[5:]
    Pload=float(60*abs(voltage[2]/denom_out)**2)
    IL=-10*np.log10(Pload/P_AVS)
    d=float(np.sum(L*np.abs(I)**2))
    t=float(np.real(np.vdot(I,M@I)))
    qm=25*t/d
    mutual_terms={}
    for n,k in enumerate(x[8:11]):
        j,l=L_ORDER[n:n+2]
        mutual_terms[f"L{j}_L{l}"]=float(
            2*M[j,l]*np.real(np.conj(I[j])*I[l])/d)
    Pcoil=float(w*1e-9*d/25)
    Iin=injection-ysrc*voltage[0]
    Vin_ext=ain[0,0]*voltage[0]+ain[0,1]*Iin
    I_ext=ain[1,0]*voltage[0]+ain[1,1]*Iin
    Pref=float(abs(1-100*I_ext)**2/200)
    Pin=float(np.real(Vin_ext*np.conj(I_ext)-voltage[0]*np.conj(Iin)))
    Pout=float(np.real(voltage[2]*np.conj(yout*voltage[2]))-Pload)
    c_loss=y.real*abs(BC.T@voltage)**2
    Pfix=float(np.sum(c_loss[:4]))
    Pvar=float(np.sum(c_loss[4:]))
    parts={"load":Pload,"reflected":Pref,"input_S2P":Pin,
           "output_S2P":Pout,"chip_L":Pcoil,
           "fixed_C":Pfix,"variable_C":Pvar}
    residual=P_AVS-sum(parts.values())
    assert abs(residual)<1e-10,(f,residual)
    assert min(parts.values())>-1e-10
    return {"setting":CASES[si],"MHz":float(f),"Q_L_eff":float(qm),
            "k":x[8:11].tolist(),
            "magnetic_mutual_energy_over_self":mutual_terms,
            "chip_L_R_loss_mW":1000*Pcoil,"IL_db":float(IL),
            "power_mW":{name:1000*v for name,v in parts.items()},
            "L_branch_currents_RMS_mA":(1000*abs(I)).tolist(),
            "power_residual_W":float(residual)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--grid",type=int,default=1001)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    p,_=policy_and_seed()
    checkpoint=json.loads(INPUT.read_text(encoding="utf-8"))
    x=np.array(checkpoint["vector"],float)
    assert len(x)==29
    assert checkpoint["experiment_id"]=="EXP-042"
    assert checkpoint["candidate_id"]=="EXP042-pcb_cf1"
    assert checkpoint["CF_Q_by_fixed_index"]==[80,40,80,40]
    base.Q_C[1]=40. # PCB fixed Cf1; others GJM Cf0/Cf2 and PCB Cp
    ev=Evaluator(p,a.grid)
    reports=[]
    for label,fk in VARIANTS.items():
        v=x.copy();v[8:11]=fk(x[8:11].copy())
        sum0=ev.summary(v)
        all_il=ev.il(v)
        points=[]
        for band,f in PROBES:
            ii=np.flatnonzero((ev.setting==CASES.index(band))&
                              np.isclose(ev.f,f,atol=1e-8)&(ev.role==0))
            assert len(ii)>0,(band,f)
            idx=int(ii[0])
            z=circuit_at(ev,idx,v)
            assert abs(z["IL_db"]-all_il[idx])<1e-8,(
                 "MNA/ABCD disagree",label,band,f,z["IL_db"],all_il[idx])
            points.append(z)
            print("POINT",label,band,f,
                  "Q",z["Q_L_eff"],"chip_R_mW",z["chip_L_R_loss_mW"],
                  "IL_dB",z["IL_db"],flush=True)
        row={"label":label,"k":v[8:11].tolist(),
             "full_band_1001pt_per_segment":sum0,
             "passes_30dB":bool(sum0["min_h2_db"]>=30 and
                                sum0["min_h3_db"]>=30),
             "points":points}
        reports.append(row)
        print("FINAL",label,"worstIL",sum0["worst_il_db"],
              "H2",sum0["min_h2_db"],"H3",sum0["min_h3_db"],
              "pass30",row["passes_30dB"],flush=True)
    result={"experiment":"EXP-042","phase":"Phase 2",
            "constraint":"RF-T005 trial of formal RF-F003",
            "variant":"pcb_cf1","chip_area":16/3,
            "inductor_Q25":True,"fixed_C_Q":[80,40,80,40],
            "IC_Q":35,
            "fixed_C_and_L_unchanged_across_k_trials":True,
            "definition":"omega Re(I^H Lmatrix I)/(I^H R I), Rii=omega Li/25",
            "grid_points_per_csv_segment":a.grid,
            "csv_segments":28,"independent_MNA":"9x9 explicit branch-current solution at four passband points per k test; separate full-band ABCD evaluation",
            "source_checkpoint":"checkpoints/pcb_cf1.json",
            "source_sha256_rule":"fixed external S2P SHA verified by policy and get_two_port_s",
            "results":reports,
            "limitations":["k perturbation other component values not retuned",
                           "local full-band finite-grid not global continuous proof",
                           "Q(f), SRF, manufacturing, physical simultaneous k not verified",
                           "magnetic stored-energy Q is not a monotone predictor of LPF IL"]}
    path=a.out or base.ROOT/"results"/"EXP-042"/"driven_passband_magnetic_q.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("OUTPUT",path,flush=True)
if __name__=="__main__":main()
