#!/usr/bin/env python3
"""Phase 2 RF-T003: 25nH-capped six-L coupling-row candidate replay.

Numerical full-band nodal and independent full 11x11 current MNA and power
balance, following the original RF-T003 trial. No new RF-F001, EM, SRF, Q(f)
or continuous-frequency proof. Does not rerun 150 optimizer starts.
Run: python scripts/verify_rft003_new_row.py --points 7001
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_rft003_cost_6p67 import check
PATH=ROOT/"data/validation/rft003_20261013/new_25nH_row30p101_best.json"
def verify(points=9):
    data=json.loads(PATH.read_text(encoding="utf-8"))
    assert data["trial"]=="RF-T003" and data["phase"]=="Phase 2"
    c=dict(data["circuit"])
    c["candidate_id"]=data["candidate_id"]
    c["adjacent_k"]=c.pop("adjacent_signed_k")
    c["validated_dense"]=dict(
        worst_IL_db=data["validation"]["worst_IL_db"],
        min_H2_db=data["validation"]["min_H2_db"],
        min_H3_db=data["validation"]["min_H3_db"],
        passes_RF_T003_nominal=True)
    assert c["L_series"]==["LQP02HV"]*6
    assert max(c["L_nH"])<=25.00000001
    assert len(c["fixed_capacitors"])==4 and sum(
        z["kind"]=="GJM01" for z in c["fixed_capacitors"])==1
    return check(c,points)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--points",type=int,default=9)
    a=p.parse_args()
    print(json.dumps(verify(a.points),indent=2,ensure_ascii=False))
