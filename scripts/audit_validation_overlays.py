#!/usr/bin/env python3
"""Validate posthoc replay overlays without mutating source-only manifests."""
import csv
import hashlib
import json
from pathlib import Path


def git_blob_sha1(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

ROOT = Path(__file__).resolve().parents[1]


def _csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def audit_overlays(root=ROOT):
    root = Path(root)
    issues = []
    overlays = _csv(root / "data/research_validation_overlays.csv")
    catalog = {x["catalog_id"]: x for x in
               _csv(root / "data/research_candidate_register.csv")}
    for row in overlays:
        cid = row["candidate_id"]
        try:
            c = catalog[cid]
            p = root / row["replay_evidence_path"]
            if not p.is_file() or ".." in Path(row["replay_evidence_path"]).parts:
                raise ValueError("Missing or unsafe replay evidence")
            artifact = json.loads(p.read_text(encoding="utf-8"))
            if (c["experiment_id"] != row["origin_experiment_id"] or
                c["constraint_id"] != row["base_constraint_id"] or
                artifact["constraint_id"] != row["base_constraint_id"] or
                artifact["effective_constraint_sha256"] != c["effective_constraint_sha256"]):
                raise ValueError("Constraint/experiment provenance mismatch")
            if (row["source_manifest_changed"] != "false" or
                not artifact["original_manifest_untouched"] or
                row["physical_validation"] != "not_run" or
                artifact["checks"]["part_specific_Qf_SRF_EM_physical_validation"]):
                raise ValueError("Replay must not assert physical validation or source manifest upgrade")
            if (row["replay_validation_status"] != "independent_finite_grid_passed" or
                artifact["ci_status"] != "completed_success" or
                not artifact["checks"]["independent_branch_current_MNA"]):
                raise ValueError("No recorded independent CI replay")
            for filename, sha in [
                (artifact["source_checkpoint_path"], artifact["source_checkpoint_git_blob_sha1"]),
                (artifact["verification_script_path"], artifact["verification_script_git_blob_sha1"])]:
                if git_blob_sha1((root / filename).read_bytes()) != sha:
                    raise ValueError("Replay script or original checkpoint changed")
            match = [x for x in artifact["results"] if x["candidate_id"] == cid]
            if len(match) != 1:
                raise ValueError("Replay is missing an unambiguous candidate result")
            m = match[0]
            for col, key in (
                    ("worst_il_db", "worst_IL_db"),
                    ("min_h2_db", "min_H2_db"),
                    ("min_h3_db", "min_H3_db")):
                if abs(float(c[col]) - float(m[key])) > 5e-5:
                    raise ValueError("Replay metric deviates from archived checkpoint catalog")
            if min(m["min_H2_db"], m["min_H3_db"]) < float(c["requirement_db"]):
                raise ValueError("Raw harmonic threshold is not met")
            if m["independent_MNA_probes"] != 84:
                raise ValueError("Unexpected MNA probe count")
        except (KeyError, ValueError, OSError) as exc:
            issues.append(f"{cid}: {exc}")
    if len({row["candidate_id"] for row in overlays}) != len(overlays):
        issues.append("Duplicate candidate replay overlay")
    return issues


if __name__ == "__main__":
    issues = audit_overlays()
    if issues:
        raise SystemExit("FAILED replay overlays:\n- " + "\n- ".join(issues))
    print("PASS: CI numerical replay overlays match archived trial checkpoints")
