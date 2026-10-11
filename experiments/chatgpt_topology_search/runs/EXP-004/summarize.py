#!/usr/bin/env python3
"""Report exact counted partial progress for manual target040 shards."""
import argparse
import json
from pathlib import Path

TOTAL=140
SHARDS=4
BASELINE=0.5083889589116496

def summarize(root):
    shards={}
    records=[]
    missing=[]
    failed=[]
    for idx in range(SHARDS):
        paths=list(root.rglob("shard-%s/checkpoint.json"%idx)) if root.exists() else []
        if len(paths)!=1:
            missing.append(idx)
            shards[idx]={"present":False,"completed":0,"expected":TOTAL//SHARDS}
            continue
        d=json.loads(paths[0].read_text(encoding="utf-8"))
        ids=[int(x) for x in d["completed_job_ids"]]
        valid_assigned={i for i in range(TOTAL) if i%SHARDS==idx}
        if len(ids)!=len(set(ids)) or not set(ids)<=valid_assigned:
            raise ValueError("Duplicate/misattributed job IDs in shard %d"%idx)
        shards[idx]={"present":True,"completed":len(ids),
                     "expected":len(valid_assigned),
                     "unfinished":d.get("unfinished",True),
                     "failure_count":len(d.get("failures",[])),
                     "source_fingerprint":d["fingerprint"],
                     "commit_sha":d.get("commit_sha")}
        records.extend(d.get("records",[]))
        failed.extend(d.get("failures",[]))
    footprints={s["source_fingerprint"] for s in shards.values() if s["present"]}
    if len(footprints)>1:raise ValueError("Incompatible source fingerprints across shards")
    eligible=[x for x in records if (x["min_H2_db"]>=35 and x["min_H3_db"]>=35)]
    eligible.sort(key=lambda x:x["max_IL_db"])
    best=eligible[0] if eligible else None
    complete=(not missing and all(s["completed"]==s["expected"] and not s.get("unfinished")
                                  for s in shards.values()))
    return {
        "workflow":"phase2-target040","objective":"full_lpf","goal_max_il_db":.4,
        "source_area_policy":"experimental chip_cost<=7, owner base hard_cap6 unchanged",
        "job_universe":TOTAL,"completed_unique_jobs":sum(s["completed"] for s in shards.values()),
        "expected_shards":SHARDS,"missing_shards":missing,"shards":shards,
        "start_optimization_records":len(records),"start_failures":len(failed),
        "has_full_declared_graph_coverage":complete,
        "any_optimizer_converged":any(x.get("optimizer_converged") for x in records),
        "best_feasible_result":best,
        "num_full_lpf_35dB_grid_feasible":len(eligible),
        "improved_over_0p508389_baseline":bool(best and best["max_IL_db"]<BASELINE),
        "nominal_0p4_target_reached":bool(best and best["max_IL_db"]<=.4),
        "global_optimum_proven":False,
        "dense_independent_MNA_validation_required_for_any_new_best":True,
        "warning":"Finite sampled grids and nonconvex local optimization; coverage of jobs is not a proof of topology or parameter global optimality."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=summarize(args.input_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Completed %s/%s jobs; missing shards=%s; failures=%s; best feasible IL=%s; target0.4=%s"%(
        result["completed_unique_jobs"],result["job_universe"],result["missing_shards"],
        result["start_failures"],
        None if result["best_feasible_result"] is None else
             result["best_feasible_result"]["max_IL_db"],
        result["nominal_0p4_target_reached"]))
    print("Report:",args.output)
    # Never silently convert failures/missing shards into 'search complete'.


if __name__=="__main__":
    main()
