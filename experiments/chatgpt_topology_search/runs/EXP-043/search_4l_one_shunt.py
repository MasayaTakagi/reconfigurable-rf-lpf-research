#!/usr/bin/env python3
"""EXP-043 companion search: 4 chip L, THREE main-series, ONE shunt L.

Purpose: one shunt-L only, but extra series-L resonance freedom vs 3L.
Chip areas 4 and 4+2/3 under RF-T005; other resource bounds unchanged.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import search_3l as engine
from scipy.optimize import minimize

L_EDGES=((0,1),(1,2),(2,3),(2,4))  # L0,L1,L2 in series + exactly Ls in shunt
CF_EDGES=((0,1),(1,2),(2,3),(4,-1))
PHYSICAL_ORDER=(0,3,1,2)  # row L0-Ls-L1-L2, adjacent strong coupling ONLY
CONFIGS={
  "4L_noGJM_caps":(("PCB","PCB","PCB"),((4,-1),(0,1),(2,3))),
  "4L_noGJM_bridge":(("PCB","PCB","PCB"),((4,-1),(0,1),(0,3))),
  "4L_oneGJM_ends":(("GJM","PCB","PCB","PCB"),((4,-1),(0,3),(2,3))),
  "4L_oneGJM_cross":(("GJM","PCB","PCB","PCB"),((4,-1),(0,2),(1,3))),
}
# First two families hold 3 PCB fixed Cs, using (Cf0,Cf2,Cp)
# and deliberately OMIT Cf1: 3+3 variables total. Other family uses
# Cf0 GJM, Cf1/Cf2/Cp PCB (three PCB caps) = one GJM.
CF_EDGES_NO_GJM=((0,1),(2,3),(4,-1))

def incidence(edges):
    B=np.zeros((5,len(edges)),float)
    for i,(a,b) in enumerate(edges):
        B[a,i]=1
        if b>=0: B[b,i]=-1
    return B

BL=incidence(L_EDGES)
def bounds_and_q(config):
    c,v=CONFIGS[config]
    assert len(v)==3 and len(c) in (3,4)
    assert sum(t=="PCB" for t in c)<=3
    bounds=([(0.4,27.)]*4+
            [(0.02,100.) if t=="GJM" else (0.02,0.2) for t in c]+
            [(-.1,.1)]*3+[(0.,3.)]*18)
    # Expand 3-fixed candidate with dummy 0-valued absent Cf1, represented
    # by fixed zero branch that incurs no Q or area. 4 fixed positions total.
    if len(c)==3:
        # C components Cf0,Cf1(absent),Cf2,Cp in fixed order.
        xbounds=[bounds[0:4],
                 [bounds[4],(0.,0.),bounds[5],bounds[6]],
                 bounds[7:]]
        bounds=sum(xbounds,[])
        types=(c[0],"ABSENT",c[1],c[2])
        edge=CF_EDGES
    else:
        types=c
        edge=CF_EDGES
    Q_C=np.asarray([80 if t=="GJM" else 40 for t in types]+[35]*3)
    area=4.+(2./3.)*sum(t=="GJM" for t in types)
    return np.array(bounds,float),Q_C,area,incidence(edge+v)

class Evaluator(engine.Evaluator):
    def matrices(self,x):
        L=np.asarray(x[:4],float)
        M=np.diag(L.copy())
        for (i,j),k in zip(((0,3),(3,1),(1,2)),x[8:11]):
            M[i,j]=M[j,i]=k*np.sqrt(L[i]*L[j])
        H=np.diag(L/25.)+1j*M
        return BL@np.linalg.solve(H,BL.T),M,H

    def il(self,x):
        x=np.asarray(x,float)
        if self.cache_x is not None and np.array_equal(self.cache_x,x):
            return self.cache_il
        n=len(self.f)
        K,M,H=self.matrices(x)
        Y=np.broadcast_to(K,(n,5,5)).copy()/(self.omega[:,None,None]*1e-9)
        cv=x[11:].reshape((6,3))[self.setting]
        cap=np.column_stack((np.broadcast_to(x[4:8],(n,4)),cv))
        yc=self.omega[:,None]*1e-12*cap/(1/self.Q_C[None,:]-1j)
        Y+=np.einsum("nb,ib,jb->nij",yc,self.BC,self.BC,optimize=True)
        ports=[0,3];inside=[1,2,4]
        P=Y[:,ports,:][:,:,ports]
        U=Y[:,ports,:][:,:,inside]
        V=Y[:,inside,:][:,:,ports]
        E=Y[:,inside,:][:,:,inside]
        red=P-U@np.linalg.solve(E,V)
        a,b,c,d=red[:,0,0],red[:,0,1],red[:,1,0],red[:,1,1]
        if np.any(np.abs(c)<1e-20): raise ValueError("Singular 4L two port")
        abcd=np.empty((n,2,2),complex)
        abcd[:,0,0]=-d/c
        abcd[:,0,1]=-1/c
        abcd[:,1,0]=-(a*d-b*c)/c
        abcd[:,1,1]=-a/c
        T=self.pre@abcd@self.post
        zl=60-40j;zs=50.
        den=T[:,0,0]*zl+T[:,0,1]+zs*(T[:,1,0]*zl+T[:,1,1])
        il=-10*np.log10(np.maximum(4*zs*zl.real/np.abs(den)**2,1e-300))
        self.cache_x,self.cache_il=x.copy(),il
        return il

def seeds(ev,rng,j):
    x=np.empty(29)
    L=np.array([2.2,2.8,4.5,14.0])*np.exp(rng.normal(0,.30 if j else .02,4))
    x[:4]=np.clip(L,.4,27)
    cguess=np.array([3.,.12,.15,.10])
    for q in range(4):
        lo,hi=ev.bounds[4+q]
        v=cguess[q]*np.exp(rng.normal(0,.3 if j else .01))
        x[4+q]=np.clip(v,lo,hi)
    x[8:11]=np.clip(rng.normal(0,.03 if j else .001,3),-.095,.095)
    bandscale=(1.,.89,.83,.4,.28,.15)
    for i,a in enumerate(bandscale):
        v=np.array([.22,.55,.9])*a
        if j: v*=np.exp(rng.normal(0,.65,3))
        x[11+3*i:14+3*i]=np.clip(v,0,3)
    return np.clip(x,ev.bounds[:,0],ev.bounds[:,1])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",choices=CONFIGS,required=True)
    ap.add_argument("--starts",type=int,default=4)
    ap.add_argument("--maxiter",type=int,default=140)
    ap.add_argument("--coarse",type=int,default=5)
    ap.add_argument("--dense",type=int,default=701)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    from lpf.constraint_versions import load_constraint
    p=load_constraint("RF-T005",allow_trial=True)
    assert (engine.HERE/"manifest.json").exists()
    # Reuse identical objective, noise seeds, and external-S2P evaluator
    # but install this circuit's incidence, component counts and 29-variable seed.
    engine.Evaluator=Evaluator
    engine.CONFIGS=CONFIGS
    engine.L_EDGES=L_EDGES
    engine.CF_EDGES=CF_EDGES
    engine.bounds_and_q=bounds_and_q
    engine.seed_vector=seeds
    results=engine.search(a.variant,p,a.starts,a.maxiter,a.coarse,a.dense,20261016)
    results["source"]="four LQP02HV (three main series, exactly one shunt), RF-T005"
    results["coupling_physical_order"]=list(PHYSICAL_ORDER)
    results["inductor_count"]=4
    results["shunt_inductor_count"]=1
    out=a.output or engine.ROOT/"results"/"EXP-043"/(a.variant+".json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n")
    print("OUTPUT",out,flush=True)

if __name__=="__main__":main()
