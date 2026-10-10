#!/usr/bin/env python3
"""Reoptimize eight matching-only 1D-adjacent L groups, including unequal L values.

Requirements: numpy, scipy. Source 50ohm, frequency-constant load 60-40j.
Nominal nonstrong chip k=0; selected physical neighbors k=+0.4.
PCB-to-PCB k=+0.6, chip-to-PCB k=0. Two variable grounded IC caps,
0..4pF independently per six configurations; NO harmonic constraints.
Numerical SLSQP/L-BFGS-B candidates only; not global/certified minima.

  OPENBLAS_NUM_THREADS=1 python experiments/matching_cost_20261010/optimize_adjacent_1d.py
"""
import csv
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

ROOT=Path(__file__).resolve().parents[2]
NAMES=["B71","B12","B28","B13+B14","B26","B8"]
Q={"1":15.,"2":25.,"P":12.}
QC=80.
RS=50.
YL=1/(60-40j)

def bands(step=1.0):
    per={k:[] for k in NAMES}
    with (ROOT/"data/bands.csv").open() as f:
        for row in csv.DictReader(f):
            if row["type"]!="pass":continue
            a,b=float(row["low_mhz"]),float(row["high_mhz"])
            n=max(2,math.ceil((b-a)/step)+1)
            per[row["case"]].append(np.linspace(a,b,n))
    f=np.concatenate([np.unique(np.concatenate(per[key])) for key in NAMES])
    i=np.concatenate([np.repeat(ix,len(np.unique(np.concatenate(per[k]))))
                      for ix,k in enumerate(NAMES)]).astype(int)
    return 2*np.pi*f*1e6,i,f

def Kmatrix(code):
    K=np.eye(len(code))
    for a in range(len(code)):
        for b in range(a+1,len(code)):
            if code[a]==code[b]=="P": k=.6
            elif code[a]!="P" and code[b]!="P" and b==a+1:k=.4
            else:k=0.
            K[a,b]=K[b,a]=k
    assert np.linalg.eigvalsh(K).min()>0
    return K

def L_equivalent(code,K,L):
    L=np.asarray(L)
    effective=float(np.sqrt(L)@K@np.sqrt(L))
    serial_resistive_L=float(sum(v/Q[t] for t,v in zip(code,L)))
    return effective,effective/serial_resistive_L

def il(x,q,w,idx):
    # x[0]: effective series inductance nH; x[1:13]: IC shunt C, 6x2 pF
    L=x[0]
    c=np.reshape(x[1:13],(6,2))
    ys=1/(w*L*1e-9*(1/q+1j))
    yi=w*c[idx,0]*1e-12/(1/QC-1j)
    yo=w*c[idx,1]*1e-12/(1/QC-1j)
    den=YL+yo+ys
    v0=(1/RS)/(1/RS+yi+ys-ys*ys/den)
    v1=ys*v0/den
    return -10*np.log10(4*RS*YL.real*abs(v1)**2)

def tune_matching(q):
    wc,ic,_=bands(3.0)
    wd,id,fd=bands(.02)
    bounds=[(.4,27)]+[(0,4)]*12
    solutions=[]
    for l0 in (6.5,8.0,10.0):
        z=np.r_[l0,np.tile([.07,.3],6)]
        for beta in (40,160,500):
            fun=lambda x:float(logsumexp(beta*il(x,q,wc,ic))/beta)
            res=minimize(fun,z,bounds=bounds,method="L-BFGS-B",
                         options={"maxiter":170,"ftol":1e-12})
            z=res.x
        solutions.append((float(il(z,q,wd,id).max()),z))
    return min(solutions,key=lambda pair:pair[0])[1]

def allocate_L(code,K,target_leff):
    n=len(code)
    q=np.array([Q[t] for t in code])
    lo=np.array([.1 if t=="P" else .4 for t in code])
    hi=np.array([3 if t=="P" else 27 for t in code])
    def le(L):return float(np.sqrt(L)@K@np.sqrt(L))
    values,vectors=np.linalg.eigh(np.sqrt(q[:,None]*q[None,:])*K)
    seed=np.sqrt(q)*np.abs(vectors[:,-1])
    seed=np.maximum(seed*seed,1e-12)
    seeds=[seed,np.ones(n),lo]
    successes=[]
    for s in seeds:
        s=np.maximum(s,lo)
        s=np.clip(s*target_leff/le(s),lo,hi)
        r=minimize(lambda x:float(np.sum(x/q)),s,method="SLSQP",
                   bounds=list(zip(lo,hi)),
                   constraints=[{"type":"eq","fun":lambda x:le(x)-target_leff}],
                   options={"maxiter":200,"ftol":1e-12})
        if abs(le(r.x)-target_leff)<1e-5:
            successes.append((float(np.sum(r.x/q)),r.x))
    if not successes:return None
    return min(successes,key=lambda p:p[0])[1]

def solve(code):
    K=Kmatrix(code)
    target=8.
    data=None
    for _ in range(4):
        L=allocate_L(code,K,target)
        if L is None:raise ValueError("no bounded L for this target")
        le,q=L_equivalent(code,K,L)
        match=tune_matching(q)
        target=float(match[0])
        if abs(target-le)<2e-5:break
    L=allocate_L(code,K,target)
    le,q=L_equivalent(code,K,L)
    match=tune_matching(q)
    # Leff changes slightly when bounded-coil Q is updated; retune capacitor codes
    # while leaving L fixed, with nominal 1 MHz band grid, if needed.
    w,idx,_=bands(.02)
    tuned=np.r_[le,match[1:]]
    IL=float(il(tuned,q,w,idx).max())
    return dict(code=code,area=code.count("2")+code.count("1")*2/3,
                L_nH=L.tolist(),Leff_nH=le,Qeff=q,IL_max_db=IL,
                cap_pf_by_band=np.reshape(tuned[1:],(6,2)).tolist(),
                positive_definite_K_min=float(np.linalg.eigvalsh(K).min()))

def main():
    codes=["PPP","12","22","122","222","2222","22222","222222"]
    for c in codes:
        ans=solve(c)
        print(json.dumps(ans,ensure_ascii=False))

if __name__=="__main__":
    main()
