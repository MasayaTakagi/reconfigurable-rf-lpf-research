#!/usr/bin/env python3
"""Re-evaluate an RF-F002 EXP-017 checkpoint with the independent branch-current MNA.

Finite-grid calculation; no SRF, EM or physical tolerance certification.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.lpf.circuit import Branch, solve
from src.lpf.evaluate import CASES, load_bands


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--points", type=int, default=101)
    options = parser.parse_args()
    if options.points < 2:
        parser.error("--points must be at least 2")
    data = json.loads(options.candidate.read_text(encoding="utf-8"))
    if data.get("constraint_id") != "RF-F002":
        raise ValueError("RF-F002 candidate required")
    if data.get("constraint_sha256") != "f20d27e93451dcec2f823e6f7c3731c06d843050c4d2ace8b0b46ded605542e2":
        raise ValueError("RF-F002 fingerprint mismatch")
    if data.get("objective") != "full_lpf" or data.get("phase") != "Phase 2":
        raise ValueError("Invalid objective or phase")
    if data.get("source_ohm") != 50 or data.get("load_ohm") != {"real": 60, "imag": -40}:
        raise ValueError("Port impedances do not match RF-F002")

    comp, topo = data["components"], data["topology"]
    if len(comp["L_nH"]) != 4 or len(comp["series"]) != 4:
        raise ValueError("Expected 4-inductor checkpoint")
    L = np.array(comp["L_nH"], dtype=float)
    Q = np.array(comp["Q_L"], dtype=float)
    for index, series in enumerate(comp["series"]):
        if series == "LQP02HV":
            if not (.4 <= L[index] <= 27 and Q[index] == 25):
                raise ValueError("Invalid HV series/Q/inductance")
        elif series == "LQW04":
            if Q[index] != 33 or L[index] <= 0:
                raise ValueError("Invalid LQW04 Q/value (physical range unverified)")
        else:
            raise ValueError("Unapproved series in this checkpoint")
    K = np.eye(4)
    ids = ["L0", "L1", "L2", "L3"]
    order = [ids.index(identifier) for identifier in topo["physical_row"]]
    for (a, b), k in zip(zip(order[:-1], order[1:]), comp["chip_adjacent_k"]):
        if abs(k) > .15 + 1e-10:
            raise ValueError("Chip coupling exceeds RF-F002 bound")
        K[a, b] = K[b, a] = k
    if np.linalg.eigvalsh(K).min() <= 0:
        raise ValueError("Non-positive-definite inductance matrix")
    if len(topo["inductor_edges"]) != 4 or len(topo["IC_VARIABLE_C_edges"]) != 2:
        raise ValueError("Incorrect branch count")
    if len(comp["chip_adjacent_k"]) != 3 or len(order) != 4 or len(set(order)) != 4:
        raise ValueError("Incorrect physical row/coupling count")
    if comp.get("nominal_nonstrong_k") != 0 or comp.get("chip_PCB_k") != 0:
        raise ValueError("Unapproved coupling")
    if comp.get("Q_GJM01") != 80 or comp.get("Q_PCB_C") != 40 or comp.get("IC_VARIABLE_C_Q") != 50:
        raise ValueError("Capacitor Q does not match RF-F002")
    n_lqw = comp["series"].count("LQW04")
    n_hv = comp["series"].count("LQP02HV")
    area = 3*n_lqw + n_hv + 2*(2/3)
    if abs(area - float(data["chip_area_units"])) > 1e-9:
        raise ValueError("Chip area incorrect")
    G = comp["GJM01_pF"]
    P = comp["PCB_PATTERN_C_pF"]
    if len(G) != 2 or any(x <= 0 or x > 100 for x in G) or not .02 <= P <= .2:
        raise ValueError("Fixed capacitance violates constraint")
    inductors = [
        Branch(a, b, v * 1e-9, q)
        for (a, b), v, q in zip(topo["inductor_edges"], L, Q)
    ]
    fixed = (
        [Branch(a, b, v * 1e-12, 80) for (a, b), v in zip(topo["fixed_GJM_edges"], G)]
        + [Branch(*topo["PCB_PATTERN_C_edge"], P * 1e-12, 40)]
    )
    rows = load_bands()
    by_setting = {}
    max_residual = 0.0
    for setting in CASES:
        variable = comp["IC_VARIABLE_C_by_setting_pF"][setting]
        if len(variable) != 2 or any(not (0 <= val <= 1.5 + 1e-10) for val in variable):
            raise ValueError("IC variable C outside RF-F002 range")
        caps = fixed + [
            Branch(a, b, v * 1e-12, 50)
            for (a, b), v in zip(topo["IC_VARIABLE_C_edges"], variable)
        ]
        result = {}
        for region in ["UL", "DL", "H2", "H3"]:
            values = []
            for band in rows:
                if band["case"] != setting or band["region"] != region:
                    continue
                for f in np.linspace(float(band["low_mhz"]), float(band["high_mhz"]), options.points):
                    s = solve(float(f) * 1e6, 5, 1, 3, inductors=inductors,
                              capacitors=caps, coupling=K,
                              source_ohms=50., load_ohms=60-40j)
                    values.append((float(s["il_db"]), float(f)))
                    max_residual = max(max_residual, abs(float(s["power_residual"])))
            if not values:
                raise ValueError("Missing frequency segment")
            result[region] = (max if region in ("UL", "DL") else min)(values)
        by_setting[setting] = result
    il = max(by_setting[c][r][0] for c in CASES for r in ("UL", "DL"))
    h2 = min(by_setting[c]["H2"][0] for c in CASES)
    h3 = min(by_setting[c]["H3"][0] for c in CASES)
    expected = data.get("evaluation")
    if expected:
        tolerance = 1e-3 if options.points < 7001 else 1e-6
        for key, observed in (("worst_IL_db", il), ("min_H2_db", h2), ("min_H3_db", h3)):
            if abs(observed - float(expected[key])) > tolerance:
                raise ValueError(f"Saved {key} does not reproduce: observed {observed}, expected {expected[key]}")
    print(json.dumps({"candidate_id":data["candidate_id"],"points_per_segment":options.points,
                      "worst_IL_db":il,"min_H2_db":h2,"min_H3_db":h3,
                      "max_power_balance_residual_W":max_residual,
                      "by_setting":by_setting,"finite_grid_only":True},indent=2,ensure_ascii=False))


if __name__ == "__main__":
    main()
