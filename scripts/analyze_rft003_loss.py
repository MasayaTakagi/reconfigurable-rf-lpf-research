#!/usr/bin/env python3
"""Phase-2 RF-T003 loss decomposition and series-aware EXP-015/3C comparison.

Power is RMS steady-state and referred to a 1 Vrms Thevenin source, Rs=50ohm:
Pavs=0.005 W. Reflected power is NOT component heat dissipation.
Actual L/C branch dissipations are separated using augmented-current MNA.
Frequency screening uses vectorized independent nodal assembly (finite grids,
NOT continuous interval proofs). No optimizer or physical SRF/Q(f)/EM model.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from lpf.circuit import Branch, solve, incidence
from lpf.independent import solve_gain
from lpf.evaluate import CASES, load_bands

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/validation/rft003_20261012/target30_results.json"
EXP15 = ROOT / "experiments/chatgpt_topology_search/runs/EXP-015"

def candidates():
    base=json.loads(BASE.read_text(encoding="utf-8"))["best"]
    result={}
    result["RF-T003_2C_HV"]={
       "L_edges":[z["nodes"] for z in base["inductors"]],
       "L_nH":[z["L_nH"] for z in base["inductors"]],
       "L_Q":[z["Q"] for z in base["inductors"]],
       "row":base["chip_index_order"],
       "k":base["chip_adjacent_k"],
       "fixed":[(z["edge"],z["C_pf"],z["Q"]) for z in base["fixed_capacitors"]],
       "variable_edges":[z["edge"] for z in base["variable_capacitors"]],
       "Cv":base["variable_C_pf_by_setting"],
       "constraint_id":"RF-T003",
    }
    for t in ("HQ3C","HV3C"):
        a=json.loads((EXP15/("EXP015-"+t+"-01.json")).read_text(encoding="utf-8"))
        result["EXP015_3C_"+t[:2]]={
           "L_edges":[[1,2],[3,4],[2,5],[2,3]],
           "L_nH":a["L_nH"],"L_Q":a["Q_L"],
           "row":a["physical_row"],"k":a["signed_neighbor_k"],
           "fixed":[(e,v,80) for e,v in zip(a["fixed_C_edges"],a["fixed_C_pf"])],
           "variable_edges":a["variable_C_edges"],"Cv":a["Cv_by_setting_pF"],
           "constraint_id":"historical_study_EX015_not_relabelled_RF-T002",
        }
    return result

def network(c,case):
    coils=tuple(Branch(*e, float(v)*1e-9,float(q))
        for e,v,q in zip(c["L_edges"],c["L_nH"],c["L_Q"]))
    caps=tuple(Branch(*e, float(v)*1e-12,float(q))
        for e,v,q in c["fixed"])
    caps+=tuple(Branch(*e, float(v)*1e-12,80.)
        for e,v in zip(c["variable_edges"],c["Cv"][case]))
    K=np.eye(4)
    for j,k in enumerate(c["k"]):
        a,b=c["row"][j:j+2]
        assert abs(k)<=.4+1e-8
        K[a,b]=K[b,a]=float(k)
    assert np.linalg.eigvalsh(K).min()>0
    return dict(n_nodes=5,source_node=1,load_node=3,
        inductors=coils,capacitors=caps,coupling=K,
        source_voltage=1.,source_ohms=50.,load_ohms=60-40j)

def worst_pass_frequency(pars,case,samples,bands):
    L=pars["inductors"]
    C=pars["capacitors"]
    B=incidence(L,5)
    K=pars["coupling"]
    values=np.array([b.value for b in L])
    q=np.array([b.q for b in L])
    M=K*np.sqrt(np.outer(values,values))
    Zi=np.linalg.inv(np.diag(values/q)+1j*M)
    coil=B@Zi@B.T
    ycap=np.zeros((5,5),complex)
    for cap in C:
        if cap.value:
            t=incidence([cap],5)[:,0]
            ycap+=np.outer(t,t)*cap.value/(1/cap.q-1j)
    port=np.zeros((5,5),complex)
    port[0,0]=1/50
    port[2,2]=1/(60-40j)
    source=np.array([1/50,0,0,0,0],complex)
    f=[]
    for b in bands:
        if b["case"]==case and b["region"] in ("UL","DL"):
            f.extend(np.linspace(float(b["low_mhz"]),float(b["high_mhz"]),samples))
    f=np.array(f)
    w=f*2*np.pi*1e6
    y=port[None,:,:]+coil[None,:,:]/w[:,None,None]+w[:,None,None]*ycap[None,:,:]
    v=np.linalg.solve(y,np.broadcast_to(source,(len(f),5))[...,None])[...,0]
    gain=abs(v[:,2])**2*(1/(60-40j)).real/.005
    il=-10*np.log10(np.maximum(gain,1e-300))
    at=int(np.argmax(il))
    return float(f[at]),float(il[at])

def breakdown(pars,f_mhz):
    f=f_mhz*1e6
    x=solve(f,**pars)
    w=2*np.pi*f
    pl=[float(abs(i)**2*w*z.value/z.q) for i,z in zip(x["inductor_current"],pars["inductors"])]
    pc=[float(abs(i)**2/(w*z.value*z.q)) if z.value else 0.
        for i,z in zip(x["capacitor_current"],pars["capacitors"])]
    pav=float(x["p_available"])
    heat=sum(pl)+sum(pc)
    assert abs(sum(pl)-x["p_inductor"])<1e-13
    assert abs(sum(pc)-x["p_capacitor"])<1e-13
    assert abs(pav-x["p_load"]-x["p_reflected"]-heat)<1e-12
    independent=solve_gain(f,**pars)
    mna_error=abs(x["il_db"]+10*np.log10(independent))
    assert mna_error<1e-8
    return {
       "f_MHz":f_mhz,"IL_dB":float(x["il_db"]),
       "P_avail_mW":pav*1000,"P_load_mW":float(x["p_load"]*1000),
       "P_reflected_mW":float(x["p_reflected"]*1000),
       "P_inductor_mW":[a*1000 for a in pl],
       "P_capacitor_mW":[a*1000 for a in pc],
       "P_inductor_total_mW":sum(pl)*1000,
       "P_capacitor_total_mW":sum(pc)*1000,
       "P_heat_total_mW":heat*1000,
       "inductor_current_mA":[float(abs(i)*1000) for i in x["inductor_current"]],
       "max_MNA_delta_dB":float(mna_error),
       "power_balance_residual_W":float(x["power_residual"]),
       "finite_grid_only":True,
    }

def run(points=101):
    assert points>=2
    bands=load_bands()
    result={"description":"Phase 2 frozen-circuit per-element power loss, constant-Q, noncausal comparison",
            "points_per_pass_segment":points,"candidate_source_main":"709cb85872236237120ab23c3402f33bba895267",
            "power_reference":"one volt RMS, Pavs = 5 milliwatts","circuits":{}}
    for name,c in candidates().items():
        cases={}
        for case in CASES:
            par=network(c,case)
            freq,il=worst_pass_frequency(par,case,points,bands)
            b=breakdown(par,freq)
            assert abs(b["IL_dB"]-il)<1e-8
            cases[case]=b
        result["circuits"][name]={
           "constraint_id":c["constraint_id"],"by_case":cases,
           "worst_IL_db":max(v["IL_dB"] for v in cases.values()),
           "L_edges":c["L_edges"],"C_edges":[e for e,_,_ in c["fixed"]]+c["variable_edges"]}
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--points",type=int,default=101)
    p.add_argument("--output",default="")
    a=p.parse_args()
    res=run(a.points)
    out=json.dumps(res,ensure_ascii=False,indent=2)+"\n"
    if a.output:
        Path(a.output).write_text(out,encoding="utf-8")
    else:
        print(out)
