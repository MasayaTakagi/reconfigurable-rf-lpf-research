#!/usr/bin/env python3
"""EXP-043 power-budget contrast, independent branch-current 7x7 MNA.

At B28 DL high-edge 803MHz and B8 DL high-edge 960MHz, decompose total
Pavs=0.005W into reflected, mandatory fixed input/output S2P dissipation,
chip inductors, fixed GJM/PCB C, variable C, and delivered load power.
The external S2P are models, NOT measurements; ideal 1V RMS source is used.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import search_3l as engine
from lpf.constraint_versions import load_constraint

FILELIST=[
    ("baseline","zero_gjm_double.json",()),
    ("gjm_cp","gjm_cp.json",(2,)),
    ("gjm_cf0_cp","gjm_cf0_cp.json",(0,2)),
]
def read_candidate(name):
    policy=load_constraint("RF-T005",allow_trial=True)
    filename,gjm=[(f,g) for n,f,g in FILELIST if n==name][0]
    content=json.loads((engine.HERE/"checkpoints"/filename).read_text())
    x=np.asarray(content["vector"],float)
    assert len(x)==26
    e=engine.Evaluator(policy,"zero_gjm_double",2)
    for i in gjm:e.Q_C[i]=80.
    return e,x

def analyze(case,f,si,e,x):
    w=2e6*np.pi*f
    caps=np.r_[x[3:6],x[8+3*si:11+3*si]]
    y=w*1e-12*caps/(1/e.Q_C-1j)
    # get two-port S2P at this specific frequency from cache (avoid band grid)
    from lpf.port_parasitics import get_two_port_s,s_to_abcd
    from lpf.constraint_versions import load_constraint
    p=load_constraint("RF-T005",allow_trial=True)
    t1=s_to_abcd(get_two_port_s(p,"input_parasitic",f*1e6,root=engine.ROOT))
    t2=s_to_abcd(get_two_port_s(p,"output_parasitic",f*1e6,root=engine.ROOT))
    zs=50.;zload=60-40j
    denin=t1[0,1]+zs*t1[1,1]
    ys=(t1[0,0]+zs*t1[1,0])/denin
    src=1/denin
    denout=t2[0,0]*zload+t2[0,1]
    yl=(t2[1,0]*zload+t2[1,1])/denout
    _,M,H=e.matrices(x)
    K=np.zeros((7,7),complex)
    K[:4,:4]=e.BC@np.diag(y)@e.BC.T
    K[0,0]+=ys
    K[2,2]+=yl
    K[:4,4:]=engine.BL
    K[4:,:4]=engine.BL.T
    K[4:,4:]=-w*1e-9*H
    rhs=np.zeros(7,complex)
    rhs[0]=src
    sol=np.linalg.solve(K,rhs)
    v,i=sol[:4],sol[4:]
    PL=60*abs(v[2]/denout)**2
    iin=src-ys*v[0]
    ve=t1[0,0]*v[0]+t1[0,1]*iin
    ie=t1[1,0]*v[0]+t1[1,1]*iin
    P_ref=abs(1-100*ie)**2/200
    P_in=float(np.real(ve*np.conj(ie)-v[0]*np.conj(iin)))
    P_out=float(np.real(v[2]*np.conj(yl*v[2]))-PL)
    P_ind=float(np.real(np.vdot(i,w*1e-9*H@i)))
    c_loss=np.real(y)*abs(e.BC.T@v)**2
    P_fix=float(np.sum(c_loss[:3]))
    P_var=float(np.sum(c_loss[3:]))
    parts={"delivered_load":float(PL),"reflected":float(P_ref),
           "input_s2p_dissipation":P_in,"output_s2p_dissipation":P_out,
           "chip_inductor_dissipation":P_ind,
           "fixed_C_dissipation":P_fix,"variable_C_dissipation":P_var}
    res=0.005-sum(parts.values())
    assert abs(res)<2e-10
    assert min(parts.values())>=-1e-10
    return {"band":case,"MHz":f,"IL_db":float(-10*np.log10(PL/.005)),
            "power_components_mW":{name:1000*p for name,p in parts.items()},
            "Pavs_mW":5.,
            "percent_of_Pavs":{name:100*p/.005 for name,p in parts.items()},
            "power_balance_residual_W":float(res),
            "L_branch_currents_mA_RMS":(1000*abs(i)).tolist(),
            "C_branch_voltage_RMS_V":abs(e.BC.T@v).tolist(),
            "S2P_valid":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    records=[]
    for name in ("baseline","gjm_cp","gjm_cf0_cp"):
        e,x=read_candidate(name)
        rec={"candidate":name,"L_nH":x[:3].tolist(),
             "coupling":x[6:8].tolist(),
             "fixed_C_pF":x[3:6].tolist(),
             "fixed_C_Q":e.Q_C[:3].tolist(),
             "points":[analyze("B28",803.,2,e,x),analyze("B8",960.,5,e,x)]}
        records.append(rec)
        for point in rec["points"]:
            print("POWER",name,point["band"],point["MHz"],
                  point["IL_db"],json.dumps(point["percent_of_Pavs"]),flush=True)
    output={
        "experiment":"EXP-043","phase":2,"condition":"RF-T005",
        "source":"verified GJM and PCB topologies from EXP-043 checkpoints",
        "external_port":"source 50ohm, load 60-j40ohm, fixed P1/P2 S2P",
        "source_V_rms":1.,"source_Pavs_mW":5.,
        "independent_analysis":"explicit 7x7 branch-current MNA, no LPF reduced 2-port",
        "states":records,
        "caveats":["Pavs budgets are source-referred and sum to 100%, not a dB additive decomposition",
                   "The GJM substitution modifies topology values as well as capacitor Q",
                   "This is a point-frequency budget, NOT Q(f) or bandmax proof",
                   "LQP02HV is assumed Q25 at all frequencies; real part SRF/EM unverified"]}
    target=a.out or engine.ROOT/"results"/"EXP-043"/"loss_budget.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    print("OUTPUT",target,flush=True)

if __name__=="__main__":
    main()
