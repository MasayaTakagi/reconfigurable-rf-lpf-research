#!/usr/bin/env python3
"""One bounded, restartable RF-F002 full-LPF optimization task."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import tempfile
import time
import traceback

import importlib.metadata
import psutil

# Set numerical-library concurrency before importing NumPy/SciPy.
for _name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))

from lpf.constraint_versions import load_constraint  # noqa: E402


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


def run_task(task_path: Path, output_path: Path, lock_fd: int) -> int:
    lock_stream = os.fdopen(int(lock_fd), "a+", encoding="utf-8")
    wall_started = time.monotonic()
    cpu_started = time.process_time()
    task_id = "unknown"
    task_payload = {}
    try:
        task_payload = json.loads(task_path.read_text(encoding="utf-8"))
        task_id = task_payload["task_id"]
        lock_stream.seek(0)
        lock_stream.truncate()
        lock_stream.write(json.dumps({"pid": os.getpid(), "task_id": task_id,
                                      "started_at": time.time()}))
        lock_stream.flush()
        os.fsync(lock_stream.fileno())
        task = task_payload["task"]
        config = task_payload["optimization"]
        task_id = task_payload["task_id"]
        # Guard direct worker invocation as well as manager-controlled execution.
        task_digest = hashlib.sha256(json.dumps(
            task, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")).hexdigest()
        if task_digest != task_payload.get("task_config_sha256"):
            raise ValueError("Worker refused: task payload checksum mismatch")
        from full_lpf import FullLPFProblem  # noqa: PLC0415

        graph_row = task["graph"]
        graph = (int(graph_row[0]), tuple(tuple(edge) for edge in graph_row[1]))
        layout = {
            "edges": tuple(tuple(edge) for edge in task["variable_layout"]["edges"]),
            "roles": tuple(task["variable_layout"]["roles"]),
        }
        policy = load_constraint("RF-F002")
        problem = FullLPFProblem(
            graph,
            layout,
            task["initial_coupling"],
            constraint_id="RF-F002",
            passband_points=int(config["passband_points"]),
            stopband_points=int(config["stopband_points"]),
            physical_order=task["physical_order"],
            resolved_policy=policy,
        )
        initial = problem.initial_vector(
            task["initial_base_values"],
            coupling_values=task.get("initial_coupling_values"),
        )
        result = problem.optimize(
            initial,
            harmonic_targets=tuple(config["harmonic_targets_db"]),
            maxiter=int(config["maxiter_per_stage"]),
            ftol=float(config["ftol"]),
        )
        result.update({
            "task_id": task_id,
            "topology_sha256": task_payload["topology_sha256"],
            "start_sha256": task_payload["start_sha256"],
            "task_config_sha256": task_payload["task_config_sha256"],
            "seed_label": task.get("seed_label"),
            "worker_pid": os.getpid(),
            "worker_wall_seconds": round(time.monotonic() - wall_started, 6),
            "worker_cpu_seconds": round(time.process_time() - cpu_started, 6),
            "worker_peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                                          (1024 if platform.system() == "Linux" else 1)),
            "worker_runtime": {
                "python": platform.python_version(),
                "numpy": importlib.metadata.version("numpy"),
                "scipy": importlib.metadata.version("scipy"),
                "memory_available_bytes_at_completion": psutil.virtual_memory().available,
            },
            "worker_threads": {name: os.environ.get(name) for name in
                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS",
                                "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
            "worker_status": "completed",
        })
        result["result_integrity_sha256"] = hashlib.sha256(json.dumps(
            result, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")).hexdigest()
        _atomic_json(output_path, result)
        print(json.dumps({
            "task_id": task_id,
            "worker_status": "completed",
            "converged": result["converged"],
            "best_found_category": result["best_found_category"],
            "worst_il_db": result["worst_il_db"],
            "min_h2_db": result["min_h2_db"],
            "min_h3_db": result["min_h3_db"],
        }, sort_keys=True))
        return 0
    except Exception as error:  # Preserve bounded failures for diagnosis/resume.
        _atomic_json(output_path, {
            "task_id": task_id,
            "topology_sha256": task_payload.get("topology_sha256"),
            "start_sha256": task_payload.get("start_sha256"),
            "task_config_sha256": task_payload.get("task_config_sha256"),
            "worker_status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        })
        print(json.dumps({"task_id": task_id, "worker_status": "failed",
                          "error_type": type(error).__name__, "error": str(error)}),
              file=sys.stderr)
        return 1
    finally:
        lock_stream.close()


def main() -> int:
    if len(sys.argv) != 4:
        print(f"usage: {Path(sys.argv[0]).name} TASK.json RESULT.json WORKER_LOCK_FD", file=sys.stderr)
        return 2
    return run_task(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))


if __name__ == "__main__":
    raise SystemExit(main())
