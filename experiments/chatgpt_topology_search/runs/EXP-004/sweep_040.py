#!/usr/bin/env python3
"""Phase2, full-LPF cost<=7: sharded, finite-grid, vectorized topology search.

All optimization results are local-search observations, never global bounds.
The base owner-approved cost hard cap=6 remains unchanged (area7 is experimental).
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
REF=ROOT/"experiments/chatgpt_topology_search/runs/EXP-002/A7-01.json"
BANDS=ROOT/"data/bands.csv"
POLICY=ROOT/"data/design_constraints.json"
CASES=("B71","B12","B28","B13+B14","B26","B8")
BASE_L=((0,1),(2,3),(1,4),(1,2))
BASE_C=((1,2),(0,2),(4,-1))
ORDER=(1,2,3,0)
EDGE_SET=((0,1),(1,2),(0,2),(0,-1),(1,-1),(2,-1),(3,-1),
          (4,-1),(3,4),(0,3),(0,4),(1,3),(1,4),(2,3),(2,4))


def grids(points):
    data=list(csv.DictReader(BANDS.open(encoding="utf-8",newline="")))
    out=[]
    for case in CASES:
        groups=[]
        for region in (("UL","DL"),("H2",),("H3",)):
            f=np.concatenate([np.linspace(float(z["low_mhz"]),float(z["high_mhz"]),points)
                for z in data if z["case"]==case and z["region"] in region])
            groups.append(f*2*np.pi*1e6)
        out.append(groups)
    return out


def jobs():
    result=[]
    def add(kind,L,C,order):
        result.append({"id":len(result),"family":kind,"Ledges":list(L),
                       "Cedges":list(C),"order":list(order),"Lcount":len(L)})
    # Three independent series L resonators, one grounding shunt L.
    series=((0,1),(1,4),(4,2),(4,3))
    series_c=((0,1),(1,4),(4,2))
    for extra in ((0,2),(0,4),(1,2),(1,3),(1,-1),(2,-1),(4,-1),
                  (3,-1),(0,-1),(2,3),(0,3)):
        for row in ((0,1,3,2),(2,1,3,0),(0,3,1,2),(3,1,2,0)):
            add("three_series_two_ground_controls",series,series_c+(extra,),row)
    topologies=(
        ((0,1),(2,3),(1,4),(1,2)),
        ((0,1),(2,3),(1,4),(0,2)),
        ((0,1),(2,3),(2,4),(1,2)),
        ((0,1),(1,3),(2,4),(1,2)),
        ((0,1),(1,3),(1,4),(1,2)),
        ((0,1),(2,3),(0,4),(1,2)),
    )
    capacitances=(
        ((1,2),(0,2),(4,-1),(0,1)),
        ((1,2),(0,2),(4,-1),(2,3)),
        ((1,2),(0,2),(4,-1),(1,3)),
        ((1,2),(0,2),(4,-1),(1,-1)),
        ((1,2),(0,2),(4,-1),(2,-1)),
        ((1,2),(0,2),(3,-1),(0,1)),
    )
    for L in topologies:
        for C in capacitances:
            for row in ((1,2,3,0),(1,3,2,0)):
                add("two_series_two_shunt",L,C,row)
    for edge in ((0,2),(0,4),(1,2),(2,4),(1,-1),(2,-1),(0,1),(3,4)):
        for row in ((1,2,3,4,0),(4,1,2,3,0),(1,4,2,3,0)):
            add("five_chip_three_GJM",BASE_L+(edge,),BASE_C,row)
    assert len(result)==140
    return result


class Model:
    def __init__(self,job):
        self.job=job; self.nL=job["Lcount"]
        self.le=job["Ledges"];self.ce=job["Cedges"];self.order=job["order"]
        self.B=self.incidence(self.le)
        self.D=np.array([np.outer(v,v) for v in self.incidence(self.ce).T])
        self.ports=np.zeros((5,5),complex)
        self.ports[0,0]=1/50
        self.ports[2,2]=1/(60-40j)
        self.excitation=np.array([1/50,0,0,0,0],complex)
    @staticmethod
    def incidence(edges):
        B=np.zeros((5,len(edges)),complex)
        for i,(a,b) in enumerate(edges):
            if a>=0:B[a,i]+=1
            if b>=0:B[b,i]-=1
        return B
    def metrics(self,x,frequencies):
        nL=self.nL;nc=len(self.ce);nk=nL-1
        L=np.exp(x[:nL])*1e-9
        C=np.exp(x[nL:nL+nc])*1e-12
        ks=x[nL+nc:nL+nc+nk]
        tun=x[nL+nc+nk:].reshape(6,2)*1e-12
        K=np.eye(nL)
        M=np.diag(L.astype(complex))
        for idx,k in enumerate(ks):
            a,b=self.order[idx:idx+2]
            K[a,b]=K[b,a]=k
            M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
        if np.linalg.eigvalsh(K).min()<=1e-6:
            return np.full((6,3),1000.)
        inductance_admittance=self.B@np.linalg.solve(np.diag(L/25)+1j*M,self.B.T)
        fixed_Y=sum((c/(1/80-1j))*D for c,D in zip(C,self.D))
        out=np.empty((6,3))
        for ci,parts in enumerate(frequencies):
            C_Y=fixed_Y.copy()
            C_Y[3,3]+=tun[ci,0]/(1/80-1j)
            C_Y[4,4]+=tun[ci,1]/(1/80-1j)
            for part,omega in enumerate(parts):
                Y=(self.ports[None,:,:]+inductance_admittance[None,:,:]/omega[:,None,None]
                   +omega[:,None,None]*C_Y[None,:,:])
                voltage=np.linalg.solve(Y,np.broadcast_to(self.excitation,(len(omega),5))[...,None])[...,0]
                gain=np.maximum(200*(60/5200)*abs(voltage[:,2])**2,1e-230)
                IL=-10*np.log10(gain)
                out[ci,part]=IL.max() if part==0 else IL.min()
        return out


def starting_point(job,reference,seed):
    nL=job["Lcount"];nc=len(job["Cedges"]);rng=np.random.default_rng(seed)
    if job["family"]=="three_series_two_ground_controls":
        L=np.array([.62,3.8,4.1,5.2])
        C=np.array([16,1.7,2,.18])
        k=np.array([.1,-.2,.12])
        tun=np.array([[1.8,1.5],[1.7,1.4],[1.5,1.35],[1.4,1.18],[1.2,1.],[1.,.86]])
    else:
        L=np.array([v["L_nH"] for v in reference["topology"]["inductors"]])
        C=np.array([v["C_pF"] for v in reference["topology"]["fixed_caps"]])
        k=np.array(reference["nominal_adjacent_k"])
        tun=np.array([reference["variable_C_pf_by_setting"][c] for c in CASES])
    if nL==5:
        L=np.r_[L,[8.]];k=np.r_[k,[0.]]
    if nc==3:C=C[:3]
    if seed>0:
        L*=np.exp(rng.normal(0,.3,nL))
        C*=np.exp(rng.normal(0,.35,nc))
        k+=rng.normal(0,.04,nL-1)
        tun+=rng.normal(0,.16,(6,2))
    x=np.r_[np.log(L),np.log(C),k,tun.ravel()]
    return x


def optimize(job,reference,seed,iterations,coarse,verification,atten):
    nL=job["Lcount"];nc=len(job["Cedges"]);nk=nL-1
    bounds=([(np.log(.4),np.log(27))]*nL
            +[(np.log(.1),np.log(100))]*nc
            +[(-.4,.4)]*nk+[(0.,4.)]*12)
    lower=np.array([a for a,b in bounds])
    upper=np.array([b for a,b in bounds])
    x=np.clip(starting_point(job,reference,seed),lower+1e-10,upper-1e-10)
    model=Model(job)
    def objective(v):
        a=model.metrics(v,coarse)
        violation=np.maximum(atten-a[:,1:],0)
        return float(a[:,0].max()+50*np.mean(violation**2)+5*np.max(violation)**2)
    r=minimize(objective,x,method="L-BFGS-B",bounds=bounds,
               options={"maxiter":iterations,"ftol":1e-10,"maxls":20})
    a=model.metrics(r.x,verification)
    return dict(job_id=job["id"],family=job["family"],topology=job,seed=seed,
                max_IL_db=float(a[:,0].max()),min_H2_db=float(a[:,1].min()),
                min_H3_db=float(a[:,2].min()),nominal_pass=bool(
                    a[:,1:].min()>=35 and a[:,0].max()<=.4),
                satisfies_35dB=bool(a[:,1:].min()>=35),
                optimizer_converged=bool(r.success),optimizer_message=str(r.message),
                iterations=int(r.nit),nfev=int(r.nfev),objective=float(r.fun),
                x=r.x.tolist(),verification_grid_points_per_segment=verification[0][0].size,
                global_optimum_proven=False,independent_MNA_verified=False)


def reference_check(ref):
    d=ref["topology"]
    convert=lambda edge:(edge["a"]-1 if edge["a"] else -1,
                         edge["b"]-1 if edge["b"] else -1)
    job={"Ledges":[convert(e) for e in d["inductors"]],
         "Cedges":[convert(e) for e in d["fixed_caps"]],
         "order":[int(t[1:]) for t in ref["physical_chip_row"]],"Lcount":4}
    x=np.r_[np.log([z["L_nH"] for z in d["inductors"]]),
            np.log([z["C_pF"] for z in d["fixed_caps"]]),
            ref["nominal_adjacent_k"],
            np.array([ref["variable_C_pf_by_setting"][b] for b in CASES]).ravel()]
    m=Model(job).metrics(x,grids(9))
    if abs(m[:,0].max()-ref["verified_dense_metrics"]["worst_IL_db"])>1e-6:
        raise RuntimeError("A7-01 reference regression mismatch")
    print("A7-01 reference reproduced: worstIL %.9f dB"%m[:,0].max())


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard-index",type=int,default=0)
    p.add_argument("--shard-count",type=int,default=4)
    p.add_argument("--max-new-jobs",type=int,default=3)
    p.add_argument("--starts",type=int,default=1)
    p.add_argument("--iterations",type=int,default=80)
    p.add_argument("--coarse-points",type=int,default=3)
    p.add_argument("--verification-points",type=int,default=13)
    p.add_argument("--atten",type=float,default=35.07)
    p.add_argument("--seed",type=int,default=20261011)
    p.add_argument("--checkpoint",type=Path)
    p.add_argument("--reference-only",action="store_true")
    args=p.parse_args()
    ref=json.loads(REF.read_text(encoding="utf-8"))
    reference_check(ref)
    if args.reference_only:return
    if not (0<=args.shard_index<args.shard_count and args.max_new_jobs>=1
            and 1<=args.starts<=20 and args.iterations>=1 and args.atten>=35):
        p.error("Invalid search settings")
    joblist=jobs()
    fingerprint=hashlib.sha256(
        (POLICY.read_bytes()+BANDS.read_bytes()+Path(__file__).read_bytes()
         +json.dumps({"n":args.shard_count,"starts":args.starts,"seed":args.seed,
                      "iterations":args.iterations,"atten":args.atten}).encode())
    ).hexdigest()
    state={"fingerprint":fingerprint,"records":[],"failures":[],
           "completed_job_ids":[],"unfinished":True,"goal_max_IL_db":.4,
           "target_stop_atten_db":args.atten,"commit_sha":os.getenv("GITHUB_SHA","local"),
           "shard_index":args.shard_index,"shard_count":args.shard_count}
    if args.checkpoint and args.checkpoint.exists():
        old=json.loads(args.checkpoint.read_text(encoding="utf-8"))
        if old["fingerprint"]!=fingerprint:
            raise RuntimeError("Cannot resume a checkpoint with mismatched source or settings")
        state=old
    assigned=[j for j in joblist if j["id"]%args.shard_count==args.shard_index]
    fresh=0;start=time.monotonic()
    for job in assigned:
        if job["id"] in state["completed_job_ids"]:continue
        if fresh>=args.max_new_jobs:break
        for k in range(args.starts):
            try:
                row=optimize(job,ref,args.seed+1000*job["id"]+k,args.iterations,
                             grids(args.coarse_points),grids(args.verification_points),
                             args.atten)
                state["records"].append(row)
            except Exception as exc:
                state["failures"].append({"job_id":job["id"],"start":k,
                                          "error":repr(exc)})
        state["completed_job_ids"].append(job["id"])
        fresh+=1
        state["unfinished"]=len(state["completed_job_ids"])<len(assigned)
        state["run_seconds"]=round(time.monotonic()-start,2)
        if args.checkpoint:
            args.checkpoint.parent.mkdir(parents=True,exist_ok=True)
            tmp=args.checkpoint.with_suffix(".tmp")
            tmp.write_text(json.dumps(state,indent=1)+"\n",encoding="utf-8")
            tmp.replace(args.checkpoint)
        print("completed graph",job["id"],"fresh",fresh,"of",len(assigned),flush=True)
    good=sorted((r for r in state["records"] if r["satisfies_35dB"]),
                key=lambda r:r["max_IL_db"])
    print("final shard",args.shard_index,"completed",len(state["completed_job_ids"]),
          "of",len(assigned),"failures",len(state["failures"]),
          "best valid",good[0]["max_IL_db"] if good else None,
          "uncompleted",state["unfinished"])


if __name__=="__main__":
    main()
