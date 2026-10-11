import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))
from p4_sharding import (
    aggregate_checkpoints,
    atomic_write_json,
    canonical_config_hash,
    canonical_graph_id,
    load_checkpoint,
    shard_for_graph,
)


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

    def test_config_hash_is_independent_of_mapping_order(self):
        self.assertEqual(
            canonical_config_hash({"a": 1, "b": {"x": 2, "y": 3}}),
            canonical_config_hash({"b": {"y": 3, "x": 2}, "a": 1}),
        )

    def test_atomic_checkpoint_round_trip_and_resume_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shard" / "checkpoint.json"
            checkpoint = {
                "schema_version": 1,
                "status": "completed",
                "config_hash": "cfg",
                "shard_index": 0,
                "shard_count": 1,
                "expected_graph_ids": ["a" * 64],
                "completed_graph_ids": ["a" * 64],
                "results": [{"graph_id": "a" * 64, "score": 1.0}],
            }
            atomic_write_json(path, checkpoint)
            loaded = load_checkpoint(
                path, config_hash="cfg", shard_index=0, shard_count=1,
                expected_graph_ids=["a" * 64],
            )
            self.assertEqual(loaded, checkpoint)
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])
            with self.assertRaisesRegex(ValueError, "config_hash"):
                load_checkpoint(
                    path, config_hash="different", shard_index=0, shard_count=1,
                    expected_graph_ids=["a" * 64],
                )

    def test_resume_rejects_non_object_or_malformed_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "root"):
                load_checkpoint(
                    path, config_hash="cfg", shard_index=0, shard_count=1,
                    expected_graph_ids=[],
                )

            atomic_write_json(path, {
                "schema_version": 1, "status": "partial", "config_hash": "cfg",
                "shard_index": 0, "shard_count": 1, "expected_graph_ids": [],
                "completed_graph_ids": ["not-a-digest"], "results": [],
            })
            with self.assertRaisesRegex(ValueError, "malformed"):
                load_checkpoint(
                    path, config_hash="cfg", shard_index=0, shard_count=1,
                    expected_graph_ids=[],
                )

    def test_aggregation_requires_all_expected_shards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, graph_id in enumerate(("a" * 64, "b" * 64)):
                atomic_write_json(root / f"{index}" / "checkpoint.json", {
                    "schema_version": 1,
                    "status": "completed",
                    "config_hash": "cfg",
                    "source_commit": "commit",
                    "shard_index": index,
                    "shard_count": 2,
                    "expected_graph_ids": [graph_id],
                    "completed_graph_ids": [graph_id],
                    "results": [{"graph_id": graph_id, "score": float(index)}],
                })
            paths = sorted(root.rglob("checkpoint.json"))
            complete = aggregate_checkpoints(paths, expected_shards=2)
            self.assertEqual(complete["status"], "all_expected_shards_completed")
            self.assertEqual(complete["optimized_graphs"], 2)

            partial = aggregate_checkpoints([root / "0" / "checkpoint.json"], expected_shards=2)
            self.assertEqual(partial["status"], "partial_or_failed")
            self.assertEqual(partial["missing_shards"], [1])

    def test_aggregation_rejects_failed_matrix_even_with_old_complete_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            graph_id = "a" * 64
            atomic_write_json(path, {
                "schema_version": 1,
                "status": "completed",
                "config_hash": "cfg",
                "source_commit": "commit",
                "shard_index": 0,
                "shard_count": 1,
                "expected_graph_ids": [graph_id],
                "completed_graph_ids": [graph_id],
                "results": [{"graph_id": graph_id}],
            })
            report = aggregate_checkpoints([path], 1, matrix_result="failure")
            self.assertEqual(report["status"], "partial_or_failed")
            self.assertIn("matrix_job_result:failure", report["errors"])


if __name__ == "__main__":
    unittest.main()
