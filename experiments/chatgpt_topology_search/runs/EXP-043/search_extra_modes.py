#!/usr/bin/env python3
"""EXP-043 extra third-mode designs: C from shunt node to a signal node."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.linalg import eig
import search_3l as base
from lpf.constraint_versions import load_constraint

CONFIGS={
 "zero_trap_out":(("PCB","PCB","PCB"),((3,-1),(0,1),(2,3))),
 "zero_trap_in":(("PCB","PCB","PCB"),((3,-1),(1,2),(0,3))),
 "one_trap_out":(("GJM","PCB","PCB"),((3,-1),(0,2),(2,3))),
 "two_trap_out":(("GJM","GJM","PCB"),((3,-1),(0,2),(2,3))),
}

def modes(ev,vector):
    x=np.array(vector,float)
    _,M,_=ev.matrices(x)
    K=base.BL@np.linalg.solve(M,base.BL.T)
    result=[]
    for s in range(6):
        Cs=np.r_[x[3:6],x[8+3*s:11+3*s]]
        C=ev.BC@np.diag(Cs)@ev.BC.T
        eigvals=eig(K,C)[0]
        positive=[float(np.sqrt(v.real)*5.03292121) for v in eigvals
                  if np.isfinite(v) and abs(v.imag)<1e-7 and v.real>1e-9]
        result.append({"case":base.CASES[s],"C_rank":int(np.linalg.matrix_rank(C,tol=1e-8)),
                       "finite_lossless_modes_GHz":sorted(positive)})
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",choices=CONFIGS,required=True)
    ap.add_argument("--starts",type=int,default=4)
    ap.add_argument("--maxiter",type=int,default=140)
    ap.add_argument("--coarse",type=int,default=5)
    ap.add_argument("--dense",type=int,default=701)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    policy=load_constraint("RF-T005",allow_trial=True)
    assert (base.HERE/"manifest.json").exists()
    base.CONFIGS=CONFIGS
    checkpoint=("two_gjm_bridge" if a.variant=="two_trap_out" else "zero_gjm_double")
    seed=np.array(json.loads((base.HERE/"checkpoints"/(checkpoint+".json")).read_text())["vector"],float)
    baseline=base.seed_vector
    def start(ev,rng,j):
        if j==0: return seed.copy()
        if j==3:return baseline(ev,rng,j)
        x=seed.copy()
        x[:3]*=np.exp(rng.normal(0,.22,3))
        x[3:6]*=np.exp(rng.normal(0,.28,3))
        x[6:8]+=rng.normal(0,.025,2)
        x[8:]+=rng.normal(0,.19,18)
        return np.clip(x,ev.bounds[:,0],ev.bounds[:,1])
    base.seed_vector=start
    r=base.search(a.variant,policy,a.starts,a.maxiter,a.coarse,a.dense,20261018)
    ev=base.Evaluator(policy,a.variant,3)
    r["independent_lossless_unterminated_modal_eigenanalysis"]=modes(ev,r["selected"]["vector"])
    r["note"]="Modal eigenvalues are neither loaded transmission-zero positions nor broadband attenuation proof."
    out=a.output or base.ROOT/"results"/"EXP-043"/(a.variant+".json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n")
    print("MODES",a.variant,json.dumps(r["independent_lossless_unterminated_modal_eigenanalysis"]),flush=True)
    print("OUTPUT",out,flush=True)

if __name__=="__main__":main()
