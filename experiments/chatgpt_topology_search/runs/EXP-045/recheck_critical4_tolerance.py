#!/usr/bin/env python3
"""EXP-045: repeat limited four-frequency RF-T005 tolerance probes.

This script is newly archived; the in-chat JS was executed, but this Python
reproduction MUST NOT be marked as executed until run on a repository checkout.
It intentionally does not claim a full-band or statistical yield result.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from verify_extra_pcb import HERE, ROOT, total_attenuation
from lpf.constraint_versions import load_constraint

CRITICAL = (
    ("B28_DL_IL", "B28", 803.0),
    ("B8_DL_IL", "B8", 960.0),
    ("B13B14_H2", "B13+B14", 1554.0),
    ("B71_H3", "B71", 1989.0),
)
CASE_ORDER = ("B71", "B12", "B28", "B13+B14", "B26", "B8")


def scenario_vector(base: np.ndarray, name: str) -> np.ndarray:
    x = base.copy()
    if name in ("third_PCB_C_minus_1pct", "Cf1_PCB_C_minus_1pct"):
        # Exact electrical identity under the fixed-Q40 circuit model:
        # the third PCB 0.2 pF and Cf1 0.2 pF share nodes (1, 2).
        x[4] *= 0.99
    elif name in ("third_PCB_C_plus_1pct", "Cf1_PCB_C_plus_1pct"):
        x[4] *= 1.01
    elif name == "Cp_GJM_minus_1pct":
        x[5] *= 0.99
    elif name == "Cp_GJM_plus_1pct":
        x[5] *= 1.01
    elif name == "Cf0_PCB_C_minus_1pct":
        x[3] *= 0.99
    elif name == "Cf0_PCB_C_plus_1pct":
        x[3] *= 1.01
    elif name == "k_L0_Ls_minus_0p01":
        x[6] -= 0.01
    elif name == "k_Ls_L1_plus_0p01":
        x[7] += 0.01
    elif name == "k_Ls_L1_minus_0p01":
        x[7] -= 0.01
    elif name == "all_Cv_plus_1pct":
        x[8:] = np.minimum(3.0, x[8:] * 1.01)
    elif name == "all_Cv_minus_1pct":
        x[8:] *= 0.99
    elif name != "baseline":
        raise ValueError(f"Unknown scenario: {name}")
    return x


def main() -> None:
    policy = load_constraint("RF-T005", root=ROOT, allow_trial=True)
    checkpoint = json.loads(
        (HERE / "checkpoints/t3l_extra_pcb_out_0p2_prelim.json").read_text(encoding="utf-8")
    )
    base = np.asarray(checkpoint["vector"], dtype=float)
    cases = (
        "baseline", "third_PCB_C_plus_1pct", "third_PCB_C_minus_1pct",
        "Cf1_PCB_C_plus_1pct", "Cf1_PCB_C_minus_1pct",
        "Cp_GJM_plus_1pct", "Cp_GJM_minus_1pct",
        "Cf0_PCB_C_plus_1pct", "Cf0_PCB_C_minus_1pct",
        "k_L0_Ls_minus_0p01", "k_Ls_L1_plus_0p01",
        "k_Ls_L1_minus_0p01", "all_Cv_plus_1pct", "all_Cv_minus_1pct",
    )
    results = []
    for name in cases:
        x = scenario_vector(base, name)
        values = {
            key: float(total_attenuation(
                policy, x, CASE_ORDER.index(band), freq_mhz
            )[0])
            for key, band, freq_mhz in CRITICAL
        }
        values["minimum_critical_stop_margin_dB"] = min(
            values["B13B14_H2"], values["B71_H3"]
        ) - 30.0
        results.append({"scenario": name, **values})
    base_observed = results[0]
    expected = {
        "B28_DL_IL": 0.8951800090647889,
        "B8_DL_IL": 0.8944031897229465,
        "B13B14_H2": 30.00800000006535,
        "B71_H3": 30.008000001829046,
    }
    for key, value in expected.items():
        if abs(base_observed[key] - value) >= 1e-7:
            raise AssertionError(f"Baseline mismatch: {key}")
    print(json.dumps({
        "experiment_id": "EXP-045", "constraint_id": "RF-T005",
        "phase": "Phase 2", "scope": "four critical points only, no full band",
        "frequency_mhz": [v[2] for v in CRITICAL],
        "method": "original fixed S2P via lpf.port_parasitics and reduced nodal Y",
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
