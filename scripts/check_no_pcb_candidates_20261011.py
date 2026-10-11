#!/usr/bin/env python3
"""Check new PCB-free candidate JSONs using the repository's independent MNA topology.

Usage from repository root:
    python scripts/check_no_pcb_candidates_20261011.py
"""
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lpf.circuit import Branch, solve
from lpf.evaluate import evaluate_settings, CASES
from lpf.validate import validate_couplings


def build_settings(raw):
    order = [int(name[1:]) for name in raw["chip_physical_order"]]
    ks = raw["chip_k_per_adjacent_pair"]
    K = np.eye(4)
    for j in range(3):
        a, b = order[j], order[j+1]
        K[a,b] = K[b,a] = ks[j]
    assert not validate_couplings(K, ["chip"]*4, order,
                                  strong_pairs=[(order[i],order[i+1]) for i in range(3)],
                                  nominal=True)
    types=raw["chip_inductor_types"]
    area=sum(1 if t=="LQP02" else 2/3 for t in types)
    area+=2/3*raw["fixed_gjm01_count"]
    assert area<=6+1e-10
    assert raw["zero_pcb_inductors"]
    L=raw["chip_inductor_nh"]
    Q=raw["chip_inductor_q"]
    # The shunt trap is represented with an *actual internal node 5*:
    # node3 -- L1 -- node5 -- Cf1 -- ground, not a collapsed diagonal element.
    ind=[Branch(1,2,L[0]*1e-9,Q[0]),
         Branch(3,5,L[1]*1e-9,Q[1]),
         Branch(3,4,L[2]*1e-9,Q[2]),
         Branch(2,3,L[3]*1e-9,Q[3])]
    edges={0:(1,2),1:(5,0),2:(3,4),3:(2,3)}
    fixed=[]
    for c in raw["topology"]["fixed_caps"]:
        i=int(c["linked_inductor"][1:])
        fixed.append(Branch(*edges[i],c["value_pf"]*1e-12,80))
    assert all(0<c.value<=100e-12 for c in fixed)
    assert len(raw["topology"]["variable_caps"])==2
    settings={}
    for name in CASES:
        caps=list(fixed)
        for c in raw["topology"]["variable_caps"]:
            pf=raw["settings"][name][c["id"]+"_pf"]
            assert 0<=pf<=4 and c["b"]==0
            caps.append(Branch(c["a"],0,pf*1e-12,80))
        settings[name]=dict(n_nodes=5,source_node=1,load_node=4,
                            inductors=ind,capacitors=caps,coupling=K,
                            source_ohms=50,load_ohms=60-40j)
    return settings


def audit_candidate(path,samples_per_segment=401):
    raw=json.loads(path.read_text(encoding="utf-8"))
    settings=build_settings(raw)
    report=evaluate_settings(lambda name:settings[name],
                             samples_per_segment=samples_per_segment)
    il=report["worst_il_db"][0]
    h2=report["min_h2_db"][0]
    h3=report["min_h3_db"][0]
    claimed=raw["result"]
    for observed,key in ((il,"max_il_db"),(h2,"min_h2_db"),(h3,"min_h3_db")):
        assert abs(observed-claimed[key])<0.001,(path,key,observed,claimed[key])
    assert h2>=35 and h3>=35 and il>0.30
    max_res=max(abs(solve(1e9,**settings[name])["power_residual"]) for name in CASES)
    assert max_res<1e-10, max_res
    print(raw["candidate_id"],f"worstIL={il:.6f}",
          f"H2min={h2:.6f}",f"H3min={h3:.6f}",
          f"max_power_residual_W={max_res:.2e}")
    return report


if __name__=="__main__":
    for candidate_id in ("LPF-005","LPF-006"):
        audit_candidate(ROOT/"candidates"/(candidate_id+".json"))
