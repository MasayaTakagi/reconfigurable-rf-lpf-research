#!/usr/bin/env python3
"""EXP-043 RF-T005: passband energy-based coupled-inductor Q vs actual IL.

Independent explicit 7x7 branch-current MNA incl fixed S2P/source/load.
Q_L,eff(f)=omega I^H M I / (I^H R I),
M_ij=k_ij sqrt(L_i L_j), R_ii=omega L_i/Q25.

Shows whether strengthening mutual coupling raises *magnetic* Q, lowers
the actual inductor dissipation in milliwatts, and lowers full-network IL.
These are three different questions, with different answers.

The analysis retains the original six IC-C settings: it does not retune C.
"""
import argparse
import json
from pathlib import Path
import numpy as np

import search_3l as engine
from lpf.constraint_versions import load_constraint

BASE=engine.HERE/"checkpoints"
CANDIDATES={
    "zero_gjm_double": {"file":"zero_gjm_double.json","gjm_fixed":[]},
    "gjm_cf0_cp": {"file":"gjm_cf0_cp.json","gjm_fixed":[0,2]},
}
SAMPLES=[("B71",617.,0),("B71",698.,0),("B28",803.,2),
         ("B26",894.,4),("B8",960.,5)]
PORT_SOURCE_RMS_V=1.
PORT_AVS_W=PORT_SOURCE_RMS_V**2/(4*50.)

def analyze_one(ev,x,sample_idx,k):
    row=ev.f
    f,setting=ev.f[sample_idx],ev.setting[sample_idx]
    w=2*np.pi*f*1e6
    y=np.r_[x[3:6],x[8+3*setting:11+3*setting]]
    adm=w*1e-12*y/(1./ev.Q_C-1j)
    t1,t2=ev.pre[sample_idx],ev.post[sample_idx]
    zload=60-40j
    tin=t1[0,1]+50*t1[1,1]
    ys=(t1[0,0]+50*t1[1,0])/tin
    source=PORT_SOURCE_RMS_V/tin
    tout=t2[0,0]*zload+t2[0,1]
    yl=(t2[1,0]*zload+t2[1,1])/tout
    u=x.copy()
    u[6:8]=k
    _,M,H=ev.matrices(u)
    A=np.zeros((7,7),complex)
    A[:4,:4]=ev.BC@np.diag(adm)@ev.BC.T
    A[0,0]+=ys
    A[2,2]+=yl
    A[:4,4:]=engine.BL
    A[4:,:4]=engine.BL.T
    A[4:,4:]=-w*1e-9*H
    b=np.zeros(7,complex); b[0]=source
    ans=np.linalg.solve(A,b)
    V,I=ans[:4],ans[4:]
    menergy=float(np.real(np.vdot(I,M@I)))
    diagenergy=float(np.sum(x[:3]*np.abs(I)**2))
    assert menergy>0 and diagenergy>0
    # H=diag(L/Q25) + j*M, in nH. Q_L,eff includes magnetic
    # interaction but only physical resistive dissipation of chip L.
    qeff=25*menergy/diagenergy
    diagP=float(w*1e-9*diagenergy/25)
    sub0=2*k[0]*np.sqrt(x[0]*x[2])*float(np.real(np.conj(I[0])*I[2]))
    sub1=2*k[1]*np.sqrt(x[1]*x[2])*float(np.real(np.conj(I[1])*I[2]))
    assert abs(menergy-(diagenergy+sub0+sub1))<1e-8*diagenergy
    pout=float(zload.real*np.abs(V[2]/tout)**2)
    i_into=source-ys*V[0]
    ve=t1[0,0]*V[0]+t1[0,1]*i_into
    ie=t1[1,0]*V[0]+t1[1,1]*i_into
    p_ref=float(abs(PORT_SOURCE_RMS_V-100*ie)**2/200)
    p_in=float(np.real(ve*np.conj(ie)-V[0]*np.conj(i_into)))
    p_out=float(np.real(V[2]*np.conj(yl*V[2]))-pout)
    pC=np.real(adm)*np.abs(ev.BC.T@V)**2
    pCfix=float(sum(pC[:3]))
    pCvar=float(sum(pC[3:]))
    power_components={"load":pout,"reflected":p_ref,
                      "input_S2P_loss":p_in,"output_S2P_loss":p_out,
                      "chip_L_loss":diagP,"fixed_C_loss":pCfix,
                      "variable_C_loss":pCvar}
    balance=float(PORT_AVS_W-sum(power_components.values()))
    if abs(balance)>2e-10:raise AssertionError(f"Power mismatch {balance}")
    if min(power_components.values()) < -1e-10:raise AssertionError("negative passive loss")
    return {
        "case":engine.CASES[setting],"f_MHz":float(f),
        "k":list(map(float,k)),"Q_L_eff":float(qeff),
        "L_energy_diagonal_relative":float(diagenergy),
        "L_energy_mutual_relative":{"L0-Ls":sub0/diagenergy,"L1-Ls":sub1/diagenergy},
        "L_currents_mA_RMS":(1000*np.abs(I)).tolist(),
        "coil_R_losses_mW":diagP*1000,
        "full_transducer_IL_db":float(-10*np.log10(pout/PORT_AVS_W)),
        "power_budget_mW":{name:val*1000 for name,val in power_components.items()},
        "power_balance_error_W":balance,
        "min_L_matrix_eigenvalue_nH":float(np.linalg.eigvalsh(M)[0])
    }

def run():
    p=load_constraint("RF-T005",allow_trial=True)
    assert (engine.HERE/"manifest.json").exists()
    allout=[]
    for name,desc in CANDIDATES.items():
        ck=json.loads((BASE/desc["file"]).read_text())
        x=np.asarray(ck["vector"],float)
        ev=engine.Evaluator(p,"zero_gjm_double",2)
        for i in desc["gjm_fixed"]:ev.Q_C[i]=80.
        runs=[]
        saved=x[6:8].copy()
        for klabel,k in [
            ("saved",saved),("zero",[0.,0.]),
            ("both_limit",[.1,-.1])
        ]:
            xk=x.copy();xk[6:8]=k
            direct=ev.il(xk)
            measurements=[]
            for c,f,setting in SAMPLES:
                rows=np.flatnonzero((ev.setting==setting)&np.isclose(ev.f,f))
                if len(rows)==0:raise AssertionError("missing sample "+str((c,f)))
                idx=int(rows[0])
                pt=analyze_one(ev,x,idx,k)
                if abs(pt["full_transducer_IL_db"]-direct[idx])>1e-8:
                    raise AssertionError("ABCD vs independent MNA IL mismatch")
                measurements.append(pt)
                print("PASSBAND",name,klabel,c,f,
                      "Q_L_eff",round(pt["Q_L_eff"],7),
                      "P_L_mW",round(pt["coil_R_losses_mW"],8),
                      "IL_db",round(pt["full_transducer_IL_db"],7),
                      flush=True)
            runs.append({"k_policy":klabel,"samples":measurements})
        allout.append({"candidate":name,"source_checkpoint":str(BASE/desc["file"]),
                       "fixed_GJM_indices":desc["gjm_fixed"],"L_nH":x[:3].tolist(),
                       "physical_adjacent_k":x[6:8].tolist(),
                       "fixed_C_pF":x[3:6].tolist(),"modes":runs})
    return {
        "experiment":"EXP-043","condition":"RF-T005","phase":2,
        "status":"executed_current_7x7_MNA_and_independent_ABCD",
        "objective":"Compare actual passband inductor Q and resistance with IL at unchanged C and L values",
        "model":"3L LQP02HV Q25; lossless mutual; 3 variable Q35; fixed C Q40 or Q80",
        "reference":"50ohm source 1Vrms; load 60-j40ohm; immutable S2P each direction",
        "definition":"Q_L_eff=omega Re(I^H Lmatrix I)/(I^H Rmatrix I), Rii=omega Lii/25",
        "note":"This is total magnetic-inductor Q under network-driven currents, not unloaded eigenmode Q or full LC Q",
        "samples":allout,
        "limitations":["point-frequency comparisons only","other component C and L not reoptimized at changed k",
                       "no Q(f), SRF, EM, tolerance, or physical k realization",
                       "passband Q is not a global minimax RF insertion-loss objective"]
    }
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    result=run()
    target=args.out or engine.ROOT/"results"/"EXP-043"/"passband_effective_q.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("OUTPUT",target,flush=True)
