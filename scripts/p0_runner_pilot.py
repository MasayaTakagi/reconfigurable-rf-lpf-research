#!/usr/bin/env python3
"""P0 GitHub-hosted runner endurance pilot; no new RF performance claims."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--minutes",type=int,default=2)
    p.add_argument("--output",default="results/p0_runner_pilot.json")
    a=p.parse_args()
    if not 1<=a.minutes<=30:
        p.error("minutes must be 1..30")
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    rows=[]
    manifest={"status":"running","git_sha":os.getenv("GITHUB_SHA","unknown"),
              "run_id":os.getenv("GITHUB_RUN_ID","local"),
              "python":sys.version,"platform":platform.platform(),
              "start_utc":datetime.now(timezone.utc).isoformat(),
              "requested_minutes":a.minutes,"runs":rows}
    checks=[
        ["experiments/matching_cost_20261010/verify_adjacent_1d.py"],
        ["experiments/matching_cost_20261010/reoptimize_lqp02.py"],
    ]
    def persist():
        tmp=out.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        tmp.replace(out)
    persist()
    deadline=started+a.minutes*60
    index=0
    while time.monotonic()<deadline or index==0:
        check=checks[index%len(checks)]
        begin=time.monotonic()
        remaining=max(30,int(deadline-begin))
        try:
            proc=subprocess.run([sys.executable,*check],capture_output=True,text=True,
                                timeout=min(remaining,600),check=False)
            code=proc.returncode
            stdout=proc.stdout[-6000:]
            stderr=proc.stderr[-6000:]
        except subprocess.TimeoutExpired as exc:
            code=124
            stdout=str(exc.stdout or "")[-6000:]
            stderr="subprocess timeout: "+str(exc)
        rows.append({"index":index,"script":check[0],"returncode":code,
                     "elapsed_seconds":round(time.monotonic()-begin,3),
                     "stdout_tail":stdout,"stderr_tail":stderr})
        manifest["elapsed_seconds"]=round(time.monotonic()-started,3)
        manifest["completed_checks"]=len(rows)
        persist()
        if code!=0:
            manifest["status"]="failed"
            persist()
            print("P0 validation failed",file=sys.stderr)
            return 1
        index+=1
    manifest["status"]="completed"
    manifest["finish_utc"]=datetime.now(timezone.utc).isoformat()
    persist()
    print(json.dumps({"status":manifest["status"],"checks":len(rows),
                      "elapsed_seconds":manifest["elapsed_seconds"],"output":str(out)}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
