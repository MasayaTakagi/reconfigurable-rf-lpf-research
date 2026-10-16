#!/usr/bin/env python3
"""EXP-043 three-L shunt node relocation: IN vs OUT taps, same RF-T005."""
import argparse
import json
from pathlib import Path
import numpy as np
import search_3l as base
from lpf.constraint_versions import load_constraint

CONFIGS={
    "shunt_in_zero":base.CONFIGS["zero_gjm_double"],
    "shunt_out_zero":base.CONFIGS["zero_gjm_double"],
    "shunt_in_twoGJM":base.CONFIGS["two_gjm_bridge"],
    "shunt_out_twoGJM":base.CONFIGS["two_gjm_bridge"],
    "shunt_in_zeroBridge":base.CONFIGS["zero_gjm_bridge"],
    "shunt_out_zeroBridge":base.CONFIGS["zero_gjm_bridge"],
}
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
    new_tap=0 if a.variant.startswith("shunt_in_") else 2
    L_EDGES=((0,1),(1,2),(new_tap,3))
    base.CONFIGS=CONFIGS
    base.L_EDGES=L_EDGES
    base.BL=base.incidence(L_EDGES)
    checkpoint_name=("two_gjm_bridge" if a.variant.endswith("twoGJM")
                      else "zero_gjm_double")
    f=base.HERE/"checkpoints"/(checkpoint_name+".json")
    seed=np.array(json.loads(f.read_text())["vector"],float)
    original_seeds=base.seed_vector
    def seed_from_checkpoint(ev,rng,j):
        if j==0:return seed.copy()
        x=seed.copy()
        x[:3]*=np.exp(rng.normal(0,.17,3))
        x[3:6]*=np.exp(rng.normal(0,.20,3))
        x[6:8]+=rng.normal(0,.028,2)
        x[8:]+=rng.normal(0,.17,18)
        if j==3:
            x=original_seeds(ev,rng,j)
        return np.clip(x,ev.bounds[:,0],ev.bounds[:,1])
    base.seed_vector=seed_from_checkpoint
    result=base.search(a.variant,policy,a.starts,a.maxiter,a.coarse,a.dense,20261017)
    result["shunt_attachment_electrical_node"]=new_tap
    result["L_connections"]=L_EDGES
    result["origin_checkpoint"]=checkpoint_name
    result["physical_shunt_count"]=1
    out=a.output or base.ROOT/"results"/"EXP-043"/(a.variant+".json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("OUTPUT",out,flush=True)

if __name__=="__main__":main()
