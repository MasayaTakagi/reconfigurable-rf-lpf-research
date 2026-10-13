#!/usr/bin/env python3
"""Resource-aware local process manager for deterministic P4-A shards.

This module orchestrates the existing P4-A calculation and checkpoint code; it
contains no circuit solver or optimization implementation.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid

for _thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

import numpy as np
import psutil
import scipy

ROOT = Path(__file__).resolve().parents[1]
MATCHING = ROOT / "experiments" / "matching_limit"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(MATCHING))
sys.path.insert(0, str(ROOT / "scripts"))

import p4_batch
from coverage_sampler import sample_graphs
from p4_sharding import (
    CheckpointCompatibilityError,
    CheckpointCorruptError,
    aggregate_checkpoints,
    atomic_write_json,
    canonical_config_hash,
    canonical_graph_id,
    load_checkpoint,
    shard_for_graph,
)
from search_space import enumerate_variable_c_layouts
from selection_patch import select_node_balanced

SCHEMA_VERSION = 1
MAX_WORKERS = 4
DEFAULT_RUN_ROOT = "results/local-runs"


class RunnerError(RuntimeError):
    """A local job cannot be safely started, resumed, or aggregated."""


class RunnerCompatibilityError(RunnerError):
    """The current source or numerical environment differs from a saved run."""


class RunLockedError(RunnerError):
    """Another manager currently owns the run directory."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_hash(value) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def run_git(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def cpu_model() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


def _backend_signature(module) -> dict:
    config_module = getattr(module, "__config__", None)
    show = getattr(config_module, "show", None)
    try:
        config = show(mode="dicts") if callable(show) else None
    except (TypeError, ValueError):
        config = None
    result = {}
    if isinstance(config, dict):
        dependencies = config.get("Build Dependencies", {})
        for name in ("blas", "lapack"):
            backend = dependencies.get(name, {}) if isinstance(dependencies, dict) else {}
            if isinstance(backend, dict):
                result[name] = {key: backend[key] for key in ("name", "version", "has ilp64")
                                if key in backend}
    return result or {"backend_identity": "not_exposed"}


def numerical_environment() -> dict:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "blas_lapack": {
            "numpy": _backend_signature(np),
            "scipy": _backend_signature(scipy),
        },
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "thread_environment": {
            name: os.environ.get(name, "unset")
            for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def tracked_source_fingerprints() -> dict[str, str]:
    # Keep an explicit list for the calculation and manager provenance. The
    # solver sources are all hashed so a resumed job cannot silently mix code.
    paths = [ROOT / "scripts" / "local_p4.py", ROOT / "scripts" / "aggregate_p4_a_shards.py"]
    paths += sorted((ROOT / "experiments" / "matching_limit").glob("*.py"))
    paths += sorted((ROOT / "src" / "lpf").glob("*.py"))
    paths += [
        ROOT / "requirements.txt", ROOT / "pyproject.toml", ROOT / "uv.lock",
        ROOT / "data" / "bands.csv", ROOT / "data" / "design_constraints.json",
        ROOT / "data" / "constraints" / "registry.json",
        ROOT / "docs" / "specification.md",
    ]
    formal_dir = ROOT / "data" / "constraints" / "formal"
    trial_dir = ROOT / "data" / "constraints" / "trial"
    if formal_dir.exists():
        paths += sorted(formal_dir.glob("RF-F*.json"))
    if trial_dir.exists():
        paths += sorted(trial_dir.glob("RF-T*.json"))
    unique = sorted(set(paths))
    missing = [str(path) for path in unique if not path.is_file()]
    if missing:
        raise RunnerError("Missing provenance source(s): " + ", ".join(missing))
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in unique}


def environment_snapshot() -> dict:
    uv = shutil.which("uv")
    try:
        uv_version = subprocess.check_output([uv, "--version"], text=True).strip() if uv else None
    except (OSError, subprocess.CalledProcessError):
        uv_version = None
    memory = psutil.virtual_memory()
    return {
        "source_commit": run_git("rev-parse", "HEAD"),
        "git_worktree_status": run_git("status", "--porcelain", "--untracked-files=no") or "",
        "git_worktree_clean": not bool(run_git("status", "--porcelain", "--untracked-files=no")),
        "source_fingerprints": tracked_source_fingerprints(),
        "uv_version": uv_version,
        "uv_lock_sha256": sha256_file(ROOT / "uv.lock"),
        "numerical": numerical_environment(),
        "cpu": {
            "model": cpu_model(),
            "logical_count": psutil.cpu_count(logical=True),
            "physical_count": psutil.cpu_count(logical=False),
        },
        "memory_at_start": {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
            "swap_total_bytes": psutil.swap_memory().total,
        },
        "platform": platform.platform(),
    }


def compatibility_view(snapshot: dict) -> dict:
    """Fields that must remain byte-for-byte compatible for safe resume."""
    return {
        "source_fingerprints": snapshot["source_fingerprints"],
        "uv_lock_sha256": snapshot["uv_lock_sha256"],
        "numerical": snapshot["numerical"],
        "cpu_model": snapshot["cpu"]["model"],
        "platform_machine": platform.machine(),
    }


def _runner_args(search: dict, shard_count: int, shard_index: int = 0) -> argparse.Namespace:
    """Translate a stored search record to the P4-A Namespace API."""
    values = dict(search)
    values.update({
        "shard_count": shard_count,
        "shard_index": shard_index,
        "output": "unused-result.json",
        "checkpoint": "unused-checkpoint.json",
        "failure_report": None,
        "resume": False,
        "resume_run_id": None,
        "resume_artifact_missing": False,
        "max_graphs_per_batch": values.get("max_graphs_per_batch"),
        "max_batch_seconds": values.get("max_batch_seconds"),
    })
    return argparse.Namespace(**values)


def build_plan(search: dict, shard_count: int) -> dict:
    """Use the P4-A enumerators to create a no-computation deterministic plan."""
    if not 1 <= shard_count <= 64:
        raise RunnerError("shard-count must be between 1 and 64")
    args = _runner_args(search, shard_count)
    profile = p4_batch._search_profile(args)
    graphs, sampling_counts = sample_graphs(
        max_internal=4, attempts_per_cell=args.attempts, seed=args.seed,
        max_branches=8, series_mode=None if profile["legacy"] else profile["series_mode"],
    )
    if args.require_lqp02:
        if profile["legacy"]:
            raise RunnerError("--require-lqp02 needs explicit-series mode")
        graphs = [graph for graph in graphs if any(
            kind in ("LQP02HV", "LQP02HQ") for _, _, kind in graph[1]
        )]
    if args.require_both_series:
        if profile["legacy"] or profile["series_mode"] != "both":
            raise RunnerError("--require-both-series requires --series-mode both")
        graphs = [graph for graph in graphs if {"LQP02HV", "LQP02HQ"} <= {
            kind for _, _, kind in graph[1]
        }]
    graphs = [graph for graph in graphs if any(kind != "GJM01" for _, _, kind in graph[1])]
    selected, eligible = select_node_balanced(graphs, args.per_bin)
    if args.max_topology_graphs is not None:
        selected = selected[:args.max_topology_graphs]
    rows = p4_batch.load_bands()
    grid = p4_batch.frequency_grid(rows, args.coarse_points)
    entries = sorted(
        (canonical_graph_id(graph), internal_nodes, bin_index, graph)
        for (internal_nodes, bin_index), graph in selected
    )
    graph_ids = [entry[0] for entry in entries]
    if len(graph_ids) != len(set(graph_ids)):
        raise RunnerError("P4-A plan contains duplicate canonical graph IDs")
    candidate_plan = {}
    graph_records = []
    for graph_id, internal_nodes, bin_index, graph in entries:
        variable_layouts = enumerate_variable_c_layouts(
            graph, profile["policy"], max_layouts=profile["max_variable_layouts"]
        )
        coupling_layouts = p4_batch.layout_candidates(
            graph, args.layouts, resolved_policy=profile["policy"]
        )
        if not variable_layouts or not coupling_layouts:
            raise RunnerError(f"No admissible optimizer candidates for graph {graph_id}")
        candidates = len(variable_layouts) * len(coupling_layouts) * args.starts
        candidate_plan[graph_id] = candidates
        graph_records.append({
            "graph_id": graph_id,
            "internal_nodes": internal_nodes,
            "area_bin": bin_index,
            "edges": [list(edge) for edge in graph[1]],
            "candidate_count": candidates,
            "shard_index": shard_for_graph(graph_id, shard_count),
        })
    config = p4_batch.build_run_config(
        args, grid, graph_ids, {key: candidate_plan[key] for key in sorted(candidate_plan)}
    )
    assignments = {
        str(index): [record["graph_id"] for record in graph_records
                     if record["shard_index"] == index]
        for index in range(shard_count)
    }
    assigned = [graph_id for values in assignments.values() for graph_id in values]
    if len(assigned) != len(set(assigned)) or sorted(assigned) != sorted(graph_ids):
        raise RunnerError("Deterministic shard assignment has a duplicate or missing graph")
    return {
        "constraint_id": profile["constraint_id"],
        "effective_constraint_sha256": profile["constraint_sha256"],
        "analysis_mode": "matching_only",
        "p4_config": config,
        "p4_config_hash": p4_batch.canonical_config_hash(config),
        "graph_count": len(graph_records),
        "planned_optimizer_candidates": sum(candidate_plan.values()),
        "sampling_counts": _json_safe(sampling_counts),
        "eligible_count": _json_safe(eligible),
        "graphs": graph_records,
        "graph_ids": graph_ids,
        "shard_assignments": assignments,
        "search": search,
        "shard_count": shard_count,
    }


def search_from_namespace(args: argparse.Namespace) -> dict:
    return {
        "constraint_id": args.constraint_id,
        "series_mode": args.series_mode,
        "attempts": args.attempts,
        "per_bin": args.per_bin,
        "starts": args.starts,
        "layouts": args.layouts,
        "iterations": args.iterations,
        "coarse_points": args.coarse_points,
        "validation_points": args.validation_points,
        "seed": args.seed,
        "max_variable_layouts": args.max_variable_layouts,
        "require_lqp02": args.require_lqp02,
        "require_both_series": args.require_both_series,
        "max_topology_graphs": args.max_topology_graphs,
        "max_graphs_per_batch": args.max_graphs_per_batch,
        "max_batch_seconds": args.max_batch_seconds,
    }


def _run_id_ok(run_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", run_id))


def run_dir(root: Path, run_id: str) -> Path:
    if not _run_id_ok(run_id):
        raise RunnerError("Invalid run ID")
    return root / run_id


@contextmanager
def exclusive_run_lock(directory: Path):
    path = directory / "manager.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RunLockedError(f"Another local manager holds {path}") from exc
        stream.seek(0)
        stream.truncate()
        stream.write(json.dumps({"pid": os.getpid(), "acquired_at_utc": utc_now()}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _shard_worker_lock_path(directory: Path, index: int) -> Path:
    return directory / "shards" / f"shard-{index}" / "worker.lock"


def assert_no_active_shard_workers(directory: Path, shard_count: int) -> None:
    """Refuse a resume while an orphan/live child still owns a shard.

    The worker inherits the flock file descriptor at exec. A manager crash
    releases manager.lock but cannot release the worker's own file lock.
    Never remove or replace worker.lock: a deleted, locked inode would allow
    a second writer through a new inode at the same pathname.
    """
    for index in range(shard_count):
        path = _shard_worker_lock_path(directory, index)
        if not path.exists():
            continue
        with path.open("a+b") as stream:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RunLockedError(
                    f"Shard {index} worker is still active ({path}); "
                    "wait for it to exit or stop it safely before resuming"
                ) from exc
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"Invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RunnerError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, payload: dict) -> None:
    atomic_write_json(path, payload)


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def _current_memory() -> dict:
    memory = psutil.virtual_memory()
    return {
        "total_bytes": memory.total,
        "available_bytes": memory.available,
        "used_bytes": memory.used,
        "percent": memory.percent,
        "swap_used_bytes": psutil.swap_memory().used,
    }


def memory_allows_launch(available_bytes: int, minimum_available_bytes: int) -> bool:
    return available_bytes >= minimum_available_bytes


def _bytes_mib(value: int) -> float:
    return round(value / (1024 * 1024), 2)


def _checkpoint_status(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = _read_json(path)
    except RunnerError:
        return "corrupt"
    value = payload.get("status")
    return value if isinstance(value, str) else "corrupt"


def _optimization_counts(checkpoints: list[Path], planned: int) -> dict:
    records = {}
    failed_keys = set()
    for path in checkpoints:
        if not path.is_file():
            continue
        try:
            payload = _read_json(path)
        except RunnerError:
            continue
        for row in payload.get("results", []) if isinstance(payload.get("results"), list) else []:
            if not isinstance(row, dict):
                continue
            for item in row.get("optimization_runs", []) if isinstance(row.get("optimization_runs"), list) else []:
                if isinstance(item, dict) and isinstance(item.get("candidate_key"), str):
                    records[item["candidate_key"]] = item
        partials = payload.get("partial_optimization_runs", {})
        if isinstance(partials, dict):
            for group in partials.values():
                if isinstance(group, list):
                    for item in group:
                        if isinstance(item, dict) and isinstance(item.get("candidate_key"), str):
                            records[item["candidate_key"]] = item
        log = payload.get("candidate_execution_log", [])
        if isinstance(log, list):
            for item in log:
                if isinstance(item, dict) and item.get("status") == "failed":
                    key = item.get("candidate_key")
                    if isinstance(key, str):
                        failed_keys.add(key)
    converged = sum(bool(item.get("converged")) for item in records.values())
    nonconverged = len(records) - converged
    failed = len(failed_keys - records.keys())
    return {
        "planned": planned,
        "completed": len(records),
        "converged": converged,
        "nonconverged": nonconverged,
        "failed": failed,
        "unrun": max(0, planned - len(records) - failed),
    }


class LocalRunManager:
    def __init__(self, directory: Path, *, workers: int, memory_min_free_mib: float,
                 monitor_interval: float, memory_stall_timeout: float,
                 max_runtime: float, force_kill_after: float):
        self.directory = directory
        self.workers = workers
        self.memory_min_free_bytes = int(memory_min_free_mib * 1024 * 1024)
        self.monitor_interval = monitor_interval
        self.memory_stall_timeout = memory_stall_timeout
        self.max_runtime = max_runtime
        self.force_kill_after = force_kill_after
        self.stop_event = threading.Event()
        self.stop_reason: str | None = None
        self.stop_requested = False
        self._signal_reason: str | None = None
        self.manifest = _read_json(directory / "manifest.json")
        self.plan = self.manifest["plan"]
        self.search = self.plan["search"]
        self.shard_count = self.plan["shard_count"]
        self.shards_root = directory / "shards"
        self.shards_root.mkdir(parents=True, exist_ok=True)
        self.status = _read_json(directory / "status.json") if (directory / "status.json").exists() else {}
        self._active: dict[int, dict] = {}
        self._started_monotonic: float | None = None
        self._resource_summary = self.manifest.setdefault("resource_summary", {
            "peak_total_worker_rss_bytes": 0,
            "peak_worker_rss_bytes": {},
            "peak_cpu_percent": 0.0,
            "cpu_percent_samples": [],
            "minimum_available_memory_bytes": None,
            "maximum_process_count": 0,
        })

    def _record(self, event: str, **fields) -> None:
        record = {"timestamp_utc": utc_now(), "event": event, **fields}
        with (self.directory / "logs" / "manager.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
        print(json.dumps(record, ensure_ascii=False), flush=True)

    def _save(self, state: str, *, finish: bool = False) -> None:
        now = utc_now()
        self.manifest["status"] = state
        self.manifest["updated_at_utc"] = now
        if finish:
            self.manifest["finished_at_utc"] = now
            if self._started_monotonic is not None:
                self.manifest["elapsed_seconds"] = round(time.monotonic() - self._started_monotonic, 3)
        self.manifest["shard_process_history"] = {
            index: item.get("process_history", [])
            for index, item in self.status.get("shards", {}).items()
        }
        self.status.update({
            "run_id": self.manifest["run_id"],
            "status": state,
            "updated_at_utc": now,
            "workers_requested": self.workers,
            "shard_count": self.shard_count,
            "active_processes": len(self._active),
            "shards": self.status.get("shards", {}),
            "resources": self.status.get("resources", {}),
        })
        self.manifest["resource_summary"] = self._resource_summary
        _write_json(self.directory / "manifest.json", self.manifest)
        _write_json(self.directory / "status.json", self.status)

    def _shard_dir(self, index: int) -> Path:
        return self.shards_root / f"shard-{index}"

    def _prepare_shard(self, index: int, *, resume: bool) -> None:
        directory = self._shard_dir(index)
        directory.mkdir(parents=True, exist_ok=True)
        checkpoint = directory / "checkpoint.json"
        failure = directory / "failure.json"
        if resume and checkpoint.exists():
            expected_ids = self.plan["shard_assignments"][str(index)]
            try:
                load_checkpoint(
                    checkpoint,
                    config_hash=self.plan["p4_config_hash"],
                    shard_index=index,
                    shard_count=self.shard_count,
                    expected_graph_ids=expected_ids,
                )
            except (CheckpointCompatibilityError, CheckpointCorruptError) as exc:
                kind = "incompatible" if isinstance(exc, CheckpointCompatibilityError) else "corrupt"
                raise RunnerCompatibilityError(f"Shard {index} checkpoint {kind}: {exc}") from exc
        if failure.exists():
            history = directory / "failure-history"
            history.mkdir(exist_ok=True)
            destination = history / f"failure-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}.json"
            os.replace(failure, destination)
        state = _checkpoint_status(checkpoint)
        shards = self.status.setdefault("shards", {})
        item = shards.setdefault(str(index), {})
        if resume and state == "completed":
            item.update({
                "status": "completed", "exit_code": 0, "checkpoint": str(checkpoint),
                "restored": True, "completed_graphs": len(self.plan["shard_assignments"][str(index)]),
                "expected_graphs": len(self.plan["shard_assignments"][str(index)]),
                "pid": None,
            })
            return
        progress = {}
        if checkpoint.exists():
            payload = _read_json(checkpoint)
            progress = {
                "completed_graphs": len(payload.get("completed_graph_ids", [])),
                "completed_optimizer_candidates": payload.get("completed_optimizer_candidates", 0),
                "planned_optimizer_candidates": payload.get("planned_optimizer_candidates", 0),
            }
        item.update({
            "status": "queued", "checkpoint": str(checkpoint),
            "attempts": item.get("attempts", 0),
            "completed_graphs": progress.get("completed_graphs", 0),
            "completed_optimizer_candidates": progress.get("completed_optimizer_candidates", 0),
            "planned_optimizer_candidates": progress.get("planned_optimizer_candidates", 0),
            "expected_graphs": len(self.plan["shard_assignments"][str(index)]),
            "restored": bool(resume and checkpoint.exists()),
            "pid": None,
        })
        if item.get("process_history"):
            for previous in item["process_history"]:
                if previous.get("exit_code") is None:
                    previous["manager_lost_exit_observation"] = True

    def _worker_command(self, index: int, *, resume: bool) -> list[str]:
        directory = self._shard_dir(index)
        command = [
            sys.executable, str(MATCHING / "p4_batch.py"),
            "--constraint-id", self.search["constraint_id"],
            "--series-mode", self.search["series_mode"],
            "--attempts", str(self.search["attempts"]),
            "--per-bin", str(self.search["per_bin"]),
            "--starts", str(self.search["starts"]),
            "--layouts", str(self.search["layouts"]),
            "--iterations", str(self.search["iterations"]),
            "--coarse-points", str(self.search["coarse_points"]),
            "--validation-points", str(self.search["validation_points"]),
            "--max-variable-layouts", str(self.search["max_variable_layouts"]),
            "--seed", str(self.search["seed"]),
            "--shard-count", str(self.shard_count),
            "--shard-index", str(index),
            "--checkpoint", str(directory / "checkpoint.json"),
            "--output", str(directory / "result.json"),
            "--failure-report", str(directory / "failure.json"),
        ]
        if self.search.get("require_lqp02"):
            command.append("--require-lqp02")
        if self.search.get("require_both_series"):
            command.append("--require-both-series")
        if self.search.get("max_topology_graphs") is not None:
            command += ["--max-topology-graphs", str(self.search["max_topology_graphs"])]
        if self.search.get("max_graphs_per_batch") is not None:
            command += ["--max-graphs-per-batch", str(self.search["max_graphs_per_batch"])]
        if self.search.get("max_batch_seconds") is not None:
            command += ["--max-batch-seconds", str(self.search["max_batch_seconds"])]
        if resume and (directory / "checkpoint.json").exists():
            command.append("--resume")
        return command

    def _spawn(self, index: int, *, resume: bool) -> None:
        directory = self._shard_dir(index)
        log_path = directory / "worker.log"
        log = log_path.open("ab", buffering=0)
        env = os.environ.copy()
        env.update({
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONUNBUFFERED": "1",
        })
        command = self._worker_command(index, resume=resume)
        worker_lock = _shard_worker_lock_path(self.directory, index).open("a+b")
        try:
            try:
                fcntl.flock(worker_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RunLockedError(
                    f"Shard {index} still has an active worker; refusing duplicate writer"
                ) from exc
            # pass_fds explicitly survives exec, so the child keeps the lock
            # even if this manager is killed without running cleanup.
            process = subprocess.Popen(
                command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, pass_fds=(worker_lock.fileno(),),
            )
        except Exception:
            log.close()
            raise
        finally:
            worker_lock.close()
        self._active[index] = {
            "process": process,
            "log": log,
            "pid": process.pid,
            "started_monotonic": time.monotonic(),
            "started_at_utc": utc_now(),
            "rss_peak_bytes": 0,
            "cpu_percent": 0.0,
            "resume": resume,
        }
        item = self.status["shards"][str(index)]
        item.update({"status": "running", "pid": process.pid,
                     "attempts": item.get("attempts", 0) + 1,
                     "last_started_at_utc": utc_now()})
        item.setdefault("process_history", []).append({
            "pid": process.pid,
            "started_at_utc": self._active[index]["started_at_utc"],
            "resume": resume,
            "command": command,
            "exit_code": None,
        })
        self._record("worker_started", shard_index=index, pid=process.pid,
                     command=command, resume=resume)

    def _mark_launch_failed(self, index: int, exc: Exception) -> None:
        item = self.status["shards"][str(index)]
        failure = {
            "state": "failed", "shard_index": index,
            "message": f"worker launch failed: {type(exc).__name__}: {exc}",
            "failed_at_utc": utc_now(),
        }
        item.update({"status": "failed", "exit_code": None, "pid": None,
                     "failure_reason": failure["message"]})
        item.setdefault("process_history", []).append({
            "started_at_utc": failure["failed_at_utc"], "finished_at_utc": failure["failed_at_utc"],
            "exit_code": None, "launch_error": failure["message"],
        })
        _write_json(self._shard_dir(index) / "failure.json", failure)
        self._record("worker_launch_failed", shard_index=index, error=failure["message"])

    def _sample_resources(self) -> dict:
        memory = _current_memory()
        rss_sum = 0
        process_count = 0
        active_metrics = {}
        for index, item in self._active.items():
            process = item["process"]
            try:
                proc = psutil.Process(process.pid)
                rss = proc.memory_info().rss
                cpu = proc.cpu_percent(interval=None)
                item["rss_peak_bytes"] = max(item["rss_peak_bytes"], rss)
                item["cpu_percent"] = cpu
                rss_sum += rss
                process_count += 1
                active_metrics[str(index)] = {"pid": process.pid, "rss_bytes": rss,
                                              "cpu_percent": cpu}
                peaks = self._resource_summary["peak_worker_rss_bytes"]
                peaks[str(index)] = max(peaks.get(str(index), 0), item["rss_peak_bytes"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                active_metrics[str(index)] = {"pid": process.pid, "rss_bytes": None,
                                              "cpu_percent": None}
        cpu_percent = psutil.cpu_percent(interval=None)
        self._resource_summary["peak_total_worker_rss_bytes"] = max(
            self._resource_summary["peak_total_worker_rss_bytes"], rss_sum
        )
        self._resource_summary["peak_cpu_percent"] = max(
            self._resource_summary["peak_cpu_percent"], cpu_percent
        )
        samples = self._resource_summary["cpu_percent_samples"]
        samples.append(cpu_percent)
        if len(samples) > 10000:
            del samples[:-10000]
        minimum = self._resource_summary["minimum_available_memory_bytes"]
        self._resource_summary["minimum_available_memory_bytes"] = (
            memory["available_bytes"] if minimum is None
            else min(minimum, memory["available_bytes"])
        )
        self._resource_summary["maximum_process_count"] = max(
            self._resource_summary["maximum_process_count"], process_count
        )
        sample = {
            "timestamp_utc": utc_now(),
            "memory": memory,
            "total_worker_rss_bytes": rss_sum,
            "cpu_percent": cpu_percent,
            "active_processes": process_count,
            "workers": active_metrics,
        }
        with (self.directory / "logs" / "monitor.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(sample, sort_keys=True) + "\n")
        self.status["resources"] = {
            "memory": memory,
            "total_worker_rss_bytes": rss_sum,
            "cpu_percent": cpu_percent,
            "active_processes": process_count,
            "workers": active_metrics,
            "peak_total_worker_rss_bytes": self._resource_summary["peak_total_worker_rss_bytes"],
            "peak_cpu_percent": self._resource_summary["peak_cpu_percent"],
        }
        return memory

    def _update_shard_checkpoint_progress(self, index: int) -> None:
        directory = self._shard_dir(index)
        checkpoint = directory / "checkpoint.json"
        item = self.status["shards"][str(index)]
        if not checkpoint.exists():
            return
        try:
            payload = _read_json(checkpoint)
        except RunnerError as exc:
            item["checkpoint_read_error"] = str(exc)
            item["checkpoint_status"] = "corrupt"
            return
        item.update({
            "checkpoint_status": payload.get("status"),
            "completed_graphs": len(payload.get("completed_graph_ids", [])),
            "expected_graphs": len(payload.get("expected_graph_ids", [])),
            "completed_optimizer_candidates": payload.get("completed_optimizer_candidates", 0),
            "planned_optimizer_candidates": payload.get("planned_optimizer_candidates", 0),
            "elapsed_seconds": payload.get("elapsed_seconds", 0),
        })

    def _request_stop(self, reason: str) -> None:
        if self.stop_requested:
            return
        self.stop_requested = True
        self.stop_reason = reason
        queued = list(self._pending)
        self._pending.clear()
        for index in queued:
            self.status["shards"][str(index)]["status"] = "not_run"
        self._record("graceful_stop_requested", reason=reason, active_shards=sorted(self._active),
                     not_run_shards=queued)
        for index, item in self._active.items():
            process = item["process"]
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            self.status["shards"][str(index)]["stop_requested"] = True
        self._save("interrupted")

    def _finish_worker(self, index: int) -> None:
        item = self._active.pop(index)
        process = item["process"]
        returncode = process.poll()
        elapsed = round(time.monotonic() - item["started_monotonic"], 3)
        item["log"].close()
        shard_status = self.status["shards"][str(index)]
        checkpoint_path = self._shard_dir(index) / "checkpoint.json"
        checkpoint_state = _checkpoint_status(checkpoint_path)
        shard_status.update({
            "pid": None,
            "exit_code": returncode,
            "last_elapsed_seconds": elapsed,
            "cumulative_elapsed_seconds": round(shard_status.get("cumulative_elapsed_seconds", 0) + elapsed, 3),
            "peak_rss_bytes": max(shard_status.get("peak_rss_bytes", 0), item["rss_peak_bytes"]),
            "checkpoint_status": checkpoint_state,
            "finished_at_utc": utc_now(),
        })
        history = shard_status.setdefault("process_history", [])
        if history:
            history[-1].update({
                "finished_at_utc": shard_status["finished_at_utc"],
                "elapsed_seconds": elapsed,
                "exit_code": returncode,
                "checkpoint_status": checkpoint_state,
                "peak_rss_bytes": item["rss_peak_bytes"],
            })
        if returncode == 0 and checkpoint_state == "completed":
            shard_status["status"] = "completed"
        elif returncode == 0 and checkpoint_state in {"partial", "running"} and self.stop_reason is None:
            shard_status["status"] = "queued"
            self._pending.append(index)
        elif returncode == 0 and checkpoint_state in {"partial", "running"}:
            shard_status["status"] = "interrupted"
        elif (returncode in (130, -signal.SIGTERM, -signal.SIGINT) or checkpoint_state == "interrupted"
              or (self.stop_reason is not None and returncode is not None and returncode < 0)):
            shard_status["status"] = "interrupted"
            if self.stop_reason is None:
                self._request_stop("worker_interrupted")
        else:
            shard_status["status"] = "failed"
            shard_status["failure_reason"] = f"worker_exit_{returncode}; checkpoint={checkpoint_state}"
        self._record("worker_finished", shard_index=index, exit_code=returncode,
                     checkpoint_status=checkpoint_state, elapsed_seconds=elapsed,
                     peak_rss_bytes=item["rss_peak_bytes"], state=shard_status["status"])

    def execute(self, *, resume: bool) -> int:
        started = time.monotonic()
        self.manifest["started_at_utc"] = self.manifest.get("started_at_utc") or utc_now()
        self.manifest["execution_history"].append({
            "started_at_utc": utc_now(), "workers": self.workers,
            "resume": resume, "status": "running",
            "memory_min_free_bytes": self.memory_min_free_bytes,
            "monitor_interval_seconds": self.monitor_interval,
            "max_runtime_seconds": self.max_runtime,
        })
        self._started_monotonic = started
        if resume:
            self.manifest["resume_count"] = self.manifest.get("resume_count", 0) + 1
        self._pending = []
        for index in range(self.shard_count):
            self._prepare_shard(index, resume=resume)
            shard_state = self.status["shards"][str(index)]["status"]
            if shard_state != "completed":
                self._pending.append(index)
        self._save("running")
        wall_started = time.monotonic()
        mem_stall_started = None
        terminating_at = None
        original_handlers = {}

        def signal_handler(signum, _frame):
            self.stop_event.set()
            self._signal_reason = f"signal_{signal.Signals(signum).name}"

        for sig in (signal.SIGINT, signal.SIGTERM):
            original_handlers[sig] = signal.signal(sig, signal_handler)
        try:
            while self._pending or self._active:
                now = time.monotonic()
                if self.stop_event.is_set() and terminating_at is None:
                    self._request_stop(self._signal_reason or "signal_received")
                    terminating_at = now
                if self.max_runtime and now - wall_started >= self.max_runtime and terminating_at is None:
                    self._request_stop("max_runtime_reached")
                    terminating_at = now
                memory = self._sample_resources()
                pending_blocked = bool(self._pending) and len(self._active) < self.workers
                if pending_blocked and not memory_allows_launch(
                    memory["available_bytes"], self.memory_min_free_bytes
                ):
                    if mem_stall_started is None:
                        mem_stall_started = now
                        self._record("memory_launch_paused", available_bytes=memory["available_bytes"],
                                     threshold_bytes=self.memory_min_free_bytes)
                    elif self.memory_stall_timeout and now - mem_stall_started >= self.memory_stall_timeout:
                        self._request_stop("memory_stall_timeout")
                        terminating_at = now
                else:
                    mem_stall_started = None
                # Reap first, so newly available slots are used without waiting a
                # full sample interval. A partial graph batch is safely requeued.
                for index, item in list(self._active.items()):
                    if item["process"].poll() is not None:
                        self._update_shard_checkpoint_progress(index)
                        self._finish_worker(index)
                if self.stop_reason is None:
                    while self._pending and len(self._active) < self.workers:
                        current_memory = _current_memory()
                        if not memory_allows_launch(current_memory["available_bytes"],
                                                    self.memory_min_free_bytes):
                            break
                        index = self._pending.pop(0)
                        checkpoint_exists = (self._shard_dir(index) / "checkpoint.json").exists()
                        try:
                            self._spawn(index, resume=checkpoint_exists)
                        except Exception as exc:
                            self._mark_launch_failed(index, exc)
                            self._save("failed")
                            continue
                        # Give the child time to import its numerical stack before
                        # deciding whether another process fits in available RAM.
                        time.sleep(min(0.2, self.monitor_interval))
                        memory = self._sample_resources()
                        if not memory_allows_launch(memory["available_bytes"],
                                                    self.memory_min_free_bytes):
                            if mem_stall_started is None:
                                mem_stall_started = time.monotonic()
                                self._record("memory_launch_paused", available_bytes=memory["available_bytes"],
                                             threshold_bytes=self.memory_min_free_bytes)
                            break
                for index in list(self._active):
                    self._update_shard_checkpoint_progress(index)
                self.status["active_processes"] = len(self._active)
                self._save("interrupted" if self.stop_reason else "running")
                if terminating_at is not None and self._active:
                    elapsed_stop = time.monotonic() - terminating_at
                    if self.force_kill_after and elapsed_stop >= self.force_kill_after:
                        self._record("graceful_stop_timeout_escalated", elapsed_seconds=elapsed_stop,
                                     active_shards=sorted(self._active),
                                     note="Atomic checkpoint replacement limits damage; interrupted checkpoint may replay last candidate")
                        for item in self._active.values():
                            process = item["process"]
                            if process.poll() is None:
                                try:
                                    os.killpg(process.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                        self.force_kill_after = 0
                if self._pending or self._active:
                    time.sleep(self.monitor_interval)
        finally:
            for sig, handler in original_handlers.items():
                signal.signal(sig, handler)
        self._sample_resources()
        failures = [index for index, item in self.status["shards"].items()
                    if item.get("status") == "failed"]
        pending = [index for index, item in self.status["shards"].items()
                   if item.get("status") not in {"completed", "failed"}]
        if failures:
            final_state = "failed"
            exit_code = 1
        elif all(item.get("status") == "completed" for item in self.status["shards"].values()):
            final_state = "completed"
            exit_code = 0
        elif pending or self.stop_reason:
            final_state = "interrupted" if self.stop_reason else "partial"
            exit_code = 130 if self.stop_reason else 0
        else:
            final_state = "partial"
            exit_code = 0
        if self.manifest["execution_history"]:
            self.manifest["execution_history"][-1].update({
                "finished_at_utc": utc_now(), "elapsed_seconds": round(time.monotonic() - started, 3),
                "status": final_state, "worker_exit_codes": {
                    index: item.get("exit_code") for index, item in self.status["shards"].items()
                },
            })
        self.manifest["worker_exit_codes"] = {
            index: item.get("exit_code") for index, item in self.status["shards"].items()
        }
        self.manifest["resource_summary"] = self._resource_summary
        self.manifest["optimizer_counts"] = _optimization_counts(
            [self._shard_dir(index) / "checkpoint.json" for index in range(self.shard_count)],
            self.plan["planned_optimizer_candidates"],
        )
        self._save(final_state, finish=True)
        self._record("run_finished", state=final_state, exit_code=exit_code,
                     optimizer_counts=self.manifest["optimizer_counts"])
        return exit_code


def create_run(root: Path, args) -> tuple[str, Path]:
    search = search_from_namespace(args)
    plan = build_plan(search, args.shard_count)
    snapshot = environment_snapshot()
    compatibility = compatibility_view(snapshot)
    run_id = _now_run_id()
    directory = run_dir(root, run_id)
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir(exist_ok=False)
    (directory / "logs").mkdir()
    (directory / "shards").mkdir()
    started = utc_now()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at_utc": started,
        "started_at_utc": None,
        "finished_at_utc": None,
        "status": "created",
        "analysis_mode": "matching_only",
        "constraint_id": plan["constraint_id"],
        "effective_constraint_sha256": plan["effective_constraint_sha256"],
        "git": {
            "commit_sha": snapshot["source_commit"],
            "worktree_clean": snapshot["git_worktree_clean"],
            "worktree_status": snapshot["git_worktree_status"],
        },
        "source_fingerprints": snapshot["source_fingerprints"],
        "environment": snapshot,
        "compatibility": compatibility,
        "compatibility_sha256": canonical_json_hash(compatibility),
        "uv_lock_sha256": snapshot["uv_lock_sha256"],
        "plan": plan,
        "execution_settings": {
            "workers_initial": args.workers,
            "workers_max_allowed": MAX_WORKERS,
            "memory_min_free_mib": args.memory_min_free_mib,
            "monitor_interval_seconds": args.monitor_interval,
            "memory_stall_timeout_seconds": args.memory_stall_timeout,
            "max_runtime_seconds": args.max_runtime,
            "force_kill_after_seconds": args.force_kill_after,
        },
        "execution_history": [],
        "resume_count": 0,
        "worker_exit_codes": {},
        "resource_summary": {
            "peak_total_worker_rss_bytes": 0,
            "peak_worker_rss_bytes": {},
            "peak_cpu_percent": 0.0,
            "cpu_percent_samples": [],
            "minimum_available_memory_bytes": None,
            "maximum_process_count": 0,
        },
        "optimizer_counts": {
            "planned": plan["planned_optimizer_candidates"],
            "completed": 0, "converged": 0, "nonconverged": 0,
            "failed": 0, "unrun": plan["planned_optimizer_candidates"],
        },
    }
    _write_json(directory / "manifest.json", manifest)
    _write_json(directory / "status.json", {
        "run_id": run_id, "status": "created", "created_at_utc": started,
        "workers_requested": args.workers, "shard_count": args.shard_count,
        "active_processes": 0, "shards": {}, "resources": {},
    })
    for index in range(args.shard_count):
        shard_dir = directory / "shards" / f"shard-{index}"
        shard_dir.mkdir()
    return run_id, directory


def _load_manifest(directory: Path) -> dict:
    manifest = _read_json(directory / "manifest.json")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise RunnerCompatibilityError("Unsupported local run manifest schema")
    if manifest.get("run_id") != directory.name:
        raise RunnerCompatibilityError("Run directory and manifest run IDs do not match")
    return manifest


def verify_resume_compatibility(directory: Path, manifest: dict) -> dict:
    snapshot = environment_snapshot()
    current = compatibility_view(snapshot)
    saved = manifest.get("compatibility")
    if not isinstance(saved, dict):
        raise RunnerCompatibilityError("Manifest has no compatibility fingerprint")
    if current != saved:
        changed = [key for key in sorted(set(current) | set(saved)) if current.get(key) != saved.get(key)]
        raise RunnerCompatibilityError("Incompatible resume environment/source: " + ", ".join(changed))
    plan = manifest.get("plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("search"), dict):
        raise RunnerCompatibilityError("Manifest has no P4-A search configuration")
    recalculated = build_plan(plan["search"], plan["shard_count"])
    if recalculated["p4_config_hash"] != plan.get("p4_config_hash"):
        raise RunnerCompatibilityError("P4-A settings, RF policy, frequency grid, or source hash changed")
    if recalculated["graph_ids"] != plan.get("graph_ids"):
        raise RunnerCompatibilityError("Deterministic selected graph set differs from manifest")
    if recalculated["shard_assignments"] != plan.get("shard_assignments"):
        raise RunnerCompatibilityError("Deterministic shard assignment differs from manifest")
    return snapshot


def resume_run(root: Path, run_id: str, *, workers: int | None = None,
               memory_min_free_mib: float | None = None, monitor_interval: float | None = None,
               memory_stall_timeout: float | None = None, max_runtime: float | None = None,
               force_kill_after: float | None = None) -> int:
    directory = run_dir(root, run_id)
    if not directory.is_dir():
        raise RunnerError(f"Run directory not found: {directory}")
    with exclusive_run_lock(directory):
        manifest = _load_manifest(directory)
        snapshot = verify_resume_compatibility(directory, manifest)
        # Check before updating manifests/checkpoints; manager.lock alone is
        # insufficient after an uncatchable manager crash (SIGKILL).
        assert_no_active_shard_workers(directory, manifest["plan"]["shard_count"])
        manifest["resume_environment_history"] = manifest.get("resume_environment_history", [])
        manifest["resume_environment_history"].append({
            "at_utc": utc_now(), "source_commit": snapshot["source_commit"],
            "worktree_clean": snapshot["git_worktree_clean"],
            "compatibility_sha256": canonical_json_hash(compatibility_view(snapshot)),
        })
        _write_json(directory / "manifest.json", manifest)
        settings = manifest["execution_settings"]
        count = workers if workers is not None else settings["workers_initial"]
        _validate_workers(count, manifest["plan"]["shard_count"])
        manager = LocalRunManager(
            directory,
            workers=count,
            memory_min_free_mib=(memory_min_free_mib if memory_min_free_mib is not None
                                 else settings["memory_min_free_mib"]),
            monitor_interval=(monitor_interval if monitor_interval is not None
                              else settings["monitor_interval_seconds"]),
            memory_stall_timeout=(memory_stall_timeout if memory_stall_timeout is not None
                                  else settings["memory_stall_timeout_seconds"]),
            max_runtime=(max_runtime if max_runtime is not None else settings["max_runtime_seconds"]),
            force_kill_after=(force_kill_after if force_kill_after is not None
                              else settings["force_kill_after_seconds"]),
        )
        return manager.execute(resume=True)


def _validate_workers(workers: int, shard_count: int) -> None:
    if isinstance(workers, bool) or not 1 <= workers <= MAX_WORKERS:
        raise RunnerError(f"workers must be between 1 and {MAX_WORKERS}")
    if workers > shard_count:
        raise RunnerError("workers cannot exceed shard-count")


def start_run(root: Path, args) -> tuple[int, str, Path]:
    _validate_workers(args.workers, args.shard_count)
    run_id, directory = create_run(root, args)
    with exclusive_run_lock(directory):
        manager = LocalRunManager(
            directory, workers=args.workers,
            memory_min_free_mib=args.memory_min_free_mib,
            monitor_interval=args.monitor_interval,
            memory_stall_timeout=args.memory_stall_timeout,
            max_runtime=args.max_runtime,
            force_kill_after=args.force_kill_after,
        )
        code = manager.execute(resume=False)
    return code, run_id, directory


def status_run(root: Path, run_id: str) -> dict:
    directory = run_dir(root, run_id)
    if not directory.is_dir():
        raise RunnerError(f"Run directory not found: {directory}")
    manifest = _load_manifest(directory)
    status_path = directory / "status.json"
    status = _read_json(status_path) if status_path.exists() else {"status": manifest.get("status")}
    current = psutil.virtual_memory()
    active = []
    for shard_index, item in status.get("shards", {}).items():
        pid = item.get("pid") if isinstance(item, dict) else None
        if isinstance(pid, int) and psutil.pid_exists(pid):
            try:
                active.append({"shard_index": int(shard_index), "pid": pid,
                               "rss_bytes": psutil.Process(pid).memory_info().rss})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    status["active_processes"] = len(active)
    resources = status.get("resources")
    if isinstance(resources, dict):
        resources["active_processes"] = len(active)
        resources["memory"] = {
            "total_bytes": current.total,
            "available_bytes": current.available,
            "used_bytes": current.used,
            "percent": current.percent,
            "swap_used_bytes": psutil.swap_memory().used,
        }
        resources["workers"] = {str(item["shard_index"]): item for item in active}
    status["current_host_resources"] = {
        "memory_available_bytes": current.available,
        "memory_total_bytes": current.total,
        "active_worker_processes": active,
    }
    status["analysis_mode"] = manifest.get("analysis_mode")
    status["constraint_id"] = manifest.get("constraint_id")
    status["run_directory"] = str(directory)
    return status


def aggregate_run(root: Path, run_id: str) -> dict:
    directory = run_dir(root, run_id)
    if not directory.is_dir():
        raise RunnerError(f"Run directory not found: {directory}")
    with exclusive_run_lock(directory):
        manifest = _load_manifest(directory)
        count = manifest["plan"]["shard_count"]
        checkpoint_paths = sorted((directory / "shards").glob("shard-*/checkpoint.json"))
        failure_paths = sorted((directory / "shards").glob("shard-*/failure.json"))
        report = aggregate_checkpoints(checkpoint_paths, count, "success", failure_paths)
        optimizer_counts = _optimization_counts(
            checkpoint_paths, manifest["plan"]["planned_optimizer_candidates"]
        )
        all_expected = manifest["plan"]["graph_ids"]
        report["planned_graphs"] = len(all_expected)
        report["planned_optimizer_candidates"] = manifest["plan"]["planned_optimizer_candidates"]
        report["optimizer_counts"] = optimizer_counts
        report["constraint_id"] = manifest["constraint_id"]
        report["effective_constraint_sha256"] = manifest["effective_constraint_sha256"]
        report["analysis_mode"] = "matching_only"
        state = report["status"]
        errors = report.get("errors", [])
        corrupt_evidence = (
            bool(report.get("corrupt_checkpoint_paths"))
            or (bool(checkpoint_paths) and state == "corrupt")
            or any(error.startswith((
                "invalid_", "malformed", "corrupt_", "duplicate_", "unsupported_",
                "missing_compatibility_config", "incompatible_shard", "mixed_config_hashes",
                "shard_count_mismatch", "global_expected_config_mismatch",
                "graph_assigned_to_multiple_shards", "graph_assignment_",
                "result_graph_id_mismatch", "completed_shard_missing_results",
                "candidate_log_result_mismatch",
            )) for error in errors)
        )
        report["aggregation_status"] = state
        if state == "incompatible":
            report["status"] = "incompatible"
        elif corrupt_evidence:
            report["status"] = "corrupt"
        elif manifest.get("status") == "failed" or state == "failed":
            report["status"] = "failed"
            report["errors"] = sorted(set(errors + ["local_manager_failed"]))
        elif manifest.get("status") == "interrupted":
            report["status"] = "interrupted"
        elif not checkpoint_paths and not failure_paths:
            report["status"] = "not_run"
            report["errors"] = []
        else:
            report["status"] = state
        report["overall_complete"] = report["status"] == "completed" and report["overall_complete"]
        report["manifest_status"] = manifest.get("status")
        report["run_id"] = run_id
        report["source_commit"] = manifest.get("git", {}).get("commit_sha")
        report["output"] = str(directory / "aggregate.json")
        _write_json(directory / "aggregate.json", report)
        return report


def _add_search_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--constraint-id",
        choices=("RF-F001", "RF-F002", "RF-T001", "RF-T002", "RF-T003", "RF-T004"),
        default=None,
        help="Required for new CLI jobs: use RF-F002 for current formal jobs or an explicit historical/trial ID",
    )
    parser.add_argument("--series-mode", choices=("HV", "HQ", "both"), default="HV")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--per-bin", type=int, default=1)
    parser.add_argument("--starts", type=int, default=1)
    parser.add_argument("--layouts", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--coarse-points", type=int, default=2)
    parser.add_argument("--validation-points", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261013)
    parser.add_argument("--max-variable-layouts", type=int, default=2)
    parser.add_argument("--require-lqp02", action="store_true")
    parser.add_argument("--require-both-series", action="store_true")
    parser.add_argument("--max-topology-graphs", type=int, default=4)
    parser.add_argument("--shard-count", type=int, default=4)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-graphs-per-batch", type=int, default=1)
    parser.add_argument("--max-batch-seconds", type=int, default=600)
    parser.add_argument("--memory-min-free-mib", type=float, default=1536.0)
    parser.add_argument("--monitor-interval", type=float, default=5.0)
    parser.add_argument("--memory-stall-timeout", type=float, default=300.0)
    parser.add_argument("--max-runtime", type=float, default=0.0,
                        help="wall-time limit in seconds; 0 means no limit")
    parser.add_argument("--force-kill-after", type=float, default=120.0,
                        help="escalate only after this graceful-stop wait; 0 disables escalation")
    parser.add_argument("--root", default=DEFAULT_RUN_ROOT)


def _positive_options(args, parser) -> None:
    for name in ("attempts", "per_bin", "starts", "layouts", "iterations", "coarse_points",
                 "validation_points", "max_variable_layouts", "max_topology_graphs",
                 "shard_count", "max_graphs_per_batch", "max_batch_seconds"):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.validation_points < 2:
        parser.error("--validation-points must be at least 2")
    runtime_values = (
        args.memory_min_free_mib, args.monitor_interval, args.memory_stall_timeout,
        args.max_runtime, args.force_kill_after,
    )
    if not all(math.isfinite(value) for value in runtime_values):
        parser.error("memory and runtime settings must be finite numbers")
    if args.memory_min_free_mib < 0 or args.monitor_interval <= 0 or args.memory_stall_timeout < 0:
        parser.error("memory threshold, monitor interval, and stall timeout are invalid")
    if args.max_runtime < 0 or args.force_kill_after < 0:
        parser.error("runtime limits cannot be negative")
    if args.require_both_series and args.series_mode != "both":
        parser.error("--require-both-series requires --series-mode both")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("plan", "run"):
        command = subparsers.add_parser(operation)
        _add_search_arguments(command)
    status = subparsers.add_parser("status")
    status.add_argument("run_id")
    status.add_argument("--root", default=DEFAULT_RUN_ROOT)
    resume = subparsers.add_parser("resume")
    resume.add_argument("run_id")
    resume.add_argument("--workers", type=int, default=None)
    resume.add_argument("--memory-min-free-mib", type=float, default=None)
    resume.add_argument("--monitor-interval", type=float, default=None)
    resume.add_argument("--memory-stall-timeout", type=float, default=None)
    resume.add_argument("--max-runtime", type=float, default=None)
    resume.add_argument("--force-kill-after", type=float, default=None)
    resume.add_argument("--root", default=DEFAULT_RUN_ROOT)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("run_id")
    aggregate.add_argument("--root", default=DEFAULT_RUN_ROOT)
    return parser


def main(argv=None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.operation in {"plan", "run"} and args.constraint_id is None:
        parser.error("New jobs require explicit --constraint-id (current formal: RF-F002)")
    try:
        if args.operation == "plan":
            _positive_options(args, parser)
            _validate_workers(args.workers, args.shard_count)
            plan = build_plan(search_from_namespace(args), args.shard_count)
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            return 0
        if args.operation == "run":
            _positive_options(args, parser)
            code, run_id, directory = start_run(Path(args.root), args)
            print(json.dumps({"run_id": run_id, "run_directory": str(directory),
                              "status": _load_manifest(directory).get("status"),
                              "exit_code": code}, ensure_ascii=False))
            return code
        if args.operation == "status":
            print(json.dumps(status_run(Path(args.root), args.run_id), indent=2, ensure_ascii=False))
            return 0
        if args.operation == "resume":
            runtime_values = (
                args.memory_min_free_mib, args.monitor_interval, args.memory_stall_timeout,
                args.max_runtime, args.force_kill_after,
            )
            if not all(value is None or math.isfinite(value) for value in runtime_values):
                raise RunnerError("memory and runtime settings must be finite numbers")
            if args.workers is not None:
                _validate_workers(args.workers, 64)
            if args.monitor_interval is not None and args.monitor_interval <= 0:
                raise RunnerError("monitor-interval must be positive")
            if args.memory_min_free_mib is not None and args.memory_min_free_mib < 0:
                raise RunnerError("memory threshold cannot be negative")
            if args.memory_stall_timeout is not None and args.memory_stall_timeout < 0:
                raise RunnerError("memory stall timeout cannot be negative")
            if ((args.max_runtime is not None and args.max_runtime < 0)
                    or (args.force_kill_after is not None and args.force_kill_after < 0)):
                raise RunnerError("runtime limits cannot be negative")
            code = resume_run(Path(args.root), args.run_id, workers=args.workers,
                              memory_min_free_mib=args.memory_min_free_mib,
                              monitor_interval=args.monitor_interval,
                              memory_stall_timeout=args.memory_stall_timeout,
                              max_runtime=args.max_runtime,
                              force_kill_after=args.force_kill_after)
            print(json.dumps({"run_id": args.run_id, "status": _load_manifest(
                run_dir(Path(args.root), args.run_id)).get("status"), "exit_code": code}))
            return code
        if args.operation == "aggregate":
            report = aggregate_run(Path(args.root), args.run_id)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["status"] in {"completed", "in_progress", "interrupted", "not_run"} else 1
    except (RunnerError, OSError, ValueError, KeyError) as exc:
        print(f"local-p4: error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
