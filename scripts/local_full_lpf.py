#!/usr/bin/env python3
"""Resource-gated, resumable local manager for bounded RF-F002 full-LPF batches.

Unlike local_p4.py, this runner handles only the full_lpf epigraph optimizer.
Each start is an atomic task boundary: an interrupted start is retried from its
recorded initial vector, while completed starts are never repeated on resume.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import psutil

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts" / "full_lpf_worker.py"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))
from full_lpf import FullLPFProblem, _coupling_matrix  # noqa: E402
from lpf.constraint_versions import constraint_fingerprint, load_constraint  # noqa: E402
from lpf.validation import validate_inductor_coupling  # noqa: E402

SOURCE_PATHS = (
    "scripts/local_full_lpf.py",
    "scripts/full_lpf_worker.py",
    "experiments/matching_limit/full_lpf.py",
    "experiments/matching_limit/p4_batch.py",
    "experiments/matching_limit/instantiate_graph.py",
    "src/lpf/circuit.py",
    "src/lpf/constraint_versions.py",
    "src/lpf/constraints.py",
    "src/lpf/evaluate.py",
    "src/lpf/independent.py",
    "src/lpf/validation.py",
    "data/bands.csv",
    "data/constraints/formal/RF-F002.json",
    "pyproject.toml",
    "uv.lock",
    "data/constraints/registry.json",
)
MAX_WORKERS = 2
MAX_TASKS_PER_BATCH = 20
MAX_BATCH_SECONDS = 3600.0
MAX_TASK_SECONDS = 1800.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", suffix=".tmp",
                                     delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True,
                  allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _git_info() -> dict:
    def run(*args):
        try:
            return subprocess.check_output(args, cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return "unavailable"
    return {"commit": run("git", "rev-parse", "HEAD"),
            "working_tree_dirty": bool(run("git", "status", "--porcelain"))}


def _source_hashes() -> dict:
    return {name: _sha256_file(ROOT / name) for name in SOURCE_PATHS}


def _normalize_edge(edge):
    if not isinstance(edge, (list, tuple)) or len(edge) != 3:
        raise ValueError("Graph edges must be [node_a, node_b, component_type]")
    a, b, kind = edge
    if not isinstance(a, int) or not isinstance(b, int) or a == b or a < 0 or b < 0:
        raise ValueError(f"Invalid graph endpoints: {edge!r}")
    if not isinstance(kind, str) or not kind:
        raise ValueError(f"Invalid component type in edge: {edge!r}")
    return [a, b, kind]


def _topology_fingerprint(task: dict) -> str:
    nodes, edge_rows = task["graph"]
    edges = [_normalize_edge(edge) for edge in edge_rows]
    inductor_positions = [i for i, edge in enumerate(edges)
                          if edge[2] not in {"GJM01", "PCB_PATTERN_C"}]
    physical_order = task["physical_order"]
    physical_edges = []
    for position in physical_order:
        if not isinstance(position, int) or not 0 <= position < len(inductor_positions):
            raise ValueError("physical_order must index the inductor-only branch list")
        a, b, kind = edges[inductor_positions[position]]
        physical_edges.append([min(a, b), max(a, b), kind])
    layout = task["variable_layout"]
    var_edges = layout["edges"]
    roles = layout["roles"]
    if len(var_edges) != len(roles):
        raise ValueError("variable layout edges and roles must have matching lengths")
    variables = [[min(int(a), int(b)), max(int(a), int(b)), role]
                 for (a, b), role in zip(var_edges, roles)]
    variables.sort(key=lambda row: (row[0], row[1], "" if row[2] is None else str(row[2])))
    topology = {
        "nodes": int(nodes),
        "fixed_edges": sorted([[min(a, b), max(a, b), kind] for a, b, kind in edges]),
        "variable_edges_and_roles": variables,
        "physical_order_edges": physical_edges,
    }
    return _sha256_bytes(_canonical_bytes(topology))


def _start_fingerprint(task: dict) -> str:
    nodes, edge_rows = task["graph"]
    edges = [_normalize_edge(edge) for edge in edge_rows]
    fixed_values = task["initial_base_values"][:len(edges)]
    fixed = sorted([[min(a, b), max(a, b), kind, float(value)]
                    for (a, b, kind), value in zip(edges, fixed_values)])
    layout = task["variable_layout"]
    variable_count = len(layout["edges"])
    variable_values = task["initial_base_values"][len(edges):]
    by_variable = []
    for index, ((a, b), role) in enumerate(zip(layout["edges"], layout["roles"])):
        values = [float(variable_values[setting * variable_count + index])
                  for setting in range(6)]
        by_variable.append([min(a, b), max(a, b), role, values])
    by_variable.sort(key=lambda row: (row[0], row[1], "" if row[2] is None else str(row[2])))

    inductor_edges = [edge for edge in edges if edge[2] not in {"GJM01", "PCB_PATTERN_C"}]
    order = task["physical_order"]
    matrix = [list(row) for row in task["initial_coupling"]]
    coupling_values = task.get("initial_coupling_values")
    # Reconstruct the actual allowed initial coupling slots, not arbitrary all-pair k values.
    chip_types = {"LQP01", "LQP02HV", "LQP02HQ", "LQW04"}
    chips = [index for index in order if inductor_edges[index][2] in chip_types]
    pcbs = [index for index, edge in enumerate(inductor_edges) if edge[2] == "PCB_L"]
    slots = [(a, b) for a, b in zip(chips, chips[1:])]
    slots.extend((a, b) for position, a in enumerate(pcbs) for b in pcbs[position + 1:])
    if coupling_values is not None:
        for (a, b), value in zip(slots, coupling_values):
            matrix[a][b] = matrix[b][a] = float(value)
    coupling = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            coupling.append([i, j, float(matrix[order[i]][order[j]])])
    signature = {
        "fixed_component_values": fixed,
        "variable_values_by_setting": by_variable,
        "physical_order_edges": [[min(inductor_edges[index][0], inductor_edges[index][1]),
                                  max(inductor_edges[index][0], inductor_edges[index][1]),
                                  inductor_edges[index][2]] for index in order],
        "physical_order_coupling_values": coupling,
    }
    return _sha256_bytes(_canonical_bytes(signature))


def _prepare_config(raw: bytes) -> tuple[dict, list[dict]]:
    config = json.loads(raw)
    if config.get("constraint_id") != "RF-F002":
        raise ValueError("The full-LPF manager accepts formal RF-F002 only")
    if config.get("objective", "full_lpf") != "full_lpf":
        raise ValueError("This manager is isolated from matching_only; objective must be full_lpf")
    optimization = config.get("optimization", {})
    targets = optimization.get("harmonic_targets_db", [30.0, 35.0])
    if not isinstance(targets, list) or not targets or any(float(x) < 30.0 for x in targets):
        raise ValueError("harmonic_targets_db must contain only targets >=30 dB")
    if sorted(set(map(float, targets))) != list(map(float, targets)):
        raise ValueError("harmonic_targets_db must be strictly increasing")
    settings = {
        "harmonic_targets_db": list(map(float, targets)),
        "maxiter_per_stage": int(optimization.get("maxiter_per_stage", 120)),
        "ftol": float(optimization.get("ftol", 1e-8)),
        "passband_points": int(optimization.get("passband_points", 9)),
        "stopband_points": int(optimization.get("stopband_points", 9)),
        "max_attempts": int(optimization.get("max_attempts", 2)),
    }
    if not 1 <= settings["maxiter_per_stage"] <= 1000:
        raise ValueError("maxiter_per_stage must be in [1, 1000]")
    if not 1e-12 <= settings["ftol"] <= 1e-2:
        raise ValueError("ftol must be in [1e-12, 1e-2]")
    if not 2 <= settings["passband_points"] <= 101 or not 2 <= settings["stopband_points"] <= 101:
        raise ValueError("Optimization grid points must be in [2, 101] per segment")
    if not 1 <= settings["max_attempts"] <= 5:
        raise ValueError("max_attempts must be in [1, 5]")
    tasks_in = config.get("tasks")
    if not isinstance(tasks_in, list) or not tasks_in:
        raise ValueError("A non-empty tasks array is required")
    if len(tasks_in) > 10000:
        raise ValueError("Refusing a plan with more than 10000 task starts")
    policy = load_constraint("RF-F002")
    constraint_sha = constraint_fingerprint(policy)
    if config.get("effective_constraint_sha256", constraint_sha) != constraint_sha:
        raise ValueError("Config RF-F002 effective constraint fingerprint does not match registry")
    tasks = []
    seen_starts = set()
    topology_hashes = set()
    max_variables = int(policy["components"]["IC_VARIABLE_C"]["max_branches_principle"])
    for task_in in tasks_in:
        if not isinstance(task_in, dict):
            raise ValueError("Each task must be a JSON object")
        task = dict(task_in)
        if "seed_label" not in task:
            task["seed_label"] = "unnamed"
        graph = task.get("graph")
        if not isinstance(graph, list) or len(graph) != 2:
            raise ValueError("Each task graph must be [node_count, edge_list]")
        nodes = int(graph[0])
        edges = [_normalize_edge(edge) for edge in graph[1]]
        if not 2 <= nodes <= 32 or not 1 <= len(edges) <= 64:
            raise ValueError("Graph is outside bounded manager limits (2..32 nodes, 1..64 fixed branches)")
        if any(max(a, b) >= nodes for a, b, _ in edges):
            raise ValueError("Fixed graph edge references a node outside node_count")
        task["graph"] = [nodes, edges]
        layout = task.get("variable_layout", {})
        var_edges = layout.get("edges", [])
        roles = layout.get("roles", [None] * len(var_edges))
        if len(var_edges) > max_variables or len(var_edges) != len(roles):
            raise ValueError("RF-F002 permits at most two independent variable-C branches")
        normalized_var_edges = []
        for edge in var_edges:
            if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                raise ValueError("Variable-C edges must be [node_a, node_b]")
            a, b = map(int, edge)
            if a == b or min(a, b) < 0 or max(a, b) >= nodes:
                raise ValueError(f"Invalid variable-C edge {edge!r}")
            normalized_var_edges.append([a, b])
        if any(role not in (None, "shunt_to_ground", "bridge", "series") for role in roles):
            raise ValueError("Unknown variable-C branch role")
        task["variable_layout"] = {"edges": normalized_var_edges, "roles": list(roles)}
        types = [edge[2] for edge in edges]
        allowed_types = {"LQP01", "LQP02HV", "LQP02HQ", "LQW04",
                         "PCB_L", "GJM01", "PCB_PATTERN_C"}
        unknown_types = sorted(set(types) - allowed_types)
        if unknown_types:
            raise ValueError(f"Unsupported RF component types: {unknown_types}")
        if types.count("PCB_L") > int(policy["components"]["PCB_L"]["max_count_principle"]):
            raise ValueError("PCB_L count exceeds RF-F002 limit")
        if types.count("PCB_PATTERN_C") > int(policy["components"]["PCB_PATTERN_C"]["max_count"]):
            raise ValueError("PCB_PATTERN_C count exceeds RF-F002 limit")
        inductor_count = sum(kind not in {"GJM01", "PCB_PATTERN_C"} for kind in types)
        if inductor_count < 1:
            raise ValueError("A full-LPF task must include at least one inductor")
        physical_order = task.get("physical_order", list(range(inductor_count)))
        if sorted(physical_order) != list(range(inductor_count)):
            raise ValueError("physical_order must be a permutation of inductor branch indices")
        task["physical_order"] = physical_order
        expected_base_values = len(edges) + 6 * len(normalized_var_edges)
        base_values = task.get("initial_base_values")
        if not isinstance(base_values, list) or len(base_values) != expected_base_values:
            raise ValueError(f"initial_base_values must have {expected_base_values} values")
        if any(not isinstance(x, (int, float)) or not (-1e9 < float(x) < 1e9) for x in base_values):
            raise ValueError("initial_base_values contain invalid or non-finite numbers")
        task["initial_base_values"] = list(map(float, base_values))
        coupling = task.get("initial_coupling")
        if not isinstance(coupling, list) or len(coupling) != inductor_count or any(
                not isinstance(row, list) or len(row) != inductor_count for row in coupling):
            raise ValueError("initial_coupling must be a square matrix matching the inductor count")
        if any(not isinstance(x, (int, float)) or not (-2 < float(x) < 2)
               for row in coupling for x in row):
            raise ValueError("initial_coupling contains invalid values")
        task["initial_coupling"] = [list(map(float, row)) for row in coupling]
        if "initial_coupling_values" in task:
            values = task["initial_coupling_values"]
            chip_count = sum(kind in {"LQP01", "LQP02HV", "LQP02HQ", "LQW04"}
                             for kind in types)
            pcb_count = sum(kind == "PCB_L" for kind in types)
            expected_slots = max(0, chip_count - 1) + pcb_count * max(0, pcb_count - 1) // 2
            if not isinstance(values, list) or len(values) != expected_slots:
                raise ValueError("initial_coupling_values length does not match allowed coupling slots")
            task["initial_coupling_values"] = list(map(float, values))
        graph_tuple = (nodes, tuple(tuple(edge) for edge in edges))
        layout_tuple = {"edges": tuple(tuple(edge) for edge in normalized_var_edges),
                        "roles": tuple(roles)}
        problem = FullLPFProblem(
            graph_tuple, layout_tuple, task["initial_coupling"],
            constraint_id="RF-F002", passband_points=2, stopband_points=2,
            physical_order=task["physical_order"], resolved_policy=policy,
        )
        bounds = problem.base_bounds
        if any(float(value) < low - 1e-12 or float(value) > high + 1e-12
               for value, (low, high) in zip(task["initial_base_values"], bounds)):
            raise ValueError("Initial component/capacitance values are outside RF-F002 bounds")
        coefficients = task.get("initial_coupling_values", problem.initial_coefficients.tolist())
        if any(float(value) < low - 1e-12 or float(value) > high + 1e-12
               for value, (low, high) in zip(coefficients, problem.coupling_bounds)):
            raise ValueError("Initial coupling values are outside RF-F002 bounds")
        trial_matrix = _coupling_matrix(problem.initial_coupling, problem.slots, coefficients)
        validate_inductor_coupling(
            problem.types, [1e-9] * len(problem.types), trial_matrix,
            physical_order=problem.physical_order, resolved_policy=policy,
        )
        topology_hash = _topology_fingerprint(task)
        task_hash = _sha256_bytes(_canonical_bytes(task))
        start_hash = _start_fingerprint(task)
        start_key = (topology_hash, start_hash)
        if start_key in seen_starts:
            raise ValueError("Duplicate topology/start after canonical topology deduplication")
        seen_starts.add(start_key)
        topology_hashes.add(topology_hash)
        stable_id = _sha256_bytes(_canonical_bytes({"topology": topology_hash,
                                                    "start": start_hash}))
        tasks.append({
            "task_id": stable_id[:24],
            "task_config_sha256": task_hash,
            "start_sha256": start_hash,
            "topology_sha256": topology_hash,
            "task": task,
        })
    prepared = dict(config)
    prepared["objective"] = "full_lpf"
    prepared["optimization"] = settings
    prepared["effective_constraint_sha256"] = constraint_sha
    prepared["tasks"] = [row["task"] for row in tasks]
    return prepared, tasks


def plan(config_path: Path, run_dir: Path) -> dict:
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"Run directory is not empty: {run_dir}")
    raw = config_path.read_bytes()
    config, tasks = _prepare_config(raw)
    source_hashes = _source_hashes()
    resolved_policy = load_constraint("RF-F002")
    run_dir.mkdir(parents=True, exist_ok=True)
    task_dir = run_dir / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "results").mkdir()
    (run_dir / "logs").mkdir()
    (run_dir / "config.json").write_bytes(raw)
    for row in tasks:
        _atomic_json(task_dir / f"{row['task_id']}.json", {
            **row,
            "optimization": config["optimization"],
        })
    manifest = {
        "schema_version": 1,
        "run_type": "bounded_resumable_full_lpf_only",
        "phase": "Phase 2",
        "objective": "full_lpf",
        "constraint_id": "RF-F002",
        "effective_constraint_sha256": constraint_fingerprint(resolved_policy),
        "constraint_file_sha256": _sha256_file(ROOT / "data/constraints/formal/RF-F002.json"),
        "bands_sha256": _sha256_file(ROOT / "data/bands.csv"),
        "config_sha256": _sha256_bytes(raw),
        "source_hashes": source_hashes,
        "git": _git_info(),
        "planned_at": _utc_now(),
        "uv_lock_sha256": _sha256_file(ROOT / "uv.lock"),
        "numeric_environment": {
            "python": sys.version.split()[0],
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
            "cpu_model": next((line.split(":", 1)[1].strip()
                                for line in Path("/proc/cpuinfo").read_text().splitlines()
                                if line.lower().startswith("model name")), "unavailable"),
            "logical_cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory_total_bytes": psutil.virtual_memory().total,
            "memory_available_bytes_at_plan": psutil.virtual_memory().available,
            "worker_blas_threads": 1,
        },
        "task_count": len(tasks),
        "unique_topology_count": len({row["topology_sha256"] for row in tasks}),
        "task_ids": [row["task_id"] for row in tasks],
        "optimization": config["optimization"],
        "limitations": [
            "Planning does not execute or validate an optimization.",
            "Each task is one bounded local SLSQP start; no global-optimum claim.",
            "Dense validation is a finite numerical grid, not a continuous-band proof.",
            "Physical SRF, Q(f), parasitic, EM, tolerance, coupling-layout validation is separate.",
        ],
    }
    _atomic_json(run_dir / "manifest.json", manifest)
    status = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "run_type": "bounded_resumable_full_lpf_only",
        "state": "planned",
        "manifest_sha256": _sha256_file(run_dir / "manifest.json"),
        "config_sha256": manifest["config_sha256"],
        "source_hashes": source_hashes,
        "invocation_count": 0,
        "tasks": [{
            "task_id": row["task_id"],
            "task_config_sha256": row["task_config_sha256"],
            "topology_sha256": row["topology_sha256"],
            "start_sha256": row["start_sha256"],
            "state": "pending",
            "attempts": 0,
            "result_path": f"results/{row['task_id']}.json",
        } for row in tasks],
        "last_updated": _utc_now(),
    }
    _atomic_json(run_dir / "status.json", status)
    return {"run_dir": str(run_dir), "task_count": len(tasks),
            "unique_topology_count": manifest["unique_topology_count"],
            "config_sha256": manifest["config_sha256"]}


def _load_and_verify_run(run_dir: Path):
    manifest_path, status_path, config_path = (run_dir / "manifest.json",
                                               run_dir / "status.json",
                                               run_dir / "config.json")
    if not (manifest_path.is_file() and status_path.is_file() and config_path.is_file()):
        raise FileNotFoundError("Run directory must first be created by the plan command")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    raw = config_path.read_bytes()
    config, tasks = _prepare_config(raw)
    if _sha256_bytes(raw) != manifest["config_sha256"] or status["config_sha256"] != manifest["config_sha256"]:
        raise ValueError("Resume refused: configuration hash differs from the immutable plan")
    current_sources = _source_hashes()
    if current_sources != manifest["source_hashes"] or status["source_hashes"] != current_sources:
        raise ValueError("Resume refused: optimizer, RF model, grid, or manager source hashes changed")
    if _sha256_file(manifest_path) != status["manifest_sha256"]:
        raise ValueError("Resume refused: run manifest was edited after planning")
    if len(tasks) != len(status["tasks"]) or [row["task_id"] for row in tasks] != [
            row["task_id"] for row in status["tasks"]]:
        raise ValueError("Resume refused: planned task set does not match checkpoint")
    for planned, checkpoint in zip(tasks, status["tasks"]):
        for key in ("task_config_sha256", "topology_sha256", "start_sha256"):
            if planned[key] != checkpoint.get(key):
                raise ValueError(f"Resume refused: checkpoint {key} mismatch for {planned['task_id']}")
        if checkpoint.get("result_path") != f"results/{planned['task_id']}.json":
            raise ValueError(f"Resume refused: result path mismatch for {planned['task_id']}")
    return manifest, status, config, tasks


def _valid_result(path: Path, task_record: dict) -> dict | None:
    if not path.is_file():
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (result.get("task_id") != task_record["task_id"] or
            result.get("task_config_sha256") != task_record["task_config_sha256"] or
            result.get("start_sha256") != task_record["start_sha256"] or
            result.get("worker_status") != "completed"):
        return None
    return result


def _summary(status: dict) -> dict:
    counts = {state: sum(row["state"] == state for row in status["tasks"])
              for state in ("pending", "running", "completed", "failed")}
    return {"run_id": status["run_id"], "state": status["state"],
            "invocation_count": status["invocation_count"],
            "task_counts": counts, "total_tasks": len(status["tasks"]),
            "last_updated": status["last_updated"]}


def _acquire_lock(run_dir: Path):
    lock = run_dir / ".manager.lock"
    stream = lock.open("a+")
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        stream.close()
        raise RuntimeError(f"Another manager holds the OS lock: {lock}") from error
    stream.seek(0)
    stream.truncate()
    json.dump({"pid": os.getpid(), "started_at": _utc_now()}, stream)
    stream.flush()
    os.fsync(stream.fileno())
    return stream


def _release_lock(stream) -> None:
    if stream is None or stream.closed:
        return
    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    stream.close()


def _assert_no_active_workers(run_dir: Path, status: dict | None = None) -> None:
    if status is not None:
        for record in status.get("tasks", []):
            pid = record.get("worker_pid")
            if record.get("state") != "running" or not isinstance(pid, int):
                continue
            try:
                process = psutil.Process(pid)
                command = " ".join(process.cmdline())
                if process.is_running() and Path(WORKER).name in command:
                    raise RuntimeError(
                        f"Recorded full-LPF worker PID {pid} is still active; wait before resume"
                    )
            except psutil.NoSuchProcess:
                pass
    for lock_path in sorted((run_dir / "locks").glob("*.lock")):
        stream = lock_path.open("a+")
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            stream.close()
            raise RuntimeError(
                f"A worker still holds {lock_path}; do not delete lock files or resume concurrently"
            ) from error
        else:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            stream.close()


def _reserve_worker_lock(lock_path: Path, task_id: str):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    stream = lock_path.open("a+")
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        stream.close()
        raise RuntimeError(f"Task worker lock is already held: {lock_path}") from error
    stream.seek(0)
    stream.truncate()
    json.dump({"manager_pid": os.getpid(), "task_id": task_id,
               "reserved_at": _utc_now()}, stream)
    stream.flush()
    os.fsync(stream.fileno())
    return stream


def _terminate_workers(running: dict) -> None:
    for entry in running.values():
        if entry["process"].poll() is None:
            entry["process"].terminate()
    deadline = time.monotonic() + 3.0
    for entry in running.values():
        process = entry["process"]
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def run_batch(run_dir: Path, *, workers=2, max_runtime_seconds=900.0,
              max_tasks=4, task_timeout_seconds=900.0, min_free_mib=1536.0,
              resume=False) -> dict:
    if workers not in (1, 2) or workers > MAX_WORKERS:
        raise ValueError(f"workers must be 1 or 2 (hard cap {MAX_WORKERS})")
    if not 0 < max_runtime_seconds <= MAX_BATCH_SECONDS:
        raise ValueError(f"max_runtime_seconds must be in (0, {MAX_BATCH_SECONDS}]")
    if not 1 <= max_tasks <= MAX_TASKS_PER_BATCH:
        raise ValueError(f"max_tasks per invocation must be in [1, {MAX_TASKS_PER_BATCH}]")
    if not 0 < task_timeout_seconds <= MAX_TASK_SECONDS:
        raise ValueError(f"task timeout must be in (0, {MAX_TASK_SECONDS}]")
    if min_free_mib < 256:
        raise ValueError("RAM gate cannot be lowered below 256 MiB")
    manifest, status, config, tasks = _load_and_verify_run(run_dir)
    if status["invocation_count"] and not resume:
        raise ValueError("Run has already been invoked; pass --resume to continue safely")
    if not status["invocation_count"] and resume:
        raise ValueError("Cannot resume a run that has not been invoked")
    manager_lock = _acquire_lock(run_dir)
    try:
        manifest, status, config, tasks = _load_and_verify_run(run_dir)
        if status["invocation_count"] and not resume:
            raise ValueError("Run has already been invoked; pass --resume to continue safely")
        if not status["invocation_count"] and resume:
            raise ValueError("Cannot resume a run that has not been invoked")
    except Exception:
        _release_lock(manager_lock)
        raise
    started = time.monotonic()
    launched_this_batch = 0
    running = {}
    task_by_id = {row["task_id"]: row for row in tasks}
    status_by_id = {row["task_id"]: row for row in status["tasks"]}
    invocation = status["invocation_count"] + 1
    min_free_bytes = float(min_free_mib) * 1024 * 1024
    last_resource_sample = started - 5.0

    def persist(state=None):
        if state is not None:
            status["state"] = state
        status["last_updated"] = _utc_now()
        _atomic_json(run_dir / "status.json", status)

    try:
        _assert_no_active_workers(run_dir, status)
        # Adopt a result written atomically just before a previous manager was interrupted.
        for task_id, record in status_by_id.items():
            result_path = run_dir / record["result_path"]
            result = _valid_result(result_path, task_by_id[task_id])
            if result is not None:
                record["state"] = "completed"
                record["last_result_sha256"] = _sha256_file(result_path)
            elif record["state"] == "running":
                record["state"] = "pending"
                record["interrupted_at"] = _utc_now()
        status["invocation_count"] = invocation
        status.setdefault("invocations", []).append({
            "number": invocation, "workers": workers,
            "max_runtime_seconds": max_runtime_seconds,
            "peak_aggregate_worker_rss_bytes": 0,
            "minimum_observed_available_ram_bytes": psutil.virtual_memory().available,
            "max_tasks": max_tasks,
            "task_timeout_seconds": task_timeout_seconds,
            "minimum_free_ram_mib": min_free_mib,
            "started_at": _utc_now(),
            "available_ram_bytes_at_start": psutil.virtual_memory().available,
            "resource_samples": [],
        })
        persist("running")

        while True:
            elapsed = time.monotonic() - started
            budget_exhausted = elapsed >= max_runtime_seconds
            worker_rss = {}
            for active_id, active in running.items():
                try:
                    rss = psutil.Process(active["process"].pid).memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    rss = active.get("peak_rss_bytes", 0)
                active["peak_rss_bytes"] = max(active.get("peak_rss_bytes", 0), rss)
                worker_rss[active_id] = rss
            available_ram = psutil.virtual_memory().available
            invocation_row = status["invocations"][-1]
            invocation_row["minimum_observed_available_ram_bytes"] = min(
                invocation_row["minimum_observed_available_ram_bytes"], available_ram)
            invocation_row["peak_aggregate_worker_rss_bytes"] = max(
                invocation_row["peak_aggregate_worker_rss_bytes"], sum(worker_rss.values()))
            if elapsed - (last_resource_sample - started) >= 2.0:
                invocation_row["resource_samples"].append({
                    "at": _utc_now(),
                    "elapsed_seconds": round(elapsed, 3),
                    "available_ram_bytes": available_ram,
                    "active_workers": len(running),
                    "worker_rss_bytes": worker_rss,
                })
                last_resource_sample = time.monotonic()
                persist()
            # Reap finished workers and validate their atomic output files.
            for task_id, entry in list(running.items()):
                process = entry["process"]
                record = status_by_id[task_id]
                if process.poll() is not None:
                    result_path = run_dir / record["result_path"]
                    valid = _valid_result(result_path, task_by_id[task_id])
                    if process.returncode == 0 and valid is not None:
                        record.update({"state": "completed",
                                       "completed_at": _utc_now(),
                                       "manager_observed_peak_rss_bytes": entry.get("peak_rss_bytes", 0),
                                       "last_result_sha256": _sha256_file(result_path),
                                       "last_exit_code": process.returncode})
                    else:
                        record["state"] = "failed"
                        record["last_exit_code"] = process.returncode
                        record["last_failure"] = (
                            valid.get("error") if valid else
                            f"worker exited {process.returncode} without a valid atomic result")
                        record.setdefault("failure_history", []).append({
                            "at": _utc_now(), "exit_code": process.returncode,
                            "error": record["last_failure"],
                        })
                    persist()
                    del running[task_id]
                elif time.monotonic() - entry["started_monotonic"] >= task_timeout_seconds:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    record["state"] = "failed"
                    record["last_exit_code"] = process.returncode
                    record["last_failure"] = "per-task timeout"
                    record.setdefault("failure_history", []).append({
                        "at": _utc_now(), "exit_code": process.returncode,
                        "error": "per-task timeout",
                    })
                    persist()
                    del running[task_id]

            if budget_exhausted:
                _terminate_workers(running)
                for task_id, entry in running.items():
                    record = status_by_id[task_id]
                    record["state"] = "pending"
                    record["interrupted_at"] = _utc_now()
                    record["last_failure"] = "batch runtime limit; task will resume from its initial vector"
                running.clear()
                persist("stopped_runtime_limit")
                break

            # Launch only a finite number of starts in this batch and never exceed the RAM gate.
            while len(running) < workers and launched_this_batch < max_tasks:
                candidate = next((row for row in status["tasks"]
                                  if row["state"] in ("pending", "failed") and
                                  row["attempts"] < config["optimization"]["max_attempts"]), None)
                if candidate is None:
                    break
                available = psutil.virtual_memory().available
                if available < min_free_bytes:
                    if not running:
                        status["resource_gate"] = {
                            "state": "blocked_low_ram",
                            "available_ram_bytes": available,
                            "minimum_free_ram_bytes": int(min_free_bytes),
                            "checked_at": _utc_now(),
                        }
                        status["invocations"][-1]["finished_at"] = _utc_now()
                        status["invocations"][-1]["elapsed_seconds"] = round(time.monotonic() - started, 3)
                        persist("blocked_low_ram")
                        return _summary(status)
                    break
                task_id = candidate["task_id"]
                output_path = run_dir / candidate["result_path"]
                log_path = run_dir / "logs" / f"{task_id}.attempt-{candidate['attempts'] + 1}.log"
                worker_lock_path = run_dir / "locks" / f"{task_id}.lock"
                worker_lock_stream = _reserve_worker_lock(worker_lock_path, task_id)
                env = dict(os.environ)
                for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                             "NUMEXPR_NUM_THREADS"):
                    env[name] = "1"
                try:
                    with log_path.open("ab") as log_stream:
                        process = subprocess.Popen(
                            [sys.executable, str(WORKER),
                             str(run_dir / "tasks" / f"{task_id}.json"), str(output_path),
                             str(worker_lock_stream.fileno())],
                            cwd=ROOT, env=env, stdout=log_stream, stderr=subprocess.STDOUT,
                            start_new_session=True, pass_fds=(worker_lock_stream.fileno(),),
                        )
                except Exception:
                    fcntl.flock(worker_lock_stream.fileno(), fcntl.LOCK_UN)
                    worker_lock_stream.close()
                    raise
                else:
                    # The child inherited this open file description and retains the lock on exit.
                    worker_lock_stream.close()
                candidate["state"] = "running"
                candidate["attempts"] += 1
                candidate["started_at"] = _utc_now()
                candidate["worker_pid"] = process.pid
                candidate["last_attempt"] = candidate["attempts"]
                running[task_id] = {"process": process,
                                    "started_monotonic": time.monotonic()}
                launched_this_batch += 1
                status["resource_gate"] = {
                    "state": "passed",
                    "available_ram_bytes": available,
                    "minimum_free_ram_bytes": int(min_free_bytes),
                    "checked_at": _utc_now(),
                }
                persist("running")

            if not running:
                runnable = any(row["state"] in ("pending", "failed") and
                               row["attempts"] < config["optimization"]["max_attempts"]
                               for row in status["tasks"])
                if not runnable or launched_this_batch >= max_tasks:
                    break
            time.sleep(0.2)

        remaining = [row for row in status["tasks"] if row["state"] != "completed"]
        if not remaining:
            persist("completed")
        elif status["state"] not in ("stopped_runtime_limit", "blocked_low_ram"):
            persist("partial" if any(row["state"] == "pending" for row in remaining)
                    else "failed")
        status["invocations"][-1]["finished_at"] = _utc_now()
        status["invocations"][-1]["elapsed_seconds"] = round(time.monotonic() - started, 3)
        persist()
        return _summary(status)
    except KeyboardInterrupt:
        _terminate_workers(running)
        for task_id in running:
            record = status_by_id[task_id]
            record["state"] = "pending"
            record["interrupted_at"] = _utc_now()
            record["last_failure"] = "user interrupt; task will resume from its initial vector"
        running.clear()
        status["invocations"][-1]["finished_at"] = _utc_now()
        status["invocations"][-1]["elapsed_seconds"] = round(time.monotonic() - started, 3)
        persist("interrupted")
        raise
    finally:
        _release_lock(manager_lock)


def status_command(run_dir: Path) -> dict:
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    return _summary(status)


def _pareto(rows):
    nondominated = []
    for candidate in rows:
        area, loss = float(candidate["chip_area_cost"]), float(candidate["worst_il_db"])
        dominated = any(
            float(other["chip_area_cost"]) <= area and float(other["worst_il_db"]) <= loss and
            (float(other["chip_area_cost"]) < area or float(other["worst_il_db"]) < loss)
            for other in rows if other["task_id"] != candidate["task_id"]
        )
        if not dominated:
            nondominated.append(candidate)
    return sorted(nondominated, key=lambda row: (row["chip_area_cost"], row["worst_il_db"], row["task_id"]))


def aggregate(run_dir: Path) -> dict:
    manager_lock = _acquire_lock(run_dir)
    try:
        status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        _assert_no_active_workers(run_dir, status)
        return _aggregate_unlocked(run_dir)
    finally:
        _release_lock(manager_lock)


def _aggregate_unlocked(run_dir: Path) -> dict:
    manifest, status, config, tasks = _load_and_verify_run(run_dir)
    expected = [row["task_id"] for row in tasks]
    if len(expected) != len(set(expected)):
        raise ValueError("Duplicate task IDs in immutable plan")
    observations = []
    seen = set()
    duplicate_results = []
    for task in tasks:
        path = run_dir / "results" / f"{task['task_id']}.json"
        result = _valid_result(path, task)
        if result is None:
            continue
        if result["task_id"] in seen:
            duplicate_results.append(result["task_id"])
            continue
        seen.add(result["task_id"])
        observations.append({
            "task_id": result["task_id"],
            "topology_sha256": result["topology_sha256"],
            "start_sha256": result["start_sha256"],
            "seed_label": result.get("seed_label"),
            "chip_area_cost": result["chip_area_cost"],
            "worst_il_db": result["worst_il_db"],
            "min_h2_db": result["min_h2_db"],
            "min_h3_db": result["min_h3_db"],
            "mandatory_30db_met_on_dense_grid": result["mandatory_30db_met_on_dense_grid"],
            "nominal_35db_met_on_dense_grid": result["nominal_35db_met_on_dense_grid"],
            "il_0p30_target_met_on_dense_grid": result["il_0p30_target_met_on_dense_grid"],
            "solver_converged": result["converged"],
            "best_found_category": result["best_found_category"],
            "result_sha256": _sha256_file(path),
        })
    missing = sorted(set(expected) - seen)
    mandatory = [row for row in observations if row["mandatory_30db_met_on_dense_grid"]]
    nominal = [row for row in observations if row["nominal_35db_met_on_dense_grid"]]
    output = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "objective": "full_lpf",
        "constraint_id": "RF-F002",
        "effective_constraint_sha256": manifest["effective_constraint_sha256"],
        "config_sha256": manifest["config_sha256"],
        "source_hashes": manifest["source_hashes"],
        "scope_complete": not missing and not duplicate_results and len(observations) == len(expected),
        "expected_task_count": len(expected),
        "unique_topology_count": manifest["unique_topology_count"],
        "completed_result_count": len(observations),
        "missing_task_ids": missing,
        "duplicate_result_ids": sorted(set(duplicate_results)),
        "observations": observations,
        "pareto_area_vs_il_mandatory_30db": _pareto(mandatory),
        "pareto_area_vs_il_nominal_35db": _pareto(nominal),
        "pareto_scope_note": "Observed finite task set only; local/nonconverged status remains explicit and no global optimum is claimed.",
        "independent_validation": "Per-task result carries separate formulation and power-balance checks.",
        "physical_validation": "not_run",
        "aggregated_at": _utc_now(),
    }
    _atomic_json(run_dir / "aggregate.json", output)
    return output


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan", help="validate and hash a bounded immutable run plan")
    plan_parser.add_argument("--config", type=Path, required=True)
    plan_parser.add_argument("--run-dir", type=Path, required=True)
    run_parser = sub.add_parser("run", help="run one bounded batch")
    run_parser.add_argument("--run-dir", type=Path, required=True)
    run_parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    run_parser.add_argument("--max-runtime-seconds", type=float, default=900.0)
    run_parser.add_argument("--max-tasks", type=int, default=4)
    run_parser.add_argument("--task-timeout-seconds", type=float, default=900.0)
    run_parser.add_argument("--min-free-mib", type=float, default=1536.0)
    run_parser.add_argument("--resume", action="store_true")
    status_parser = sub.add_parser("status", help="show checkpoint and task counts")
    status_parser.add_argument("--run-dir", type=Path, required=True)
    aggregate_parser = sub.add_parser("aggregate", help="validate result IDs and write Pareto summary")
    aggregate_parser.add_argument("--run-dir", type=Path, required=True)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "plan":
        result = plan(args.config, args.run_dir)
    elif args.command == "run":
        result = run_batch(args.run_dir, workers=args.workers,
                           max_runtime_seconds=args.max_runtime_seconds,
                           max_tasks=args.max_tasks,
                           task_timeout_seconds=args.task_timeout_seconds,
                           min_free_mib=args.min_free_mib, resume=args.resume)
    elif args.command == "status":
        result = status_command(args.run_dir)
    else:
        result = aggregate(args.run_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
