import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))
from p4_sharding import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointCompatibilityError,
    CheckpointCorruptError,
    aggregate_checkpoints,
    atomic_write_json,
    canonical_config_hash,
    canonical_graph_id,
    load_checkpoint,
    shard_for_graph,
)


def fixture_ids(shard_count=2, count=8):
    values = []
    for index in range(1000):
        graph_id = f"{index:016x}" + "0" * 48
        if not values or len(values) < count:
            values.append(graph_id)
        if {shard_for_graph(value, shard_count) for value in values} == set(range(shard_count)) and len(values) >= count:
            return values
    raise AssertionError("could not create IDs covering every shard")


def fixture_config(global_ids):
    return {"topology_search": {"selected_graph_ids": global_ids}, "starts": 1}


def make_checkpoint(index, *, global_ids, shard_count=2, status="completed",
                    completed_ids=None, config=None, source_commit="commit-a"):
    expected = [graph_id for graph_id in global_ids
                if shard_for_graph(graph_id, shard_count) == index]
    completed_ids = expected if completed_ids is None and status == "completed" else (completed_ids or [])
    rows = []
    for graph_id in completed_ids:
        rows.append({
            "graph_id": graph_id,
            "converged": False,
            "coarse_il_db": 0.25,
            "optimization_runs": [{
                "graph_id": graph_id,
                "candidate_key": f"{graph_id}:0:0",
                "layout_index": 0,
                "start_index": 0,
                "initial_values": [2.0, 1.0],
                "rng_seed": 123,
                "objective_evaluation_count": 4,
            }],
        })
    run_config = config or fixture_config(global_ids)
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "status": status,
        "config_hash": canonical_config_hash(run_config),
        "run_config": run_config,
        "source_commit": source_commit,
        "source_commits": [source_commit],
        "execution_history": [{"source_commit": source_commit}],
        "shard_index": index,
        "shard_count": shard_count,
        "global_expected_graph_ids": global_ids,
        "expected_graph_ids": expected,
        "completed_graph_ids": completed_ids,
        "results": rows,
        "partial_optimization_runs": {},
        "candidate_execution_log": [
            {
                "graph_id": graph_id,
                "candidate_key": f"{graph_id}:0:0",
                "execution_segment_index": 0,
                "status": "completed",
                "objective_evaluation_count": 4,
            }
            for graph_id in completed_ids
        ],
        "interrupted_candidate_attempts": [],
        "unit_execution_log": [{"graph_id": graph_id, "status": "completed"}
                               for graph_id in completed_ids],
    }


class P4ShardingTests(unittest.TestCase):
    def test_graph_id_ignores_edge_order_and_internal_node_labels(self):
        first = (5, [(1, 3, "LQP01"), (3, 2, "PCB_L"), (0, 4, "GJM01")])
        relabeled = (5, [(0, 3, "GJM01"), (2, 4, "PCB_L"), (4, 1, "LQP01")])
        self.assertEqual(canonical_graph_id(first), canonical_graph_id(relabeled))

    def test_shard_assignment_is_stable_and_bounded(self):
        graph_id = canonical_graph_id((3, [(1, 2, "LQP01"), (0, 1, "GJM01")]))
        self.assertEqual(shard_for_graph(graph_id, 4), shard_for_graph(graph_id, 4))
        self.assertIn(shard_for_graph(graph_id, 4), range(4))
        with self.assertRaises(ValueError):
            shard_for_graph(graph_id, 0)
        with self.assertRaises(ValueError):
            shard_for_graph("z" * 64, 2)

    def test_config_hash_is_independent_of_mapping_order(self):
        self.assertEqual(
            canonical_config_hash({"a": 1, "b": {"x": 2, "y": 3}}),
            canonical_config_hash({"b": {"y": 3, "x": 2}, "a": 1}),
        )

    def test_atomic_checkpoint_and_resume_compatibility(self):
        ids = fixture_ids(shard_count=1)
        config = fixture_config(ids)
        payload = make_checkpoint(0, global_ids=ids, shard_count=1, config=config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shard" / "checkpoint.json"
            atomic_write_json(path, payload)
            loaded = load_checkpoint(
                path, config_hash=payload["config_hash"], shard_index=0,
                shard_count=1, expected_graph_ids=payload["expected_graph_ids"],
            )
            self.assertEqual(loaded, payload)
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])
            with self.assertRaises(CheckpointCompatibilityError):
                load_checkpoint(
                    path, config_hash="different", shard_index=0,
                    shard_count=1, expected_graph_ids=payload["expected_graph_ids"],
                )

    def test_runner_commit_metadata_does_not_make_compatible_shards_incompatible(self):
        ids = fixture_ids()
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, commit in enumerate(("commit-a", "commit-b")):
                path = Path(directory) / str(index) / "checkpoint.json"
                atomic_write_json(path, make_checkpoint(
                    index, global_ids=ids, source_commit=commit,
                ))
                paths.append(path)
            report = aggregate_checkpoints(paths, expected_shards=2)
        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["overall_complete"])
        self.assertEqual(report["source_commits"], ["commit-a", "commit-b"])

    def test_partial_batch_is_in_progress_not_complete(self):
        ids = fixture_ids()
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index in range(2):
                expected = [item for item in ids if shard_for_graph(item, 2) == index]
                partial = expected[:1]
                path = Path(directory) / str(index) / "checkpoint.json"
                atomic_write_json(path, make_checkpoint(
                    index, global_ids=ids, status="partial", completed_ids=partial,
                ))
                paths.append(path)
            report = aggregate_checkpoints(paths, 2)
        self.assertEqual(report["status"], "in_progress")
        self.assertFalse(report["overall_complete"])
        self.assertGreater(report["completed_optimizer_candidates"], 0)

    def test_missing_artifact_is_incomplete_and_marks_unrun_shard(self):
        ids = fixture_ids()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "0" / "checkpoint.json"
            atomic_write_json(path, make_checkpoint(0, global_ids=ids))
            report = aggregate_checkpoints([path], 2)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["missing_shards"], [1])
        self.assertEqual(report["shard_states"][1]["status"], "not_run")
        self.assertFalse(report["overall_complete"])

    def test_overlapping_graph_ids_are_rejected(self):
        ids = fixture_ids()
        expected_zero = [item for item in ids if shard_for_graph(item, 2) == 0]
        expected_one = [item for item in ids if shard_for_graph(item, 2) == 1]
        overlap = expected_zero[0]
        with tempfile.TemporaryDirectory() as directory:
            a = make_checkpoint(0, global_ids=ids)
            b = make_checkpoint(1, global_ids=ids, status="partial", completed_ids=[])
            b["expected_graph_ids"] = [overlap] + expected_one[1:]
            paths = []
            for index, item in enumerate((a, b)):
                path = Path(directory) / str(index) / "checkpoint.json"
                atomic_write_json(path, item)
                paths.append(path)
            report = aggregate_checkpoints(paths, 2)
        self.assertNotEqual(report["status"], "completed")
        self.assertIn("graph_assigned_to_multiple_shards", report["errors"])

    def test_mixed_search_conditions_are_incompatible(self):
        ids = fixture_ids()
        config = fixture_config(ids)
        other = fixture_config(ids)
        other["starts"] = 2
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, selected_config in enumerate((config, other)):
                path = Path(directory) / str(index) / "checkpoint.json"
                atomic_write_json(path, make_checkpoint(
                    index, global_ids=ids, config=selected_config,
                ))
                paths.append(path)
            report = aggregate_checkpoints(paths, 2)
        self.assertEqual(report["status"], "incompatible")
        self.assertIn("mixed_config_hashes", report["errors"])

    def test_corrupt_checkpoint_and_explicit_resume_failure_are_reported(self):
        ids = fixture_ids()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "0" / "checkpoint.json"
            bad.parent.mkdir(parents=True)
            bad.write_text("{broken", encoding="utf-8")
            failure = root / "1" / "failure.json"
            atomic_write_json(failure, {
                "state": "incompatible", "shard_index": 1,
                "message": "checkpoint config hash does not match",
            })
            report = aggregate_checkpoints([bad], 2, failure_paths=[failure])
        self.assertEqual(report["status"], "incompatible")
        self.assertTrue(report["corrupt_checkpoint_paths"])
        self.assertFalse(report["overall_complete"])

    def test_failed_matrix_and_optimizer_nonconvergence_are_distinct(self):
        ids = fixture_ids()
        payload = make_checkpoint(0, global_ids=ids, shard_count=1)
        payload["run_config"] = fixture_config(ids)
        payload["global_expected_graph_ids"] = payload["expected_graph_ids"]
        payload["config_hash"] = canonical_config_hash(payload["run_config"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            atomic_write_json(path, payload)
            completed = aggregate_checkpoints([path], 1)
            failed = aggregate_checkpoints([path], 1, matrix_result="failure")
        self.assertEqual(completed["status"], "completed")
        self.assertFalse(completed["results"][0]["converged"])
        self.assertEqual(failed["status"], "failed")

    def test_interrupted_and_running_shards_remain_in_progress(self):
        ids = fixture_ids()
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, status in enumerate(("interrupted", "running")):
                expected = [item for item in ids if shard_for_graph(item, 2) == index]
                completed = expected[:1]
                path = Path(directory) / str(index) / "checkpoint.json"
                atomic_write_json(path, make_checkpoint(
                    index, global_ids=ids, status=status, completed_ids=completed,
                ))
                paths.append(path)
            report = aggregate_checkpoints(paths, 2)
        self.assertEqual(report["status"], "in_progress")
        self.assertEqual(report["shard_states"][0]["status"], "interrupted")
        self.assertEqual(report["shard_states"][1]["status"], "running")

    def test_duplicate_graph_results_across_shards_are_rejected(self):
        ids = fixture_ids()
        first = make_checkpoint(0, global_ids=ids)
        second = make_checkpoint(1, global_ids=ids, status="partial", completed_ids=[])
        duplicate_row = dict(first["results"][0])
        duplicate_row["optimization_runs"] = [
            dict(candidate) for candidate in duplicate_row["optimization_runs"]
        ]
        second["results"] = [duplicate_row]
        second["completed_graph_ids"] = [duplicate_row["graph_id"]]
        second["unit_execution_log"] = [{
            "graph_id": duplicate_row["graph_id"], "status": "completed",
        }]
        second["candidate_execution_log"] = [dict(item) for item in first["candidate_execution_log"]]
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, payload in enumerate((first, second)):
                path = Path(directory) / str(index) / "checkpoint.json"
                atomic_write_json(path, payload)
                paths.append(path)
            report = aggregate_checkpoints(paths, 2)
        self.assertNotEqual(report["status"], "completed")
        self.assertIn("duplicate_aggregated_graph_result", report["errors"])

    def test_duplicate_candidate_key_is_rejected(self):
        ids = fixture_ids(shard_count=1)
        payload = make_checkpoint(0, global_ids=ids, shard_count=1)
        payload["results"][0]["optimization_runs"].append(
            dict(payload["results"][0]["optimization_runs"][0])
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            atomic_write_json(path, payload)
            report = aggregate_checkpoints([path], 1)
        self.assertIn("duplicate_optimization_candidate:0", report["errors"])

    def test_partial_candidate_checkpoint_is_in_progress_and_counted(self):
        ids = fixture_ids(shard_count=1)
        payload = make_checkpoint(
            0, global_ids=ids, shard_count=1, status="interrupted", completed_ids=[]
        )
        graph_id = payload["expected_graph_ids"][0]
        candidate = {
            "graph_id": graph_id,
            "candidate_key": f"{graph_id}:0:0",
            "layout_index": 0,
            "start_index": 0,
            "initial_values": [2.0, 1.0],
            "result_values": [1.9, 1.1],
            "rng_seed": 42,
            "objective_evaluation_count": 3,
        }
        payload["partial_optimization_runs"][graph_id] = [candidate]
        payload["candidate_execution_log"] = [{
            "graph_id": graph_id,
            "candidate_key": candidate["candidate_key"],
            "execution_segment_index": 0,
            "status": "completed",
            "objective_evaluation_count": 3,
        }]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            atomic_write_json(path, payload)
            report = aggregate_checkpoints([path], 1)
            loaded = load_checkpoint(
                path, config_hash=payload["config_hash"], shard_index=0,
                shard_count=1, expected_graph_ids=payload["expected_graph_ids"],
            )
        self.assertEqual(report["status"], "in_progress")
        self.assertFalse(report["overall_complete"])
        self.assertEqual(report["completed_optimizer_candidates"], 1)
        self.assertEqual(report["partial_optimizer_candidates"], 1)
        self.assertEqual(loaded["partial_optimization_runs"][graph_id][0]["candidate_key"],
                         candidate["candidate_key"])

    def test_malformed_partial_candidates_are_reported_without_crashing(self):
        ids = fixture_ids(shard_count=1)
        payload = make_checkpoint(
            0, global_ids=ids, shard_count=1, status="interrupted", completed_ids=[]
        )
        payload["partial_optimization_runs"] = {payload["expected_graph_ids"][0]: None}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            atomic_write_json(path, payload)
            report = aggregate_checkpoints([path], 1)
        self.assertEqual(report["status"], "corrupt")
        self.assertIn("malformed_partial_graph_state:0", report["errors"])

    def test_checkpoint_root_must_be_a_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(CheckpointCorruptError):
                load_checkpoint(path, config_hash="cfg", shard_index=0,
                                shard_count=1, expected_graph_ids=[])


if __name__ == "__main__":
    unittest.main()
