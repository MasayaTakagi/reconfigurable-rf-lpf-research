"""Safety, resume, hash and aggregation tests for the full-LPF-only manager."""
import fcntl
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from local_full_lpf import aggregate, plan, run_batch, _prepare_config  # noqa: E402


def _task(label, first_l=2.0):
    return {
        "seed_label": label,
        "graph": [3, [[1, 2, "LQP02HV"]]],
        "variable_layout": {"edges": [[1, 0], [2, 0]], "roles": [None, None]},
        "physical_order": [0],
        "initial_coupling": [[1.0]],
        "initial_base_values": [first_l] + [0.4] * 12,
    }


def _config():
    return {
        "constraint_id": "RF-F002",
        "objective": "full_lpf",
        "optimization": {
            "harmonic_targets_db": [30.0],
            "maxiter_per_stage": 1,
            "ftol": 1e-6,
            "passband_points": 2,
            "stopband_points": 2,
            "max_attempts": 2,
        },
        "tasks": [_task("start-a", 2.0), _task("start-b", 2.1)],
    }


class LocalFullLPFManagerTests(unittest.TestCase):
    def test_formal_full_lpf_config_deduplicates_topology_but_keeps_distinct_starts(self):
        config, tasks = _prepare_config(json.dumps(_config()).encode())
        self.assertEqual(config["constraint_id"], "RF-F002")
        self.assertEqual(config["objective"], "full_lpf")
        self.assertEqual(len(tasks), 2)
        self.assertEqual(len({row["topology_sha256"] for row in tasks}), 1)
        self.assertEqual(len({row["task_id"] for row in tasks}), 2)

    def test_rejects_trial_matching_only_duplicate_starts_and_three_variable_caps(self):
        cfg = _config()
        cfg["constraint_id"] = "RF-T004"
        with self.assertRaisesRegex(ValueError, "RF-F002 only"):
            _prepare_config(json.dumps(cfg).encode())
        cfg = _config()
        cfg["objective"] = "matching_only"
        with self.assertRaisesRegex(ValueError, "matching_only"):
            _prepare_config(json.dumps(cfg).encode())
        cfg = _config()
        cfg["tasks"] = [_task("same"), _task("different-label")]
        with self.assertRaisesRegex(ValueError, "Duplicate topology/start"):
            _prepare_config(json.dumps(cfg).encode())
        cfg = _config()
        cfg["tasks"] = [_task("three-cap")]
        cfg["tasks"][0]["variable_layout"]["edges"].append([0, 2])
        cfg["tasks"][0]["variable_layout"]["roles"].append("bridge")
        cfg["tasks"][0]["initial_base_values"].extend([0.4] * 6)
        with self.assertRaisesRegex(ValueError, "at most two"):
            _prepare_config(json.dumps(cfg).encode())

    def test_resource_gate_stop_resume_and_exact_aggregation(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            config_path = base / "config.json"
            run_dir = base / "run"
            config_path.write_text(json.dumps(_config()), encoding="utf-8")
            plan(config_path, run_dir)

            blocked = run_batch(run_dir, workers=2, max_runtime_seconds=10,
                                max_tasks=2, task_timeout_seconds=10,
                                min_free_mib=1_000_000_000)
            self.assertEqual(blocked["state"], "blocked_low_ram")
            self.assertEqual(blocked["task_counts"]["completed"], 0)

            resumed = run_batch(run_dir, workers=2, max_runtime_seconds=120,
                                max_tasks=2, task_timeout_seconds=90,
                                min_free_mib=256, resume=True)
            self.assertEqual(resumed["state"], "completed")
            self.assertEqual(resumed["task_counts"]["completed"], 2)
            report = aggregate(run_dir)
            self.assertTrue(report["scope_complete"])
            self.assertEqual(report["completed_result_count"], 2)
            self.assertEqual(report["missing_task_ids"], [])
            self.assertEqual(len(report["observations"]), 2)
            for row in report["observations"]:
                self.assertIn("solver_converged", row)
                self.assertIn("mandatory_30db_met_on_dense_grid", row)
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["invocation_count"], 2)
            self.assertTrue(all(task["state"] == "completed" for task in status["tasks"]))

            # A completed result may not be silently adopted after editing a metric.
            result_path = run_dir / status["tasks"][0]["result_path"]
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertIn("result_integrity_sha256", result)
            result["worst_il_db"] += 0.1
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "completed result checksum mismatch"):
                aggregate(run_dir)
            with self.assertRaisesRegex(ValueError, "completed result checksum mismatch"):
                run_batch(run_dir, workers=1, max_runtime_seconds=30,
                          max_tasks=1, task_timeout_seconds=30,
                          min_free_mib=256, resume=True)

    def test_modified_task_file_cannot_be_run_or_aggregated(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            config_path = base / "config.json"
            run_dir = base / "run"
            config_path.write_text(json.dumps(_config()), encoding="utf-8")
            plan(config_path, run_dir)
            task_path = next((run_dir / "tasks").glob("*.json"))
            task_file = json.loads(task_path.read_text(encoding="utf-8"))
            task_file["task"]["initial_base_values"][0] += 0.1
            task_path.write_text(json.dumps(task_file), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "task payload mismatch"):
                aggregate(run_dir)
            with self.assertRaisesRegex(ValueError, "task payload mismatch"):
                run_batch(run_dir, workers=1, max_runtime_seconds=30,
                          max_tasks=1, task_timeout_seconds=30, min_free_mib=256)

    def test_worker_rejects_modified_task_even_without_manager(self):
        import os
        from full_lpf_worker import run_task

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            config_path = base / "config.json"
            run_dir = base / "run"
            config_path.write_text(json.dumps(_config()), encoding="utf-8")
            plan(config_path, run_dir)
            task_path = next((run_dir / "tasks").glob("*.json"))
            task_file = json.loads(task_path.read_text(encoding="utf-8"))
            task_file["task"]["initial_base_values"][0] += 0.1
            task_path.write_text(json.dumps(task_file), encoding="utf-8")
            output_path = base / "worker-rejected.json"
            lock_fd = os.open(base / "worker.lock", os.O_RDWR | os.O_CREAT, 0o600)
            try:
                exit_code = run_task(task_path, output_path, lock_fd)
            finally:
                try:
                    os.close(lock_fd)
                except OSError:
                    pass  # run_task closes the inherited descriptor.
            self.assertEqual(exit_code, 1)
            worker_result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(worker_result["worker_status"], "failed")
            self.assertIn("task payload checksum mismatch", worker_result["error"])

    def test_resume_refuses_changed_sources_and_duplicate_or_missing_results_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            config_path = base / "config.json"
            run_dir = base / "run"
            config_path.write_text(json.dumps(_config()), encoding="utf-8")
            plan(config_path, run_dir)
            incomplete = aggregate(run_dir)
            self.assertFalse(incomplete["scope_complete"])
            self.assertEqual(len(incomplete["missing_task_ids"]), 2)

            worker_lock_path = run_dir / "locks" / "orphan.lock"
            worker_lock_path.parent.mkdir(parents=True)
            with worker_lock_path.open("a+") as worker_lock:
                fcntl.flock(worker_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(RuntimeError, "still holds"):
                    aggregate(run_dir)
                fcntl.flock(worker_lock.fileno(), fcntl.LOCK_UN)

            changed = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
            changed["optimization"]["maxiter_per_stage"] = 2
            (run_dir / "config.json").write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "configuration hash"):
                aggregate(run_dir)


if __name__ == "__main__":
    unittest.main()
