#!/usr/bin/env python3
"""RF-T003 cost6+2/3 inductance-limit sensitivity: replay independently.

This repeats dense segmented nodal analysis and 84 independent augmented
11x11 MNA spot checks. It does not run nonconvex optimization, simulate EM,
or certify SRF, frequency-variable Q or continuous-band extrema.

Run: python scripts/verify_rft003_Lcap.py --points 7001
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_cost_6p67 import check

DATA=ROOT/"data/validation/rft003_20261013/Lcap_reoptimization_20261013.json"

def verify(points=9):
    data=json.loads(DATA.read_text(encoding="utf-8"))
    assert data["phase"]=="Phase 2" and data["trial_id"]=="RF-T003"
    out={}
    for entry in data["observations"]:
        c=entry["circuit"]
        assert max(c["L_nH"])<=entry["Lcap_nH"]+1e-8
        assert c["L_series"]==["LQP02HV"]*6 and c["L_Q"]==[25]*6
        assert all(z["kind"]=="GJM01" for z in c["fixed_capacitors"][:1])
        assert all(z["kind"]=="PCB_PATTERN_C" for z in c["fixed_capacitors"][1:])
        assert abs(c["chip_cost"]-(6+2/3))<1e-10
        result=check(c,points)
        assert result["IL_goal_pass"]
        if points==7001:
            v=entry["verification"]
            assert result["independent_MNA_spots"]==v["independent_MNA_spots"]
            assert result["max_independent_delta_db"]<1e-8
            assert result["max_power_residual_W"]<1e-12
        out[entry["id"]]=result
    return out

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--points",type=int,default=9)
    args=parser.parse_args()
    print(json.dumps(verify(args.points),indent=2,ensure_ascii=False))
