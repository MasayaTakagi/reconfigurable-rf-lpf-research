#!/usr/bin/env python3
"""Independent full-winding MNA and 0.02MHz passband validation of 1D chip layouts.

Run at repo root:
    python experiments/matching_cost_20261010/verify_adjacent_1d.py
Requires numpy. Phase 2 matching only; not a global optimization or EM proof.
"""
import csv
import json
import math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DB = json.loads((Path(__file__).with_name("adjacent_1d_20261010_shortlist.json")).read_text())
BANDS = DB["six_bands"]
ZLOAD = 60-40j
YL = 1/ZLOAD
RS = 50.
QQ = {"1":15., "2":25., "P":12.}
QC = 80.

def grid(step=.02):
    groups={name:[] for name in BANDS}
    with (ROOT/"data/bands.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"]!="pass":continue
            a,b=float(row["low_mhz"]),float(row["high_mhz"])
            z=max(2,math.ceil((b-a)/step)+1)
            groups[row["case"]].append(np.linspace(a,b,z))
    return {key:np.unique(np.concatenate(value)) for key,value in groups.items()}

def mutual_k(code):
    n=len(code)
    K=np.eye(n)
    for i in range(n):
        for j in range(i+1,n):
            if code[i]==code[j]=="P":
                k=.6
            elif code[i]!="P" and code[j]!="P" and j==i+1:
                k=.4
            else:
                k=0.
            K[i,j]=K[j,i]=k
    return K

def admittance_cap(w,cap_pf):
    return w*cap_pf*1e-12/(1/QC-1j)

def equivalent_il(c, f, case_i):
    code=c["placement_codes"]
    L=np.array(c["coil_inductance_nh"])
    K=mutual_k(code)
    u=np.sqrt(L)
    leff=float(u@K@u)
    rnorm=sum(float(ln)/QQ[t] for ln,t in zip(L,code))
    w=2*np.pi*np.asarray(f)*1e6
    zs=w*1e-9*(rnorm+1j*leff)
    ys=1/zs
    cin,cout=c["C_variable_pf_six_bands"][case_i]
    yin=admittance_cap(w,cin);yout=admittance_cap(w,cout)
    b=YL+yout+ys
    vin=(1/RS)/(1/RS+yin+ys-ys*ys/b)
    vout=ys*vin/b
    return -10*np.log10(4*RS*YL.real*abs(vout)**2)

def full_winding_mna(c,f,case_i):
    """Independent branch-voltage KVL/KCL solve, with energy accounting."""
    code=c["placement_codes"]
    n=len(code)
    L=np.array(c["coil_inductance_nh"])
    K=mutual_k(code)
    assert np.linalg.eigvalsh(K).min()>0
    w=2*np.pi*f*1e6
    Z=1j*w*np.sqrt(L[:,None]*L[None,:])*K*1e-9
    Z+=np.diag(w*L*1e-9/np.array([QQ[t] for t in code]))
    B=np.zeros((n,n+1))
    for j in range(n):
        B[j,j]=1
        B[j,j+1]=-1
    ci,co=c["C_variable_pf_six_bands"][case_i]
    yi,yo=admittance_cap(w,ci),admittance_cap(w,co)
    Y=np.zeros((n+1,n+1),dtype=complex)
    Y[0,0]=1/RS+yi
    Y[-1,-1]=YL+yo
    mat=np.block([[Y,B.T],[B,-Z]])
    rhs=np.zeros(2*n+1,complex)
    rhs[0]=1/RS
    values=np.linalg.solve(mat,rhs)
    v,curr=values[:n+1],values[n+1:]
    load=4*RS*YL.real*abs(v[-1])**2
    reflection=abs(1-2*v[0])**2
    Lheat=4*RS*float(np.sum(w*L*1e-9/np.array([QQ[t] for t in code])*abs(curr)**2))
    Cheat=4*RS*(yi.real*abs(v[0])**2+yo.real*abs(v[-1])**2)
    assert abs(load+reflection+Lheat+Cheat-1)<1e-9
    return -10*np.log10(load)

def main():
    groups=grid()
    maxdiff=0
    for c in DB["shortlist"]:
        code=c["placement_codes"]
        n=len(code)
        L=np.array(c["coil_inductance_nh"])
        assert n and (n<=9)
        assert np.all(L>=.4-1e-9) if "P" not in code else np.all((L>=.1)&(L<=3))
        area=code.count("2")+2*code.count("1")/3
        assert area<=6+1e-9 and code.count("P")<=3
        assert abs(c["chip_area"]-area)<1e-8
        assert len(c["C_variable_pf_six_bands"])==6
        assert all(0<=x<=4 for pair in c["C_variable_pf_six_bands"] for x in pair)
        assert np.linalg.eigvalsh(mutual_k(code)).min()>0
        ilpeak=(-1,None,None)
        for idx,name in enumerate(BANDS):
            f=groups[name]
            iv=equivalent_il(c,f,idx)
            j=int(np.argmax(iv))
            if iv[j]>ilpeak[0]:ilpeak=(float(iv[j]),name,float(f[j]))
            for fm in [float(f[0]),float(f[len(f)//2]),float(f[-1])]:
                independent=full_winding_mna(c,fm,idx)
                equivalent=float(equivalent_il(c,fm,idx))
                maxdiff=max(maxdiff,abs(independent-equivalent))
                assert abs(independent-equivalent)<1e-9
        assert abs(ilpeak[0]-c["IL_max_db_dense"])<3e-5, (code,ilpeak,c["IL_max_db_dense"])
        print("".join(code),f"area={area:.4f}",f"IL={ilpeak[0]:.7f}dB",ilpeak[1],f"{ilpeak[2]:.2f}MHz","PASS")
    print(f"8/8 candidates: 0.02MHz grid, PSD, power conservation, MNA verified; max discrepancy {maxdiff:.3g}dB.")
    print("Not proof of continuous-frequency or global optimum; EM/SRF/actual-Q unverified.")

if __name__=="__main__":
    main()
