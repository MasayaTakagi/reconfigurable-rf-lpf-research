#!/usr/bin/env python3
"""Source-only Phase 2 execution metadata gap matrix.

A complete metadata row is NOT a claim that the solver reran, converged or
achieved the RF constraints. Original manifests are never mutated.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = "data/experiment_evidence_inventory.csv"
FIELDS = ("experiment_id", "constraint_class", "constraint_id",
          "execution_status", "numerical_validation", "independent_validation",
          "execution_sha_recorded", "seed_recorded", "environment_recorded",
          "registered_evidence_count", "review_flag", "missing_metadata",
          "metadata_review_class", "execution_reproduced_here")


def matrix(root=ROOT):
    root = Path(root)
    with (root / INVENTORY).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or len({r["experiment_id"] for r in rows}) != len(rows):
        raise ValueError("Inventory missing or duplicate experiment IDs")
    flags = ("execution_sha_recorded", "seed_recorded", "environment_recorded")
    output = []
    for row in rows:
        missing = []
        for flag in flags:
            if row[flag] not in ("true", "false"):
                raise ValueError("Malformed metadata boolean: " + flag)
            if row[flag] == "false":
                missing.append(flag)
        if row["execution_status"] == "unknown":
            missing.append("execution_status_unknown")
        if not row["registered_evidence_count"].isdigit():
            raise ValueError("Invalid source manifest evidence count")
        if int(row["registered_evidence_count"]) == 0:
            missing.append("manifest_evidence_empty")
        class_name = ("needs_source_recovery" if missing
                      else "metadata_fields_present_source_only")
        output.append({
            **{k: row[k] for k in FIELDS if k in row},
            "missing_metadata": ";".join(missing),
            "metadata_review_class": class_name,
            "execution_reproduced_here": "false",
        })
    output.sort(key=lambda x: x["experiment_id"])
    categories = Counter(r["constraint_class"] for r in output)
    summary = {
        "schema_version": 1, "phase": "Phase 2",
        "scope": "all 39 manifest-derived inventory entries",
        "data_source": INVENTORY,
        "experiments": len(output),
        "constraint_classes": dict(sorted(categories.items())),
        "unknown_execution_status": sum(
            "execution_status_unknown" in x["missing_metadata"] for x in output),
        "missing_seed": sum(x["seed_recorded"] == "false" for x in output),
        "missing_execution_sha": sum(
            x["execution_sha_recorded"] == "false" for x in output),
        "missing_environment": sum(
            x["environment_recorded"] == "false" for x in output),
        "zero_manifest_evidence": sum(
            x["registered_evidence_count"] == "0" for x in output),
        "metadata_flags_present": sum(
            x["metadata_review_class"] == "metadata_fields_present_source_only"
            for x in output),
        "rf_runs_reproduced_by_this_report": 0,
        "original_manifest_edits": 0,
        "missing_values_filled_by_inference": 0,
        "limitations": [
            "A field set to true reports metadata presence, not correctness.",
            "Original run replay and solver convergence are not assessed.",
            "Historical, trial and formal constraints remain distinct.",
            "Supplemental indexes can contain sources not recorded by manifests.",
        ],
    }
    return output, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    rows, summary = matrix()
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2)
                                + "\n", encoding="utf-8")
    print("PASS Phase 2 source-only metadata gap matrix:", json.dumps(summary,
                                                             ensure_ascii=False))


if __name__ == "__main__":
    main()
