#!/usr/bin/env python3
"""RF-T003 25nH capped 6L rejection-margin variants, finite-grid replay.

Run: python scripts/verify_rft003_row25_margin.py --points 7001
Model: constant Q; independent 11x11 augmented branch-current MNA and power
balance at 84 points. This does not certify continuous frequencies or EM.
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_cost_6p67 import check
DATA=ROOT/"data/validation/rft003_20261013/row25_rejection_margin_variants.json"

def verify(points=9):
    blob=json.loads(DATA.read_text(encoding="utf-8"))
    assert blob["trial_id"]=="RF-T003" and blob["phase"]=="Phase 2"
    result={}
    for entry in blob["entries"]:
        c=dict(entry["circuit"])
        c["candidate_id"]=entry["candidate_id"]
        assert max(c["L_nH"])<=25.00000001
        assert c["physical_chip_row"]==[2,1,3,5,0,4]
        assert c["L_series"]==["LQP02HV"]*6 and c["L_Q"]==[25]*6
        r=check(c,points)
        assert r["min_H2_db"]>=entry["target_min_atten_dB"]-1e-6
        assert r["min_H3_db"]>=entry["target_min_atten_dB"]-1e-6
        assert r["IL_goal_pass"]
        result[entry["candidate_id"]]=r
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--points",type=int,default=9)
    options=parser.parse_args()
    print(json.dumps(verify(options.points),indent=2,ensure_ascii=False))
