#!/usr/bin/env python3
"""EXP-042 Phase2 RF-T005 area-Pareto study: remove Cf1/Cf2 and reoptimize."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from optimize import Evaluator, BOUNDS, policy_and_seed, ROOT, HERE

DROPS = {"cf1": (5,), "cf2": (6,), "both": (5, 6)}
CV = {5: (12,15,18,21,24,27), 6: (13,16,19,22,25,28)}

def optimize_variant(kind, target=30.02, starts=3, maxiter=210, grid=9, dense=1001):
    policy, _ = policy_and_seed()
    doc = json.loads((HERE / "slsqp_30_seed.json").read_text())
    assert doc["experiment"] == "EXP-042"
    xbase = np.array(doc["vector"], float)
    drop = DROPS[kind]
    for i in drop:
        old = xbase[i]
        xbase[np.asarray(CV[i])]+=old
        xbase[i]=0.
    assert all(0<=c<=3 for c in xbase[11:])
    active = np.array([i for i in range(29) if i not in drop], int)
    bounds = tuple(BOUNDS[i] for i in active) + ((0.,10.),)
    ev = Evaluator(policy, grid)
    rng = np.random.default_rng(20261016 + sum(drop))
    results = []
    for j in range(starts):
        x0 = xbase.copy()
        if j:
            x0[:4] *= np.exp(rng.normal(0,.045,4))
            x0[8:11] += rng.normal(0,.009,3)
            x0[11:] += rng.normal(0,.04,18)
        for i in active:
            x0[i] = np.clip(x0[i], *BOUNDS[i])
        x0[list(drop)] = 0.
        def full(y):
            x = xbase.copy()
            x[active] = y[:-1]
            return x
        def cons(y):
            vals=ev.il(full(y))
            return np.where(ev.role==0, y[-1]-vals, vals-target)
        init = np.r_[x0[active], ev.summary(x0)["worst_il_db"]]
        res = minimize(lambda y:y[-1], init, method="SLSQP",
                       bounds=bounds, constraints={"type":"ineq","fun":cons},
                       options={"maxiter":maxiter,"ftol":1e-9})
        x = full(res.x)
        sm = ev.summary(x)
        r = {"start":j,"solver_success":bool(res.success),
             "solver_message":str(res.message),"iterations":int(res.nit),
             "evaluations":int(res.nfev),"constraint_slack_db":float(np.min(cons(res.x))),
             "coarse":sm,"vector":x.tolist()}
        results.append(r)
        print("RUN", kind,j,sm["worst_il_db"],sm["min_h2_db"],sm["min_h3_db"],
              "slack",r["constraint_slack_db"],"converged",res.success,flush=True)
    feasible = [r for r in results if r["constraint_slack_db"] >= -1e-7]
    best = (min(feasible,key=lambda d:d["coarse"]["worst_il_db"]) if feasible
            else max(results,key=lambda d:d["constraint_slack_db"]))
    fine = Evaluator(policy,dense).summary(best["vector"])
    area = 6. - len(drop)*2/3
    out = {"experiment":"EXP-042","constraint_id":"RF-T005",
           "source":"C-H30p0002 parallel Cf2||Cv2",
           "variant":kind,"removed_fixed_cap_indices":list(drop),
           "chip_area":area,"chip_inductors":4,"fixed_GJM":3-len(drop),
           "variable_C_branches":3,"variable_C_Q":35,
           "variable_C_range_pF":[0,3],
           "interim_IL_target_db":0.8,"mandatory_H_db":30,
           "optimization_harmonic_target_db":target,
           "coarse_grid_per_segment":grid,"dense_grid_per_segment":dense,
           "starts":starts,"results":results,"selected":best,"dense":fine,
           "dense_pass_30db":fine["min_h2_db"]>=30 and fine["min_h3_db"]>=30,
           "dense_pass_interim_IL":fine["worst_il_db"]<=0.8,
           "cancellation_QLoss_not_ignored":True,
           "caveat":"Finite grid/local optimization; independent MNA and SRF/EM pending."}
    print("FINAL",kind,"area",area,"dense",fine,
          "both_pass",out["dense_pass_30db"] and out["dense_pass_interim_IL"],flush=True)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",required=True,choices=DROPS)
    ap.add_argument("--target",type=float,default=30.02)
    ap.add_argument("--starts",type=int,default=3)
    ap.add_argument("--maxiter",type=int,default=210)
    ap.add_argument("--grid",type=int,default=9)
    ap.add_argument("--dense",type=int,default=1001)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    out=optimize_variant(args.variant,args.target,args.starts,args.maxiter,args.grid,args.dense)
    path=args.out or ROOT/"results"/"EXP-042"/("area_"+args.variant+".json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("OUTPUT",path,flush=True)

if __name__=="__main__": main()
