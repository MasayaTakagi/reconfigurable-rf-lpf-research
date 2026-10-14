#!/usr/bin/env python3
"""Verify supplemental links without rewriting historical manifest evidence.

The link index records Git blob SHA-1 (not the separate SHA-256 used by
experiment manifests). Source links do not imply verified RF performance.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = "data/supplemental_experiment_evidence_index.csv"
RUNS = "experiments/chatgpt_topology_search/runs"
KNOWN_EMPTY = {"EXP-016", "EXP-017", "EXP-021", "EXP-022", "EXP-023", "EXP-024"}


def git_blob_sha1(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def check_supplemental_evidence(root=ROOT):
    root = Path(root)
    issues = []
    with (root / INDEX).open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    seen = set()
    covered = set()
    for row in records:
        exp = row["experiment_id"]
        path = row["source_path"]
        candidate = Path(path)
        allowed_prefix = f"{RUNS}/{exp}/"
        if exp not in KNOWN_EMPTY or path in seen or not path.startswith(allowed_prefix):
            issues.append(f"Invalid experiment or duplicate link: {path}")
            continue
        seen.add(path)
        covered.add(exp)
        if candidate.is_absolute() or ".." in candidate.parts or "\\" in path:
            issues.append(f"Unsafe source path: {path}")
            continue
        target = root / candidate
        if not target.is_file():
            issues.append(f"Missing supplemental evidence: {path}")
            continue
        data = target.read_bytes()
        if int(row["bytes"]) != len(data) or row["git_blob_sha1"] != git_blob_sha1(data):
            issues.append(f"Git blob content mismatch: {path}")
        if (row["manifest_evidence_state"] != "not_registered_in_manifest" or
                row["validation_claim"] != "source_reference_only"):
            issues.append(f"Evidence link incorrectly claims validation: {path}")
    if covered != KNOWN_EMPTY:
        issues.append("Some manifest-empty experiments have no supplemental source links")
    for exp in KNOWN_EMPTY:
        exp_dir = root / RUNS / exp
        manifest = json.loads((exp_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest["evidence"]:
            issues.append(f"Prior zero-evidence assumption changed; review links: {exp}")
        actual_files = {p.relative_to(root).as_posix() for p in exp_dir.rglob("*")
                        if p.is_file() and p.name != "manifest.json"}
        covered_files = {x for x in seen if x.startswith(f"{RUNS}/{exp}/")}
        if actual_files != covered_files:
            issues.append(f"Supplemental evidence file set is incomplete for {exp}")
    return issues


if __name__ == "__main__":
    issues = check_supplemental_evidence()
    if issues:
        raise SystemExit("FAILED supplemental provenance:\n- " + "\n- ".join(issues))
    print("PASS: supplemental files for six manifest-empty experiments retain Git blob identity")
