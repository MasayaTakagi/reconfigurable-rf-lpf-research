#!/usr/bin/env python3
"""Independent MNA cross-check for exploratory area-7 full LPF references.

Historical baseline approved cap=6 was in force at experiment time. These
old exploratory references used cost cap=7; current RF-F001 has no area cap. Finite frequency grids do not prove global
optimality or continuous-band validity.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/"src"))

from lpf.circuit import Branch,solve
from lpf.configuration import validate_six_settings
from lpf.evaluate import CASES,evaluate_settings,load_bands
from lpf.independent import solve_gain
from lpf.validate import validate_couplings


def load_reference(reference):
    path=Path(reference)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    candidate=(Path(__file__).resolve().parent/(str(reference)+".json"))
    if not candidate.is_file() and str(reference)=="A7-03":
        candidate=Path(__file__).resolve().parent.parent/"EXP-005/A7-03.json"
    if not candidate.is_file() and str(reference)=="A7-04":
        candidate=Path(__file__).resolve().parent.parent/"EXP-006/A7-04.json"
    return json.loads(candidate.read_text(encoding="utf-8"))


def build_settings(d):
    assert d["study_override"]["exploratory_cost_cap"]==7
    assert d["study_override"]["approved_base_cap"]==6
    assert d["study_override"]["canonical_policy_hard_cap_modified"] is False
    assert d["components"]["LQP02"]["count"]==4
    assert d["components"]["GJM01"]["count"]==4
    assert d["components"]["PCB_PATTERN_C"]["count"]==0
    assert d["components"]["PCB_L"]["count"]==0
    assert d["components"]["IC_VARIABLE_C"]["count"]==2
    cost=4+4*(2/3)
    assert abs(d["chip_area_cost_units"]-cost)<1e-12 and cost<=7
    topo=d["topology"]
    chips=topo["inductors"]
    caps=topo["fixed_caps"]
    variables=topo["variable_caps"]
    assert len(chips)==4 and len(caps)==4 and len(variables)==2
    for ind in chips:
        assert ind["Q"]==25 and ind["L_nH"]>0
    for cap in caps:
        assert cap["Q"]==80 and cap["type"]=="GJM01"
        assert 0<cap["C_pF"]<=100
    for v in variables:
        assert v["Q"]==80 and (v["a"]==0 or v["b"]==0)
        assert v["min_pF"]==0 and v["max_pF"]==4
    ids=[v["id"] for v in chips]
    order=[ids.index(name) for name in d["physical_chip_row"]]
    pairs=[(ids.index(a),ids.index(b)) for a,b in d["designated_strong_adjacent_pairs"]]
    K=np.eye(len(chips))
    for i,val in enumerate(d["nominal_adjacent_k"]):
        a,b=order[i:i+2]
        K[a,b]=K[b,a]=float(val)
    violations=validate_couplings(K,["chip"]*len(chips),order,strong_pairs=pairs,nominal=True)
    if violations: raise ValueError(f"Coupling policy violation: {violations}")
    L=tuple(Branch(c["a"],c["b"],c["L_nH"]*1e-9,c["Q"]) for c in chips)
    Cf=tuple(Branch(c["a"],c["b"],c["C_pF"]*1e-12,c["Q"]) for c in caps)
    cfg={}
    for case in CASES:
        values=d["variable_C_pf_by_setting"][case]
        if len(values)!=2 or any(not 0<=v<=4 for v in values):
            raise ValueError("Invalid variable-C setting")
        Cv=tuple(Branch(v["a"],v["b"],c*1e-12,v["Q"]) for v,c in zip(variables,values))
        cfg[case]=dict(n_nodes=topo["n_nodes"],source_node=topo["input_node"],
                       load_node=topo["output_node"],inductors=L,capacitors=Cf+Cv,
                       coupling=K.copy(),source_voltage=1.0,source_ohms=50.0,
                       load_ohms=60.-40.j)
    validate_six_settings(cfg,variable_cap_indices=(4,5))
    return cfg,K


def verify(d,samples_per_segment=61,check_reference=False):
    cfg,K=build_settings(d)
    results=evaluate_settings(lambda case:cfg[case],samples_per_segment=samples_per_segment)
    independent_gain_error=0.
    power_error=0.
    rows=load_bands()
    for case in CASES:
        for row in (r for r in rows if r["case"]==case):
            for f in (float(row["low_mhz"]),float(row["high_mhz"])):
                sample=solve(f*1e6,**cfg[case])
                independent_gain_error=max(independent_gain_error,
                     abs(sample["gain"]-solve_gain(f*1e6,**cfg[case])))
                power_error=max(power_error,abs(sample["power_residual"]))
    max_il=results["worst_il_db"][0];h2=results["min_h2_db"][0];h3=results["min_h3_db"][0]
    if not (max_il<0.52 and h2>=35-0.001 and h3>=35-0.001):
        raise AssertionError("Area7 candidate failed basic RF passband/harmonics")
    if independent_gain_error>1e-9 or power_error>1e-10:
        raise AssertionError("MNA/power balance discrepancy")
    if check_reference:
        saved=d["verified_dense_metrics"]
        # On a sparse grid, extrema cannot be worse than those found on a
        # sufficiently sampled denser grid by more than numerical tolerance.
        if max_il>saved["worst_IL_db"]+1e-5 or h2<saved["min_H2_db"]-1e-5 or h3<saved["min_H3_db"]-1e-5:
            raise AssertionError("Measured grid contradicted saved dense reference")
    return dict(max_il_db=max_il,min_h2_db=h2,min_h3_db=h3,
                samples_per_segment=samples_per_segment,
                min_K_eigenvalue=float(np.linalg.eigvalsh(K).min()),
                worst_independent_gain_error=independent_gain_error,
                max_power_balance_residual_W=power_error,
                per_setting=results["per_case"],grid_only=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",choices=("A7-01","A7-02","A7-03","A7-04"),default="A7-01")
    p.add_argument("--points",type=int,default=61,
                   help="Samples PER listed frequency segment; use 7001 for <=0.02 MHz H3 grid")
    p.add_argument("--check-saved",action="store_true")
    p.add_argument("--out")
    args=p.parse_args()
    if args.points<2: p.error("points must be >=2")
    d=load_reference(args.reference)
    report=verify(d,samples_per_segment=args.points,check_reference=args.check_saved)
    if args.out:
        Path(args.out).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"{args.reference}: max IL={report['max_il_db']:.9f}dB, "
          f"min H2={report['min_h2_db']:.9f}dB, min H3={report['min_h3_db']:.9f}dB; "
          f"independent gain error={report['worst_independent_gain_error']:.3e}, "
          f"power balance residual={report['max_power_balance_residual_W']:.3e} W")


if __name__=="__main__":
    main()
