#!/usr/bin/env python3
"""Aggregate P4-A shard checkpoints without hiding missing or failed shards."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))
from p4_sharding import aggregate_checkpoints, atomic_write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="results/shards")
    parser.add_argument("--expected-shards", type=int, required=True)
    parser.add_argument(
        "--matrix-result", default="success",
        choices=("success", "failure", "cancelled", "skipped"),
        help="GitHub Actions result for the complete shard matrix job",
    )
    parser.add_argument("--output", default="results/p4_a_aggregate.json")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    checkpoints = sorted(input_dir.rglob("checkpoint.json")) if input_dir.exists() else []
    failures = sorted(input_dir.rglob("failure.json")) if input_dir.exists() else []
    report = aggregate_checkpoints(
        checkpoints, args.expected_shards, args.matrix_result, failure_paths=failures
    )
    report["checkpoint_files"] = [str(path) for path in checkpoints]
    report["failure_report_files"] = [str(path) for path in failures]
    atomic_write_json(args.output, report)
    print({
        "status": report["status"],
        "overall_complete": report["overall_complete"],
        "expected_shards": report["expected_shards"],
        "received_shards": report["received_shards"],
        "missing_shards": report["missing_shards"],
        "optimized_graphs": report["optimized_graphs"],
        "errors": report["errors"],
        "output": args.output,
    })
    return 0 if report["status"] in {"completed", "in_progress"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
