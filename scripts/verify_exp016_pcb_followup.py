#!/usr/bin/env python3
"""Independent EXP-016 PCB-C checkpoint recomputation (Phase 2 / RF-F001).

Read the saved candidate values; run the repository's current-augmented MNA,
and cross-check with separately stamped nodal admittance.  This script does
not optimize, prove globality, or validate physical PCB/SRF feasibility.
Run from repo root: PYTHONPATH=src python scripts/verify_exp016_pcb_followup.py
Optional exhaustive finite grid: --samples 7001.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from lpf.circuit import Branch, solve
from lpf.evaluate import CASES, load_bands
from lpf.validate import validate_couplings

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "validation" / "exp016_20261012" / "pcb_followup_shortlist.json"

def circuit(common, candidate, case):
    labels = common["inductor_edges"]
    ind = tuple(Branch(a,b,float(v)*1e-9,25.) for (a,b),v
                in zip(labels,candidate["L_nH"]))
    fixed_parts = common["fixed_capacitor_parts"]
    cap = [Branch(*z["edge"],float(v)*1e-12,float(z["Q"]))
           for z,v in zip(fixed_parts,candidate["fixed_C_pf"])]
    cap += [Branch(*edge,float(v)*1e-12,80.)
            for edge,v in zip(common["variable_capacitor_edges"],
                             candidate["variable_C_pf_by_setting"][case])]
    row=common["chip_row"]
    K=np.eye(len(ind))
    for (a,b),k in zip(zip(row,row[1:]),candidate["adjacent_signed_k"]):
        K[a,b]=K[b,a]=float(k)
    errs=validate_couplings(K,["chip"]*len(ind),row,
                             list(zip(row,row[1:])),nominal=True)
    if errs:raise ValueError(str(errs))
    assert all(.4<=float(v)<=27 for v in candidate["L_nH"])
    assert all(0<=float(v)<=4 for v in candidate["variable_C_pf_by_setting"][case])
    assert sum(z["kind"]=="PCB_PATTERN_C" for z in fixed_parts)<=3
    for z,v in zip(fixed_parts,candidate["fixed_C_pf"]):
        if z["kind"]=="PCB_PATTERN_C":assert .02-1e-10<=v<=.2+1e-10
    return dict(n_nodes=5,source_node=1,load_node=3,
                inductors=ind,capacitors=tuple(cap),coupling=K,
                source_voltage=1.,source_ohms=50.,load_ohms=60-40j)

def nodal_gain(frequency_hz, pars):
    # Independently stamp incidence vectors rather than calling
    # lpf.circuit.incidence or its solve method.
    w=2*np.pi*frequency_hz
    n=pars["n_nodes"]
    inductors=pars["inductors"]
    caps=pars["capacitors"]
    values=np.array([z.value for z in inductors],float)
    K=pars["coupling"]
    M=K*np.sqrt(np.outer(values,values))
    assert np.linalg.eigvalsh(M).min()>0
    y=np.zeros((n,n),complex)
    y[0,0]+=1/50
    y[2,2]+=1/(60-40j)
    B=np.zeros((n,len(inductors)),float)
    for i,z in enumerate(inductors):
        if z.a:B[z.a-1,i]+=1
        if z.b:B[z.b-1,i]-=1
    Z=np.diag(w*values/25)+1j*w*M
    y+=B@np.linalg.solve(Z,B.T)
    for z in caps:
        if z.value==0:continue
        v=np.zeros(n)
        if z.a:v[z.a-1]+=1
        if z.b:v[z.b-1]-=1
        y+=np.outer(v,v)*w*z.value/(1/z.q-1j)
    rhs=np.zeros(n,complex)
    rhs[0]=1/50
    out=np.linalg.solve(y,rhs)[2]
    load_power=abs(out)**2*(1/(60-40j)).real
    return float(load_power/(1/(4*50)))

def verify(samples):
    saved=json.loads(DATA.read_text(encoding="utf-8"))
    common=saved["constraints"]
    bands=load_bands()
    print("check:",saved["experiment_id"],common["id"],"segments",len(bands))
    for candidate in saved["candidates"]:
        results={}
        mna_max=0.;balance_max=0.
        for case in CASES:
            pars=circuit(common,candidate,case)
            reg={"UL":[],"DL":[],"H2":[],"H3":[]}
            for segment in bands:
                if segment["case"]!=case:continue
                fs=np.linspace(float(segment["low_mhz"]),float(segment["high_mhz"]),samples)
                for f in fs:
                    v=solve(float(f)*1e6,**pars)
                    reg[segment["region"]].append(v["il_db"])
                for f in (fs[0],fs[len(fs)//2],fs[-1]):
                    v=solve(float(f)*1e6,**pars)
                    gain=nodal_gain(float(f)*1e6,pars)
                    mna_max=max(mna_max,abs(v["il_db"]+10*np.log10(gain)))
                    balance_max=max(balance_max,abs(v["power_residual"]))
            results[case]=[max(reg["UL"]+reg["DL"]),min(reg["H2"]),min(reg["H3"])]
        il=max(v[0] for v in results.values())
        h2=min(v[1] for v in results.values())
        h3=min(v[2] for v in results.values())
        assert mna_max<1e-8,(candidate["candidate_id"],mna_max)
        assert balance_max<1e-12,(candidate["candidate_id"],balance_max)
        assert h2>=35-1e-5 and h3>=35-1e-5
        # Stored dense metrics are a separate 7001-point benchmark.
        if samples==7001:
            old=candidate["dense_7001_per_interval"]
            assert abs(il-old["worst_IL_db"])<1e-7,(il,old)
            assert abs(h2-old["min_H2_db"])<1e-7
            assert abs(h3-old["min_H3_db"])<1e-7
        print(json.dumps(dict(candidate_id=candidate["candidate_id"],
           samples_per_segment=samples,IL_db=il,H2_db=h2,H3_db=h3,
           max_independent_MNA_error_db=mna_max,
           max_power_balance_error_W=balance_max),ensure_ascii=False))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--samples",type=int,default=51)
    args=p.parse_args()
    if args.samples<3:raise SystemExit("--samples must be >=3")
    verify(args.samples)
