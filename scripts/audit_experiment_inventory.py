#!/usr/bin/env python3
"""Cross-check all Phase 2 manifest snapshots with the evidence inventory.

This is a metadata consistency audit, not a rerun of optimization or RF verification.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "experiments/chatgpt_topology_search/runs"
INVENTORY = ROOT / "data/experiment_evidence_inventory.csv"
AUDITED_COLUMNS = {
    "experiment_id": ("experiment_id",),
    "constraint_class": ("constraints", "class"),
    "constraint_id": ("constraints", "constraint_id"),
    "objective": ("objective",),
    "execution_status": ("execution", "status"),
    "numerical_validation": ("validation", "numerical"),
    "independent_validation": ("validation", "independent"),
    "implementation_validation": ("validation", "implementation"),
}


def _field(document, path):
    value = document
    for segment in path:
        value = value[segment]
    return "" if value is None else str(value)


def check_inventory(root=ROOT):
    root = Path(root)
    issues = []
    with (root / "data/experiment_evidence_inventory.csv").open(
            newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    seen = set()
    run_root = root / "experiments/chatgpt_topology_search/runs"
    expected_ids = {path.parent.name for path in run_root.glob("EXP-*/manifest.json")}
    if len(rows) != len(expected_ids):
        issues.append("Inventory count does not match manifest count")
    index_path = root / "data/experiment_index.csv"
    with index_path.open(newline="", encoding="utf-8") as stream:
        indexed = {row["experiment_id"] for row in csv.DictReader(stream)}
    if indexed != expected_ids:
        issues.append("Experiment index and manifest sets disagree")
    for row in rows:
        cid = row["experiment_id"]
        if cid in seen:
            issues.append(f"Duplicate inventory ID: {cid}")
        seen.add(cid)
        if cid not in expected_ids:
            issues.append(f"Unknown inventory ID: {cid}")
            continue
        manifest_path = run_root / cid / "manifest.json"
        if cid == "EXP-047":
            # The source-pinned in-chat report does not contain canonical
            # evidence/code/seed/environment fields. Never invent these.
            from src.lpf.legacy_manifest_adapter import legacy_exp047_index_view
            view = legacy_exp047_index_view(root=root)
            expected = {
                "experiment_id": "EXP-047",
                "constraint_class": view["constraints"]["class"],
                "constraint_id": view["constraints"]["constraint_id"],
                "objective": view["objective"],
                "execution_status": view["execution"]["status"],
                "numerical_validation": view["validation"]["numerical"],
                "independent_validation": view["validation"]["independent"],
                "implementation_validation": "not_run",
                "registered_evidence_count": "0",
                "execution_sha_recorded": "false",
                "seed_recorded": "false",
                "environment_recorded": "false",
                "readme_present": str((run_root / cid / "README.md").is_file()).lower(),
                "review_flag": "legacy_partial_noncanonical_manifest",
                "manifest": manifest_path.relative_to(root).as_posix(),
            }
            for key, value in expected.items():
                if row[key] != value:
                    issues.append(f"{cid}: unsupported legacy inventory value for {key}")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for column, keys in AUDITED_COLUMNS.items():
            if row[column] != _field(manifest, keys):
                issues.append(f"{cid}: stale {column} versus manifest")
        count = len(manifest["evidence"])
        if row["registered_evidence_count"] != str(count):
            issues.append(f"{cid}: evidence count differs from manifest")
        for column, value in [
                ("execution_sha_recorded", manifest["code"]["execution_sha"] is not None),
                ("seed_recorded", manifest["random_seed"] is not None),
                ("environment_recorded", manifest["environment"] is not None),
                ("readme_present", (run_root / cid / "README.md").is_file())]:
            if row[column] != str(value).lower():
                issues.append(f"{cid}: stale {column}")
        if row["manifest"] != manifest_path.relative_to(root).as_posix():
            issues.append(f"{cid}: manifest path differs")
        flag = row["review_flag"]
        if flag not in {
                "none", "manifest_vs_report_conflict",
                "reported_30db_checkpoint_missing",
                "mixed_runner_recovery_and_invalid_import_diagnostic",
                "invalid_warmstart_import_performance"}:
            issues.append(f"{cid}: unsupported review flag")
        if cid == "EXP-016" and flag != "manifest_vs_report_conflict":
            issues.append(f"{cid}: known evidence conflict must remain flagged")
        if cid == "EXP-017" and flag != "reported_30db_checkpoint_missing":
            issues.append(f"{cid}: unrecoverable reported checkpoint must remain flagged")
        if cid in ("EXP-034", "EXP-035", "EXP-036", "EXP-037") and flag == "none":
            issues.append(f"{cid}: known terminal mapping caveat must remain flagged")
    if seen != expected_ids:
        issues.append("Inventory missing one or more experiments")
    return issues


if __name__ == "__main__":
    problems = check_inventory()
    if problems:
        raise SystemExit("FAILED experiment inventory:\n- " + "\n- ".join(problems))
    with INVENTORY.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    print("PASS: inventory matches", len(records),
          "experiments;", dict(Counter(x["constraint_class"] for x in records)),
          "with", sum(x["registered_evidence_count"] == "0" for x in records),
          "manifest evidence-count zero records")
