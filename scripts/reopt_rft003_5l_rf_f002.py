#!/usr/bin/env python3
"""Re-synthesize a historical RF-T003 five-L seed under formal RF-F002."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))

from full_lpf import FullLPFProblem  # noqa: E402
from p4_batch import load_constraint  # noqa: E402
from instantiate_graph import check_graph  # noqa: E402
from lpf.constraint_versions import constraint_fingerprint  # noqa: E402
from lpf.evaluate import CASES  # noqa: E402

DEFAULT_SEED = ROOT / "data/validation/rft003_20261013/five_L_cost6p33_candidates.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _git_status():
    try:
        return subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT,
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _runtime_snapshot():
    memory = psutil.virtual_memory()
    model = None
    try:
        model = next((line.split(":", 1)[1].strip()
                      for line in Path("/proc/cpuinfo").read_text().splitlines()
                      if line.lower().startswith("model name")), None)
    except OSError:
        pass
    config = np.__config__.show(mode="dicts")
    dependencies = config.get("Build Dependencies", {}) if isinstance(config, dict) else {}
    blas_lapack = {}
    for name in ("blas", "lapack"):
        backend = dependencies.get(name, {}) if isinstance(dependencies, dict) else {}
        if isinstance(backend, dict):
            blas_lapack[name] = {key: backend[key] for key in ("name", "version", "has ilp64")
                                 if key in backend}
    return {
        "blas_lapack": blas_lapack,
        "cpu_model": model,
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "physical_cpu_count": psutil.cpu_count(logical=False),
        "memory_total_bytes": memory.total,
        "memory_available_bytes": memory.available,
    }


def _construct_seed(candidate):
    circuit = candidate["circuit"]
    edges = []
    edges.extend((int(a), int(b), str(kind))
                 for (a, b), kind in zip(circuit["L_edges"], circuit["L_series"]))
    edges.extend((int(cap["edge"][0]), int(cap["edge"][1]), str(cap["kind"]))
                 for cap in circuit["fixed_capacitors"])
    graph = (max(max(a, b) for a, b, _ in edges) + 1, tuple(edges))
    variable_edges = tuple(tuple(map(int, edge)) for edge in circuit["variable_C_edges"])
    variable_layout = {
        "edges": variable_edges,
        "roles": tuple(None if 0 in edge else "bridge" for edge in variable_edges),
    }

    policy = load_constraint("RF-F002")
    old_couplings = np.asarray(circuit["adjacent_k"], dtype=float)
    coupling_limit = float(policy["chip_inductor_placement"]["strong_abs_k_max"])
    scale = min(1.0, coupling_limit / max(np.max(np.abs(old_couplings)), 1e-12))
    clipped_couplings = old_couplings * scale
    physical_order = tuple(map(int, circuit["physical_chip_row"]))
    initial_coupling = np.eye(len(circuit["L_edges"]))
    for index, value in enumerate(clipped_couplings):
        a, b = physical_order[index], physical_order[index + 1]
        initial_coupling[a, b] = initial_coupling[b, a] = float(value)

    component_values = list(map(float, circuit["L_nH"]))
    component_values.extend(float(cap["C_pf"]) for cap in circuit["fixed_capacitors"])
    variable_values = []
    clipping_report = []
    for case in CASES:
        row = list(map(float, circuit["variable_C_by_case_pf"][case]))
        clipped = [min(1.5, max(0.0, value)) for value in row]
        if clipped != row:
            clipping_report.append({"case": case, "seed_pf": row, "rf_f002_start_pf": clipped})
        variable_values.extend(clipped)
    component_values.extend(variable_values)
    problem = FullLPFProblem(
        graph, variable_layout, initial_coupling,
        resolved_policy=policy, physical_order=physical_order,
        passband_points=9, stopband_points=9,
    )
    vector = problem.initial_vector(np.asarray(component_values, dtype=float),
                                    coupling_values=clipped_couplings)
    return problem, vector, policy, scale, clipping_report


def run(args):
    source = Path(args.seed_json)
    payload = json.loads(source.read_text(encoding="utf-8"))
    candidates = {row["name"]: row for row in payload["selected_candidates"]}
    if args.candidate_name not in candidates:
        raise ValueError(f"Candidate {args.candidate_name!r} not found in {source}")
    resources_before = _runtime_snapshot()
    wall_started = time.monotonic()
    candidate = candidates[args.candidate_name]
    problem, initial, policy, coupling_scale, clipping_report = _construct_seed(candidate)
    optimized = problem.optimize(
        initial, harmonic_targets=(30.0, 35.0), maxiter=args.maxiter,
        ftol=args.ftol,
    )
    wall_elapsed = time.monotonic() - wall_started
    graph_types = [edge[2] for edge in problem.graph[1]]
    area_value = check_graph(problem.graph, require_explicit_series=True)
    area = {
        "chip_area_cost": area_value,
        "component_counts": {kind: graph_types.count(kind) for kind in sorted(set(graph_types))},
        "cost_unit": "LQP02_package_footprint",
        "is_hard_constraint": False,
    }
    output = {
        **optimized,
        "experiment_id": "RF-F002-RFT003-5L-RESYNTHESIS-01",
        "source_trial": "RF-T003 historical five-L seed",
        "source_trial_candidate": args.candidate_name,
        "source_trial_constraint": payload.get("constraint_id"),
        "source_trial_commit": payload.get("source_main_sha"),
        "source_seed_file": str(source.relative_to(ROOT) if source.is_relative_to(ROOT) else source),
        "source_seed_file_sha256": _sha256(source),
        "source_formal_results_reused_as_seed_only": True,
        "constraint_id": "RF-F002",
        "constraint_status": "formal",
        "constraint_effective_sha256": constraint_fingerprint(policy),
        "bands_csv_sha256": _sha256(ROOT / "data/bands.csv"),
        "git_commit_sha": _git_sha(),
        "git_worktree_status": _git_status(),
        "runtime_source_sha256": _sha256(Path(__file__)),
        "solver_source_sha256": _sha256(ROOT / "experiments/matching_limit/full_lpf.py"),
        "source_policy_is_not_current_formal_policy": True,
        "seed_transformations": {
            "input_variable_cap_branch_edges": [list(edge) for edge in problem.variable_layout["edges"]],
            "variable_cap_clipping_to_rf_f002_max_1p5_pf": clipping_report,
            "initial_chip_neighbor_coupling_scale_to_rf_f002_limit_0p15": coupling_scale,
            "initial_couplings_are_only_initial_values": True,
            "fixed_component_values_are_reoptimized": True,
            "six_setting_variable_capacitances_are_jointly_reoptimized": True,
        },
        "area_report": area,
        "numeric_environment": {
            "python": platform.python_version(),
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
            "numpy_blas_lapack": resources_before["blas_lapack"],
            "threads": {name: os.environ.get(name) for name in
                        ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "resource_measurement": {
            "before": resources_before,
            "after": _runtime_snapshot(),
            "process_peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                                           * (1024 if platform.system() == "Linux" else 1)),
            "wall_elapsed_seconds": round(wall_elapsed, 6),
        },
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output_path.relative_to(ROOT)),
        "source_trial_candidate": args.candidate_name,
        "constraint_id": "RF-F002",
        "status": optimized["best_found_category"],
        "converged": optimized["converged"],
        "mandatory_30db_met": optimized["mandatory_30db_met_on_dense_grid"],
        "nominal_35db_met": optimized["nominal_35db_met_on_dense_grid"],
        "worst_il_db": optimized["worst_il_db"],
        "min_h2_db": optimized["min_h2_db"],
        "min_h3_db": optimized["min_h3_db"],
        "chip_area_cost": area["chip_area_cost"],
        "elapsed_seconds": optimized["elapsed_seconds"],
        "wall_elapsed_seconds": round(wall_elapsed, 3),
    }, indent=2))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-json", default=str(DEFAULT_SEED))
    parser.add_argument("--candidate-name", default="LOW_IL_30p01")
    parser.add_argument("--maxiter", type=int, default=60)
    parser.add_argument("--ftol", type=float, default=1e-8)
    parser.add_argument("--output", default="results/full-lpf/rf-f002-rft003-5l.json")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
