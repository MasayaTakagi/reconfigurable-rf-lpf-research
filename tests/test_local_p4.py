"""Tests for local P4-A orchestration, deterministic sharding, and resource guards."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import local_p4


class LocalP4PlanningTests(unittest.TestCase):
    def search(self, constraint_id="RF-F001"):
        return {
            "constraint_id": constraint_id,
            "series_mode": "HV",
            "attempts": 1,
            "per_bin": 1,
            "starts": 1,
            "layouts": 1,
            "iterations": 1,
            "coarse_points": 2,
            "validation_points": 3,
            "seed": 20261013,
            "max_variable_layouts": 2,
            "require_lqp02": False,
            "require_both_series": False,
            "max_topology_graphs": 4,
            "max_graphs_per_batch": 1,
            "max_batch_seconds": 600,
        }

    def test_plan_is_deterministic_and_disjoint_with_trial_provenance(self):
        formal_a = local_p4.build_plan(self.search("RF-F001"), 4)
        formal_b = local_p4.build_plan(self.search("RF-F001"), 4)
        trial = local_p4.build_plan(self.search("RF-T002"), 4)
        self.assertEqual(formal_a["graph_ids"], formal_b["graph_ids"])
        self.assertEqual(formal_a["shard_assignments"], formal_b["shard_assignments"])
        self.assertEqual(formal_a["p4_config_hash"], formal_b["p4_config_hash"])
        assigned = [graph_id for group in formal_a["shard_assignments"].values()
                    for graph_id in group]
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertEqual(sorted(assigned), sorted(formal_a["graph_ids"]))
        self.assertEqual(formal_a["analysis_mode"], "matching_only")
        self.assertEqual(formal_a["constraint_id"], "RF-F001")
        self.assertEqual(trial["constraint_id"], "RF-T002")
        self.assertNotEqual(formal_a["effective_constraint_sha256"],
                            trial["effective_constraint_sha256"])
        self.assertNotEqual(formal_a["p4_config_hash"], trial["p4_config_hash"])

    def test_memory_gate_pauses_below_threshold(self):
        threshold = 1536 * 1024 * 1024
        self.assertTrue(local_p4.memory_allows_launch(threshold, threshold))
        self.assertFalse(local_p4.memory_allows_launch(threshold - 1, threshold))

    def test_nonfinite_runtime_settings_are_rejected(self):
        parser = local_p4.make_parser()
        args = parser.parse_args(["run", "--memory-min-free-mib", "nan"])
        with self.assertRaises(SystemExit):
            local_p4._positive_options(args, parser)

    def test_manager_does_not_launch_below_memory_threshold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = local_p4.make_parser().parse_args([
                "run", "--root", str(root), "--shard-count", "1", "--workers", "1",
                "--memory-min-free-mib", "1536", "--monitor-interval", "0.01",
                "--memory-stall-timeout", "0.03",
            ])
            low_memory = {
                "total_bytes": 8 * 1024**3, "available_bytes": 1024**3,
                "used_bytes": 7 * 1024**3, "percent": 87.5, "swap_used_bytes": 0,
            }
            with mock.patch.object(local_p4, "_current_memory", return_value=low_memory):
                code, run_id, directory = local_p4.start_run(root, args)
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 130)
            self.assertEqual(manifest["status"], "interrupted")
            self.assertEqual(manifest["resource_summary"]["maximum_process_count"], 0)
            log = (directory / "logs" / "manager.jsonl").read_text(encoding="utf-8")
            self.assertNotIn('"event": "worker_started"', log)
            self.assertIn('"event": "memory_launch_paused"', log)

    def test_same_run_cannot_be_locked_twice(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with local_p4.exclusive_run_lock(directory):
                with self.assertRaises(local_p4.RunLockedError):
                    with local_p4.exclusive_run_lock(directory):
                        self.fail("a second manager acquired the same run")

    def test_child_keeps_shard_lock_after_parent_closes_fd(self):
        # _spawn closes the manager's descriptor immediately. The independently
        # running child must continue holding worker.lock across exec.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = local_p4.make_parser().parse_args([
                "run", "--root", str(root), "--shard-count", "1", "--workers", "1",
            ])
            run_id, directory = local_p4.create_run(root, args)
            manager = local_p4.LocalRunManager(
                directory, workers=1, memory_min_free_mib=0,
                monitor_interval=0.1, memory_stall_timeout=1,
                max_runtime=0, force_kill_after=0,
            )
            manager._prepare_shard(0, resume=False)
            sleeper = [sys.executable, "-c", "import time; time.sleep(30)"]
            with mock.patch.object(manager, "_worker_command", return_value=sleeper):
                manager._spawn(0, resume=False)
            child = manager._active[0]["process"]
            try:
                self.assertIsNone(child.poll())
                with self.assertRaisesRegex(local_p4.RunLockedError, "still active"):
                    local_p4.assert_no_active_shard_workers(directory, 1)
                before = (directory / "manifest.json").read_bytes()
                with self.assertRaisesRegex(local_p4.RunLockedError, "still active"):
                    local_p4.resume_run(root, run_id, workers=1)
                self.assertEqual((directory / "manifest.json").read_bytes(), before)
                self.assertIsNone(child.poll())
            finally:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=5)
                except local_p4.subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
                manager._active[0]["log"].close()
            # The lock file persists, but its advisory lock was released.
            self.assertTrue((directory / "shards/shard-0/worker.lock").exists())
            local_p4.assert_no_active_shard_workers(directory, 1)

    def test_source_mismatch_rejects_resume_before_checkpoint_access(self):
        saved = {"compatibility": {"uv_lock_sha256": "old-lock"}}
        current = {
            "source_fingerprints": {}, "uv_lock_sha256": "new-lock",
            "numerical": {}, "cpu": {"model": "cpu"},
        }
        with mock.patch.object(local_p4, "environment_snapshot", return_value=current):
            with self.assertRaisesRegex(local_p4.RunnerCompatibilityError, "uv_lock_sha256"):
                local_p4.verify_resume_compatibility(Path("unused"), saved)

    def test_corrupt_checkpoint_is_rejected_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = local_p4.make_parser().parse_args([
                "run", "--root", str(root), "--shard-count", "1", "--workers", "1",
            ])
            run_id, directory = local_p4.create_run(root, args)
            checkpoint = directory / "shards" / "shard-0" / "checkpoint.json"
            checkpoint.write_bytes(b"{broken-checkpoint")
            before = checkpoint.read_bytes()
            with self.assertRaisesRegex(local_p4.RunnerCompatibilityError, "corrupt"):
                local_p4.resume_run(root, run_id, workers=1, monitor_interval=0.1)
            self.assertEqual(checkpoint.read_bytes(), before)

    def test_clean_partial_batch_exit_after_stop_is_interrupted(self):
        class ExitedWorker:
            def poll(self):
                return 0

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = local_p4.make_parser().parse_args([
                "run", "--root", str(root), "--shard-count", "1", "--workers", "1",
            ])
            _run_id, directory = local_p4.create_run(root, args)
            manager = local_p4.LocalRunManager(
                directory, workers=1, memory_min_free_mib=1536,
                monitor_interval=0.1, memory_stall_timeout=1,
                max_runtime=0, force_kill_after=0,
            )
            manager.status["shards"] = {"0": {"status": "running", "attempts": 1}}
            (directory / "shards" / "shard-0" / "checkpoint.json").write_text(
                json.dumps({"status": "partial"}), encoding="utf-8"
            )
            log = (directory / "shards" / "shard-0" / "worker.log").open("ab")
            manager._active[0] = {
                "process": ExitedWorker(), "log": log, "pid": 12345,
                "started_monotonic": local_p4.time.monotonic(),
                "rss_peak_bytes": 0,
            }
            manager.stop_reason = "max_runtime_reached"
            manager._finish_worker(0)
            self.assertEqual(manager.status["shards"]["0"]["status"], "interrupted")

    def test_worker_nonzero_exit_is_recorded_as_failed(self):
        class ExitedWorker:
            def poll(self):
                return 17

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = local_p4.make_parser().parse_args([
                "run", "--root", str(root), "--shard-count", "1", "--workers", "1",
            ])
            _run_id, directory = local_p4.create_run(root, args)
            manager = local_p4.LocalRunManager(
                directory, workers=1, memory_min_free_mib=1536,
                monitor_interval=0.1, memory_stall_timeout=1,
                max_runtime=0, force_kill_after=0,
            )
            manager.status["shards"] = {"0": {"status": "running", "attempts": 1}}
            log = (directory / "shards" / "shard-0" / "worker.log").open("ab")
            manager._active[0] = {
                "process": ExitedWorker(), "log": log, "pid": 12345,
                "started_monotonic": local_p4.time.monotonic(),
                "rss_peak_bytes": 0,
            }
            manager._finish_worker(0)
            self.assertEqual(manager.status["shards"]["0"]["status"], "failed")
            self.assertEqual(manager.status["shards"]["0"]["exit_code"], 17)

    def test_empty_aggregate_is_not_reported_as_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "fixture-run"
            directory = root / run_id
            (directory / "shards").mkdir(parents=True)
            manifest = {
                "schema_version": local_p4.SCHEMA_VERSION,
                "run_id": run_id,
                "status": "created",
                "plan": {
                    "shard_count": 2,
                    "graph_ids": ["a" * 64],
                    "planned_optimizer_candidates": 3,
                },
                "constraint_id": "RF-F001",
                "effective_constraint_sha256": "hash",
                "git": {"commit_sha": "fixture"},
            }
            (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            report = local_p4.aggregate_run(root, run_id)
            self.assertEqual(report["status"], "not_run")
            self.assertFalse(report["overall_complete"])
            self.assertEqual(report["missing_shards"], [0, 1])
            self.assertEqual(report["analysis_mode"], "matching_only")

    def test_aggregation_distinguishes_worker_failure_from_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = local_p4.make_parser().parse_args([
                "run", "--root", str(root), "--shard-count", "1", "--workers", "1",
            ])
            _run_id, directory = local_p4.create_run(root, args)
            manifest_path = directory / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "failed"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            shard_dir = directory / "shards" / "shard-0"
            (shard_dir / "failure.json").write_text(json.dumps({
                "shard_index": 0, "state": "failed", "message": "worker exited nonzero",
            }), encoding="utf-8")
            report = local_p4.aggregate_run(root, _run_id)
            self.assertEqual(report["status"], "failed")
            self.assertFalse(report["overall_complete"])

            (shard_dir / "failure.json").unlink()
            (shard_dir / "checkpoint.json").write_text("{broken", encoding="utf-8")
            report = local_p4.aggregate_run(root, _run_id)
            self.assertEqual(report["status"], "corrupt")
            self.assertFalse(report["overall_complete"])

    def test_one_and_two_worker_runs_are_numerically_equivalent_and_resumable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reports = {}
            for workers in (1, 2):
                argv = [
                    "run", "--root", str(root), "--constraint-id", "RF-F001",
                    "--series-mode", "HV", "--attempts", "1", "--per-bin", "1",
                    "--starts", "1", "--layouts", "1", "--iterations", "1",
                    "--coarse-points", "2", "--validation-points", "3",
                    "--seed", "20261013", "--max-variable-layouts", "2",
                    "--max-topology-graphs", "4", "--shard-count", "4",
                    "--workers", str(workers), "--max-graphs-per-batch", "1",
                    "--max-batch-seconds", "600", "--memory-min-free-mib", "0",
                    "--monitor-interval", "0.1", "--memory-stall-timeout", "10",
                    "--max-runtime", "90",
                ]
                args = local_p4.make_parser().parse_args(argv)
                code, run_id, directory = local_p4.start_run(root, args)
                self.assertEqual(code, 0)
                manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["status"], "completed")
                self.assertEqual(manifest["analysis_mode"], "matching_only")
                self.assertEqual(manifest["optimizer_counts"]["planned"],
                                 manifest["optimizer_counts"]["completed"])
                self.assertEqual(manifest["optimizer_counts"]["unrun"], 0)
                self.assertLessEqual(manifest["resource_summary"]["maximum_process_count"], workers)
                self.assertGreater(manifest["resource_summary"]["peak_total_worker_rss_bytes"], 0)
                self.assertTrue(manifest["shard_process_history"])
                self.assertTrue(all(
                    process["exit_code"] == 0
                    for entries in manifest["shard_process_history"].values()
                    for process in entries
                ))
                report = local_p4.aggregate_run(root, run_id)
                self.assertEqual(report["status"], "completed")
                self.assertTrue(report["overall_complete"])
                self.assertEqual(report["optimized_graphs"], 4)
                self.assertEqual(sorted(manifest["plan"]["graph_ids"]),
                                 sorted(row["graph_id"] for row in report["results"]))
                self.assertEqual(report["optimizer_counts"]["completed"], 7)
                reports[workers] = (run_id, directory, report)

            sequential = reports[1][2]["results"]
            parallel = reports[2][2]["results"]
            self.assertEqual([row["graph_id"] for row in sequential],
                             [row["graph_id"] for row in parallel])
            self.assertEqual(len({row["graph_id"] for row in parallel}), len(parallel))
            for first, second in zip(sequential, parallel):
                self.assertEqual(first["best_candidate_key"], second["best_candidate_key"])
                self.assertAlmostEqual(first["coarse_il_db"], second["coarse_il_db"], places=12)
                self.assertEqual(first["values"], second["values"])
                self.assertEqual(
                    [(item["candidate_key"], item["converged"], item["result_values"],
                      item["objective_evaluation_count"])
                     for item in first["optimization_runs"]],
                    [(item["candidate_key"], item["converged"], item["result_values"],
                      item["objective_evaluation_count"])
                     for item in second["optimization_runs"]],
                )

            # A manager-level resume skips already completed shards and does not
            # append duplicate graph/candidate results.
            run_id, directory, before = reports[2]
            code = local_p4.resume_run(root, run_id, workers=2, monitor_interval=0.1)
            self.assertEqual(code, 0)
            after = local_p4.aggregate_run(root, run_id)
            self.assertEqual(after["status"], "completed")
            self.assertEqual(after["optimized_graphs"], before["optimized_graphs"])
            self.assertEqual(after["optimizer_counts"], before["optimizer_counts"])
            updated = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["resume_count"], 1)


if __name__ == "__main__":
    unittest.main()
