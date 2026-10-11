"""Deterministic P4-A shard IDs, atomic checkpoints, and completeness checks."""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import tempfile


CHECKPOINT_SCHEMA_VERSION = 1
MAX_SHARDS = 64


def _is_graph_id(value):
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


def _canonical_edges(graph):
    node_count, edges = graph
    node_count = int(node_count)
    if node_count < 3:
        raise ValueError("A grounded graph needs ground, input, and output nodes")

    normalized = []
    for edge in edges:
        if len(edge) != 3:
            raise ValueError("Every graph edge must have two nodes and a component type")
        a, b, component = int(edge[0]), int(edge[1]), str(edge[2])
        if a == b or not (0 <= a < node_count and 0 <= b < node_count):
            raise ValueError("Graph edge contains an invalid node")
        normalized.append((a, b, component))

    best = None
    internal_nodes = range(3, node_count)
    for permutation in itertools.permutations(internal_nodes):
        mapping = {0: 0, 1: 1, 2: 2}
        mapping.update(zip(internal_nodes, permutation))
        mapped = tuple(sorted(
            (min(mapping[a], mapping[b]), max(mapping[a], mapping[b]), component)
            for a, b, component in normalized
        ))
        if best is None or mapped < best:
            best = mapped
    return node_count, best or ()


def canonical_graph_id(graph) -> str:
    """Return a process-independent SHA-256 ID, invariant to internal labels."""
    node_count, edges = _canonical_edges(graph)
    payload = {"node_count": node_count, "edges": [list(edge) for edge in edges]}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def shard_for_graph(graph_id: str, shard_count: int) -> int:
    """Assign a graph to a shard using its stable ID, never Python's hash()."""
    if not 1 <= shard_count <= MAX_SHARDS:
        raise ValueError(f"shard_count must be between 1 and {MAX_SHARDS}")
    if not _is_graph_id(graph_id):
        raise ValueError("graph_id must be a SHA-256 hex digest")
    digest = bytes.fromhex(graph_id)
    return int.from_bytes(digest[:8], "big") % shard_count


def canonical_config_hash(config) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def atomic_write_json(path, payload) -> None:
    """Write a JSON checkpoint with fsync plus same-directory atomic replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
        try:
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # The file itself is already durable enough for platforms without
            # directory fsync support.
            pass
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def load_checkpoint(path, *, config_hash, shard_index, shard_count, expected_graph_ids):
    """Load a compatible checkpoint or reject stale/corrupt resume state."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Resume checkpoint not found: {source}")
    try:
        checkpoint = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid checkpoint JSON: {source}") from exc
    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint root must be a JSON object")
    if checkpoint.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("Unsupported checkpoint schema version")
    expected = list(expected_graph_ids)
    checks = {
        "config_hash": config_hash,
        "shard_index": shard_index,
        "shard_count": shard_count,
        "expected_graph_ids": expected,
    }
    for key, value in checks.items():
        if checkpoint.get(key) != value:
            raise ValueError(f"Checkpoint {key} does not match this run")
    if checkpoint.get("status") not in {"running", "interrupted", "partial", "completed"}:
        raise ValueError("Checkpoint has an invalid status")
    results = checkpoint.get("results")
    completed = checkpoint.get("completed_graph_ids")
    if not isinstance(results, list) or not isinstance(completed, list):
        raise ValueError("Checkpoint result state is malformed")
    result_ids = [row.get("graph_id") for row in results if isinstance(row, dict)]
    if (len(result_ids) != len(results)
            or any(not _is_graph_id(graph_id) for graph_id in result_ids)
            or any(not _is_graph_id(graph_id) for graph_id in completed)
            or len(result_ids) != len(set(result_ids))):
        raise ValueError("Checkpoint has malformed or duplicate graph results")
    if set(result_ids) - set(expected) or sorted(result_ids) != sorted(completed):
        raise ValueError("Checkpoint results do not match its completed graph IDs")
    if checkpoint["status"] == "completed" and set(result_ids) != set(expected):
        raise ValueError("Completed checkpoint is missing expected graph results")
    return checkpoint


def aggregate_checkpoints(checkpoint_paths, expected_shards, matrix_result="success"):
    """Aggregate shard files; incomplete or mixed outputs never pass silently."""
    if not 1 <= expected_shards <= MAX_SHARDS:
        raise ValueError(f"expected_shards must be between 1 and {MAX_SHARDS}")

    errors = []
    shards = {}
    for path in sorted(map(Path, checkpoint_paths)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            errors.append(f"invalid_checkpoint:{path}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"invalid_checkpoint:{path}")
            continue
        index = payload.get("shard_index")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < expected_shards:
            errors.append(f"invalid_shard_index:{path}")
            continue
        if index in shards:
            errors.append(f"duplicate_shard:{index}")
            continue
        shards[index] = payload

    missing = sorted(set(range(expected_shards)) - set(shards))
    if missing:
        errors.append("missing_shards")
    if matrix_result != "success":
        errors.append(f"matrix_job_result:{matrix_result}")

    config_hashes = set()
    source_commits = set()
    expected_ids = []
    result_rows = []
    for index, payload in sorted(shards.items()):
        if payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            errors.append(f"unsupported_checkpoint_schema:{index}")
        shard_count = payload.get("shard_count")
        if isinstance(shard_count, bool) or not isinstance(shard_count, int) or shard_count != expected_shards:
            errors.append(f"shard_count_mismatch:{index}")
        config_value = payload.get("config_hash")
        source_value = payload.get("source_commit")
        if isinstance(config_value, str) and config_value:
            config_hashes.add(config_value)
        if isinstance(source_value, str) and source_value:
            source_commits.add(source_value)

        shard_expected = payload.get("expected_graph_ids")
        rows = payload.get("results")
        completed = payload.get("completed_graph_ids")
        if not isinstance(shard_expected, list) or not isinstance(rows, list) or not isinstance(completed, list):
            errors.append(f"malformed_checkpoint:{index}")
            continue
        if any(not _is_graph_id(graph_id) for graph_id in shard_expected):
            errors.append(f"malformed_expected_graph_ids:{index}")
            continue
        if any(not _is_graph_id(graph_id) for graph_id in completed):
            errors.append(f"malformed_completed_graph_ids:{index}")
            continue
        if len(shard_expected) != len(set(shard_expected)):
            errors.append(f"duplicate_expected_graph:{index}")
        expected_ids.extend(shard_expected)

        valid_rows = [row for row in rows if isinstance(row, dict)
                      and _is_graph_id(row.get("graph_id"))]
        row_ids = [row["graph_id"] for row in valid_rows]
        if len(row_ids) != len(rows) or len(row_ids) != len(set(row_ids)):
            errors.append(f"duplicate_or_malformed_result:{index}")
        if set(row_ids) - set(shard_expected) or sorted(row_ids) != sorted(completed):
            errors.append(f"result_graph_id_mismatch:{index}")
        if payload.get("status") != "completed" or set(row_ids) != set(shard_expected):
            errors.append(f"incomplete_shard:{index}")
        result_rows.extend(valid_rows)

    if len(expected_ids) != len(set(expected_ids)):
        errors.append("graph_assigned_to_multiple_shards")
    if len(config_hashes) != 1:
        errors.append("missing_or_mixed_config_hashes")
    if len(config_hashes) > 1:
        errors.append("mixed_config_hashes")
    if len(source_commits) != 1:
        errors.append("missing_or_mixed_source_commits")
    if len(source_commits) > 1:
        errors.append("mixed_source_commits")
    all_result_ids = [row.get("graph_id") for row in result_rows if isinstance(row, dict)]
    if len(all_result_ids) != len(set(all_result_ids)):
        errors.append("duplicate_aggregated_graph_result")

    successful = not errors
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "status": "all_expected_shards_completed" if successful else "partial_or_failed",
        "search_claim": "bounded_seeded_sample_not_exhaustive_or_global_optimum",
        "expected_shards": expected_shards,
        "received_shards": sorted(shards),
        "missing_shards": missing,
        "selected_graphs": len(expected_ids),
        "optimized_graphs": len(result_rows),
        "config_hash": next(iter(config_hashes)) if len(config_hashes) == 1 else None,
        "source_commit": next(iter(source_commits)) if len(source_commits) == 1 else None,
        "errors": sorted(set(errors)),
        "results": sorted(result_rows, key=lambda row: row.get("graph_id", "")),
    }
