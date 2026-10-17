#!/usr/bin/env python3
"""Phase 2 W4: read-only current-tree experiment and workflow disposition audit.

This is a PRE-deletion inspection. No file is retired by this script.
Unlinked/unreferenced is not equivalent to redundant or reproducible.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

from build_reference_inventory import create_inventory

ROOT = Path(__file__).resolve().parents[1]
PRE_W4_MAIN = "a11e9edc06b1238558cfeff1efb005faf668692b"
PROTECTED = ROOT / "data/repository_reviews/step4_retention_46_20261017.csv"
RUN_PREFIX = "experiments/chatgpt_topology_search/runs/"
AREAS = ("data/validation/", RUN_PREFIX)
W4_SCOPES = ("E-001", "E-002", "W-001")


def git(*args, text=True):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=text)


def sha1_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def output_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase2_reports/w4")
    args = ap.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    tracked = set(p for p in git("ls-files", "-z", text=False).decode().split("\0") if p)
    head = git("rev-parse", "HEAD").strip()
    base_head = git("rev-parse", PRE_W4_MAIN).strip()
    assert base_head == PRE_W4_MAIN, "Pre-W4 main not available"
    deleted = git("diff", "--diff-filter=D", "--name-only", PRE_W4_MAIN, "HEAD").splitlines()
    assert not deleted, "W4 is read-only; deletion is not approved: " + repr(deleted)

    with PROTECTED.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 46
    protected = {}
    for row in rows:
        name = row["path"]
        expected = row["git_blob_sha1"]
        assert name in tracked and (ROOT / name).is_file(), "Protected original absent: " + name
        raw = (ROOT / name).read_bytes()
        assert sha1_blob(raw) == expected, "Protected original changed: " + name
        protected[name] = expected

    inventory, reference_summary = create_inventory(root=ROOT, tracked=tracked)
    by_path = {r["path"]: r for r in inventory}
    total = collections.Counter()
    file_decisions = []
    for row in inventory:
        path = row["path"]
        if not path.startswith(AREAS):
            continue
        if path.startswith(RUN_PREFIX):
            tail = path[len(RUN_PREFIX):]
            group = tail.split("/", 1)[0]
            scope = "E-002"
        else:
            tail = path[len("data/validation/"):]
            group = tail.split("/", 1)[0]
            scope = "E-001"
        if path in protected:
            decision = "retain_protected_46"
        elif row["review_decision"] in ("preserve_immutable", "preserve_referenced"):
            decision = "retain_machine_referenced"
        elif path.endswith("/manifest.json"):
            decision = "retain_original_manifest"
        elif any(x in path for x in ("/locks/", "/tasks/", "/logs/", "manager.log", "code_snapshot", "source_pr")):
            decision = "review_runtime_or_source_provenance"
        else:
            decision = "review_unindexed_no_deletion_authority"
        file_decisions.append({
            "w4_scope": scope,
            "path": path,
            "git_blob_sha1": row["git_blob_sha1"],
            "bytes": row["bytes"],
            "run_or_validation_group": group,
            "storage_class": row["storage_class"],
            "machine_reference_kinds": row["source_refs"],
            "manifest_ids": row["manifest_experiments"],
            "catalog_ids": row["catalog_candidates"],
            "supplemental_ids": row["supplemental_experiments"],
            "protected_46": "true" if path in protected else "false",
            "w4_disposition": decision,
            "owner_delete_approval": "not_granted",
        })
        total[(scope, decision)] += 1

    fields = (
        "w4_scope", "path", "git_blob_sha1", "bytes", "run_or_validation_group",
        "storage_class", "machine_reference_kinds", "manifest_ids",
        "catalog_ids", "supplemental_ids", "protected_46",
        "w4_disposition", "owner_delete_approval",
    )
    output_csv(out / "w4_evidence_file_review.csv", file_decisions, fields)

    workflow_rows = []
    workflow_source_missing = []
    for p in sorted(x for x in tracked if x.startswith(".github/workflows/") and x.endswith((".yml", ".yaml"))):
        data = (ROOT / p).read_text(encoding="utf-8")
        names = sorted(set(re.findall(r"(?:experiments|scripts|src)/[A-Za-z0-9_./-]+\.(?:py|json|csv|sh)", data)))
        missing = [x for x in names if x not in tracked]
        if missing:
            workflow_source_missing.append({"workflow": p, "unresolved_literal_references": missing})
        is_experiment = bool(re.search(r"(?i)(?:exp0[0-9]|lpf-exp0|rft003|lpf-target|lpf-p4-a)", p))
        has_dispatch = bool(re.search(r"(?m)^\s*workflow_dispatch\s*:", data))
        has_write = bool(re.search(r"(?m)^\s*contents:\s*write\s*$", data)) or "git push " in data
        pinned_branch = bool(re.search(r"(?i)(?:refs/heads/research/|ref:\s*(?:exp/|research/|exp-|exp0))", data))
        if not is_experiment:
            disposition = "retain_shared_ci_or_governance"
        elif has_write or pinned_branch:
            disposition = "retain_security_and_branch_dependency_review"
        elif has_dispatch:
            disposition = "retain_manual_replay_until_run_review"
        else:
            disposition = "review_historical_trigger_until_run_review"
        workflow_rows.append({
            "w4_scope": "W-001" if "exp042" in p else "W-other",
            "path": p,
            "git_blob_sha1": sha1_blob(data.encode()),
            "bytes": len(data.encode()),
            "manual_dispatch": str(has_dispatch).lower(),
            "writes_or_pushes": str(has_write).lower(),
            "pinned_branch_reference": str(pinned_branch).lower(),
            "referenced_code_paths": ";".join(names),
            "literal_source_paths_not_found": ";".join(missing),
            "w4_disposition": disposition,
            "owner_delete_approval": "not_granted",
        })

    wf_fields = (
        "w4_scope", "path", "git_blob_sha1", "bytes", "manual_dispatch",
        "writes_or_pushes", "pinned_branch_reference", "referenced_code_paths",
        "literal_source_paths_not_found", "w4_disposition", "owner_delete_approval"
    )
    output_csv(out / "w4_workflow_review.csv", workflow_rows, wf_fields)
    by_run = collections.Counter(row["run_or_validation_group"] for row in file_decisions)
    result = {
        "phase": "Phase 2",
        "operation": "W4 read-only current checked-out tree review",
        "pre_w4_main_commit": PRE_W4_MAIN,
        "checkout_commit": head,
        "tracked_file_count": len(tracked),
        "evidence_review_file_count": len(file_decisions),
        "evidence_review_bytes": sum(int(r["bytes"]) for r in file_decisions),
        "by_scope": {scope: sum(row["w4_scope"] == scope for row in file_decisions) for scope in ("E-001", "E-002")},
        "by_disposition": dict(sorted(((s + ":" + d), n) for (s, d), n in total.items())),
        "groups_count": len(by_run),
        "top_groups": by_run.most_common(12),
        "workflow_count": len(workflow_rows),
        "workflow_exp042_count": sum(x["w4_scope"] == "W-001" for x in workflow_rows),
        "workflow_dispatch_count": sum(x["manual_dispatch"] == "true" for x in workflow_rows),
        "workflow_mutating_or_branch_pinned": [
            row["path"] for row in workflow_rows
            if row["w4_disposition"] == "retain_security_and_branch_dependency_review"
        ],
        "workflow_literal_source_paths_not_found": workflow_source_missing,
        "protected_46_pass": len(protected),
        "source_reference_limits": (
            "manifest/catalog/supplemental/overlay graph is partial;"
            " scan of literal workflow references is heuristic;"
            " actual run IDs and dynamic paths not exhaustively indexed;"
            " absence from these indices never proves redundancy"
        ),
        "owner_approved_artifact_deletions": 0,
        "owner_approved_workflow_deletions": 0,
        "executed_deletions": 0,
        "new_rf_computations": 0,
        "phase3_started": False,
    }
    (out / "w4_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("W4_AUDIT_SUMMARY=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    print("W4_AUDIT_PASS: review only; 46 historical protected blobs unchanged; no deleted paths; no artifact/workflow removal")
    if workflow_source_missing:
        print("W4_WARNING: literal code path references missing from tracked tree require individual inspection")


if __name__ == "__main__":
    main()
