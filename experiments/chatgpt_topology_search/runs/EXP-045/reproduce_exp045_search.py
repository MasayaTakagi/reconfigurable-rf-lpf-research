#!/usr/bin/env python3
"""EXP-045 executable reproduction of the in-chat coordinate-pattern search.
THIS FILE IS A RECONSTRUCTION AND HAS NOT BEEN EXECUTED BY THE CURRENT RUN.
The independent full-mesh + branch-MNA recheck is recheck_exp045.py.
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

# Same graph, loss models and physical row as EXP-043 local 26D checkpoint:
source.CONFIGS["exp045_t3l_ppg"] = (
    ("PCB", "PCB", "GJM"), ((3, -1), (0, 1), (1, 2))
)
policy = load_constraint("RF-T005", allow_trial=True)
ev = source.Evaluator(policy, "exp045_t3l_ppg", 5)
bounds = ev.bounds
steps_initial = np.array(
    [.2, .3, .2, .015, .015, .08, .01, .01] + [.08] * 18, float
)
assert bounds.shape == (26, 2)

def score(x, target):
    response = ev.il(x)
    worst = np.max(response[ev.role == 0])
    h2 = np.min(response[ev.role == 1])
    h3 = np.min(response[ev.role == 2])
    violation = max(0., target-h2, target-h3)
    return float(worst + 60.*violation**2 + .1*violation)

def pattern(initial, target):
    x = np.array(initial, float).copy()
    steps = steps_initial.copy()
    current = score(x, target)
    accepted = 0
    for _ in range(10):
        changed = False
        for j in range(len(x)):
            old = x[j]
            trial_best_value = old
            trial_best_merit = current
            for direction in (-1., 1.):
                trial_value = np.clip(old + direction*steps[j],
                                      bounds[j, 0], bounds[j, 1])
                if abs(trial_value-old) < 1e-12:
                    continue
                x[j] = trial_value
                new_merit = score(x, target)
                if new_merit < trial_best_merit - 1e-10:
                    trial_best_merit = new_merit
                    trial_best_value = trial_value
            x[j] = trial_best_value
            if trial_best_merit < current - 1e-10:
                current = trial_best_merit
                accepted += 1
                changed = True
        if not changed:
            steps *= .55
        if np.max(steps[:3]) < .002 and np.max(steps[8:]) < .0005:
            break
    return x, current, accepted

base = json.loads((HERE.parent / "EXP-043" / "checkpoints" /
                  "gjm_cp_local_H30p0032.json").read_text())["vector"]
for target, filename in ((30.001,"t3l_lowil"),(30.015,"t3l_harmonic_margin")):
    x, merit, accepted = pattern(base, target)
    saved = json.loads((HERE / "checkpoints" /
                        (filename + ".json")).read_text())
    diff = np.max(np.abs(x - np.array(saved["vector"])))
    print(json.dumps({"candidate": filename, "target": target,
                      "coordinate_accepts": accepted, "merit": merit,
                      "max_abs_parameter_delta_to_saved": float(diff),
                      "recomputed_grid5": ev.summary(x)},
                     ensure_ascii=False, indent=2))
