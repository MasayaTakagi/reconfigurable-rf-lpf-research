#!/usr/bin/env python3
"""EXP-043 Phase2 one GJM Cp trial local improvement validation.

Verifies both saved benchmark and locally retuned target; counts ALL 28 CSV
intervals separately at 1001 points per range, with mandatory input/output
fixed S2Ps and source50/load60-j40. Uses independent 7x7 MNA from established
EXP-043 verify code. This performs no search; it is a deterministic check.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from lpf.constraint_versions import load_constraint
import diagnose_pcb_gjm as verify
import search_3l as source

HERE=Path(__file__).resolve().parent
CHECKS=[
  ("original","gjm_cp.json"),
  ("locally_retuned","gjm_cp_local_H30p0032.json")
]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--samples",type=int,default=1001)
    ap.add_argument("--mna-points",type=int,default=3)
    ap.add_argument("--out",type=Path)
    arg=ap.parse_args()
    p=load_constraint("RF-T005",allow_trial=True)
    e=verify.evaluator(p,"gjm_cp",arg.samples)
    assert np.array_equal(e.Q_C,[40,40,80,35,35,35])
    report={"experiment":"EXP-043","constraint_id":"RF-T005","phase":2,
            "topology":"3 LQP02HV, PCB Cf0/Cf1, GJM Cp, three Cv",
            "frequency_segments":28,"samples_per_segment":arg.samples,
            "vectors":[]}
    for name,check in CHECKS:
        src=json.loads((HERE/"checkpoints"/check).read_text())
        x=np.asarray(src["vector"],float)
        assert len(x)==26
        assert np.all(x[:3]>=0.4) and np.all(x[:3]<=27)
        assert np.all(x[3:5]>=.02) and np.all(x[3:5]<=.2)
        assert x[5]>=.02 and x[5]<=100
        assert np.all(np.abs(x[6:8])<=.1000000001)
        assert np.all(x[8:]>=0) and np.all(x[8:]<=3)
        scalar=e.summary(x)
        mna=verify.mna_verify(p,"gjm_cp",x,points=arg.mna_points)
        row={"id":name,"checkpoint":str(check),"metrics":scalar,
             "strict_H2H3_30db_pass":bool(scalar["min_H2_db"]>=30 and
                                      scalar["min_H3_db"]>=30),
             "IL_below_interim_0p8db":bool(scalar["worst_IL_db"]<=.8),
             "independent_7x7_mna":mna}
        report["vectors"].append(row)
        print(name,"IL",scalar["worst_IL_db"],
              "H2",scalar["min_H2_db"],"H3",scalar["min_H3_db"],
              "MNA_PASS",mna["passed"],flush=True)
        if not row["strict_H2H3_30db_pass"] or not mna["passed"]:
            raise AssertionError("RF-T005 numerical / independent MNA failed")
    b,r=report["vectors"]
    report["delta_IL_dB"]=b["metrics"]["worst_IL_db"]-r["metrics"]["worst_IL_db"]
    print("IMPROVEMENT_dB",report["delta_IL_dB"],flush=True)
    out=arg.out or source.ROOT/"results"/"EXP-043"/"verify_area3p667_local.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("OUTPUT",out,flush=True)
if __name__=="__main__":
    main()
