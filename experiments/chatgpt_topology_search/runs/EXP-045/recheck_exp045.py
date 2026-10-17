#!/usr/bin/env python3
"""EXP-045 saved candidates: exact RF-T005 S2P and independent 7x7 MNA recheck.
NOT YET EXECUTED in the EXP-045 research run. Runs against immutable main S2P.
Usage: uv run --frozen python experiments/chatgpt_topology_search/runs/EXP-045/recheck_exp045.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "src"), str(HERE.parent / "EXP-043")]
from lpf.constraint_versions import load_constraint
import search_3l as source
import verify_3l as independent

# Fixed caps: PCB Cf0/Cf1, GJM shunt Cp. Cv positions parallel to each.
VARIANT = "exp045_t3l_ppg"
source.CONFIGS[VARIANT] = (
    ("PCB", "PCB", "GJM"), ((3, -1), (0, 1), (1, 2))
)
policy = load_constraint("RF-T005", allow_trial=True)

for name in ("t3l_lowil", "t3l_harmonic_margin"):
    saved = json.loads((HERE / "checkpoints" / (name + ".json")).read_text())
    x = np.asarray(saved["vector"], dtype=float)
    assert len(x) == 26
    assert np.all((x[:3] >= .4) & (x[:3] <= 27))
    assert np.all((x[6:8] >= -.1) & (x[6:8] <= .1))
    assert np.all((x[8:] >= 0) & (x[8:] <= 3))
    ev = source.Evaluator(policy, VARIANT, 301)
    summary = ev.summary(x)
    assert abs(summary["worst_IL_db"] - saved["result"]["worst_IL_db"]) < 1e-8
    assert abs(summary["min_H2_db"] - saved["result"]["min_H2_db"]) < 1e-8
    assert abs(summary["min_H3_db"] - saved["result"]["min_H3_db"]) < 1e-8
    # The existing independent checker expects EXP-043's checkpoint schema;
    # this internal compatibility adapter does not reassign the research ID.
    adapter = {"experiment": "EXP-043", "variant": VARIANT,
               "vector": saved["vector"]}
    mna = independent.verify(adapter, points=3)
    assert mna["PASS"]
    print(json.dumps({"experiment": "EXP-045", "candidate": name,
                      "grid_301": summary, "independent_7x7": mna},
                     ensure_ascii=False, indent=2))
