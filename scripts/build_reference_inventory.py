#!/usr/bin/env python3
"""Trace tracked Phase 2 evidence references without deleting or moving sources.

References are restricted to machine-readable manifest, catalog and overlay links.
An unlinked file is NOT necessarily redundant: code, copied run state, and old
reports can carry provenance outside those indices. This emits review candidates,
not deletion authorization, and does not perform RF numerical analysis.
"""
import argparse
import csv
import hashlib
import io
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = "experiments/chatgpt_topology_search/runs/"
FIELDS = (
    "path", "bytes", "git_blob_sha1", "location", "source_refs",
    "manifest_experiments", "catalog_candidates", "supplemental_experiments",
    "replay_candidates", "storage_class", "review_decision",
)


def _read_csv(root, path):
    with (root / path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _blob_sha1(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _tracked_paths(root):
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    return {path for path in raw.decode("utf-8").split("\0") if path}


def _safe_reference(root, rel):
    if not isinstance(rel, str) or not rel or "\\" in rel:
        raise ValueError("Invalid relative source reference")
    relpath = Path(rel)
    if relpath.is_absolute() or ".." in relpath.parts:
        raise ValueError("Unsafe relative source reference: " + rel)
    actual = (root / relpath).resolve()
    if not actual.is_relative_to(root.resolve()) or not actual.is_file():
        raise ValueError("Source reference is missing or outside repository: " + rel)
    return rel


def _location(path):
    if path.startswith("data/validation/"):
        return "validation"
    if path.startswith(RUNS):
        return "experiment"
    if path.startswith("candidates/"):
        return "legacy_candidate"
    if path.startswith("data/constraints/") or path in (
            "data/design_constraints.json", "data/bands.csv"):
        return "rf_policy"
    if path.startswith("data/"):
        return "research_index"
    return "repository_other"


def _runtime_diagnostic(path):
    parts = Path(path).parts
    return (path.endswith((".lock", ".log", ".manager.lock")) or
            "locks" in parts or "logs" in parts or "tasks" in parts or
            "results" in parts or Path(path).name in ("status.json", "manager.log"))


def _classify(path, sources):
    location = _location(path)
    if location == "rf_policy":
        return "approved_or_historical_policy", "preserve_immutable"
    if path.endswith("/manifest.json") and path.startswith(RUNS):
        return "original_experiment_manifest", "preserve_immutable"
    if "manifest_sha256" in sources:
        return ("registered_runtime_evidence" if _runtime_diagnostic(path)
                else "registered_manifest_evidence"), "preserve_referenced"
    if "candidate_checkpoint" in sources:
        return "curated_checkpoint", "preserve_referenced"
    if "candidate_verification" in sources or "posthoc_replay" in sources:
        return "curated_validation_evidence", "preserve_referenced"
    if "supplemental_blob" in sources:
        return "historical_supplemental_source", "preserve_referenced"
    if _runtime_diagnostic(path):
        return "unlinked_runtime_diagnostic", "review_only_no_deletion"
    if location == "validation":
        return "unlinked_validation_artifact", "review_only_no_deletion"
    if location == "experiment":
        return "unlinked_historical_source", "review_only_no_deletion"
    return "unlinked_nonruntime_file", "review_only_no_deletion"


def create_inventory(root=ROOT, tracked=None):
    root = Path(root)
    if tracked is None:
        tracked = _tracked_paths(root)
    tracked = set(tracked)
    refs = defaultdict(lambda: {"kinds": set(), "manifest": set(),
                                "candidates": set(), "supplemental": set(),
                                "replays": set()})

    def link(rel, kind, owner):
        rel = _safe_reference(root, rel)
        if rel not in tracked:
            raise ValueError(f"Source evidence not tracked by Git: {kind} {rel}")
        d = refs[rel]
        d["kinds"].add(kind)
        if kind == "manifest_sha256":
            d["manifest"].add(owner)
        elif kind in ("candidate_checkpoint", "candidate_verification"):
            d["candidates"].add(owner)
        elif kind == "supplemental_blob":
            d["supplemental"].add(owner)
        elif kind == "posthoc_replay":
            d["replays"].add(owner)

    for manifest in sorted((root / RUNS).glob("EXP-*/manifest.json")):
        exp_id = manifest.parent.name
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for item in data["evidence"]:
            link(item["path"], "manifest_sha256", exp_id)
    for row in _read_csv(root, "data/research_candidate_register.csv"):
        link(row["checkpoint_path"], "candidate_checkpoint", row["catalog_id"])
        link(row["verification_path"], "candidate_verification", row["catalog_id"])
    for row in _read_csv(root, "data/supplemental_experiment_evidence_index.csv"):
        link(row["source_path"], "supplemental_blob", row["experiment_id"])
    for row in _read_csv(root, "data/research_validation_overlays.csv"):
        link(row["replay_evidence_path"], "posthoc_replay", row["candidate_id"])

    # Classify all tracked paths, but export files relevant to RF provenance only.
    exported = sorted(x for x in tracked if _location(x) != "repository_other")
    records = []
    for path in exported:
        raw = (root / path).read_bytes()
        source = refs[path]
        category, decision = _classify(path, source["kinds"])
        records.append({
            "path": path, "bytes": len(raw), "git_blob_sha1": _blob_sha1(raw),
            "location": _location(path),
            "source_refs": ";".join(sorted(source["kinds"])),
            "manifest_experiments": ";".join(sorted(source["manifest"])),
            "catalog_candidates": ";".join(sorted(source["candidates"])),
            "supplemental_experiments": ";".join(sorted(source["supplemental"])),
            "replay_candidates": ";".join(sorted(source["replays"])),
            "storage_class": category, "review_decision": decision,
        })
    counts = Counter(row["storage_class"] for row in records)
    decisions = Counter(row["review_decision"] for row in records)
    duplicate_paths = defaultdict(list)
    for record in records:
        duplicate_paths[record["git_blob_sha1"]].append(record["path"])
    same_bytes = [sorted(paths) for paths in duplicate_paths.values() if len(paths) > 1]
    same_bytes.sort(key=lambda paths: (-len(paths), paths[0]))
    review = [r for r in records if r["review_decision"] == "review_only_no_deletion"]
    summary = {
        "schema_version": 1, "phase": "Phase 2",
        "report_type": "tracked_file_reference_inventory",
        "scope": "all tracked data/ files, experiment runs and candidates",
        "tracked_source_files_total": len(tracked),
        "classified_files": len(records),
        "classified_bytes": sum(r["bytes"] for r in records),
        "storage_classes": dict(sorted(counts.items())),
        "retention_decisions": dict(sorted(decisions.items())),
        "review_only_by_location": dict(sorted(Counter(r["location"] for r in review).items())),
        "review_only_example_paths": [r["path"] for r in review[:25]],
        "identical_content_blob_groups": len(same_bytes),
        "additional_paths_with_identical_content": sum(len(p) - 1 for p in same_bytes),
        "identical_content_examples": same_bytes[:12],
        "duplicate_paths_also_require_independent_review": True,
        "manifest_referenced_files": sum(bool(r["manifest_experiments"]) for r in records),
        "catalog_referenced_files": sum(bool(r["catalog_candidates"]) for r in records),
        "supplemental_referenced_files": sum(bool(r["supplemental_experiments"]) for r in records),
        "replay_referenced_files": sum(bool(r["replay_candidates"]) for r in records),
        "review_only_is_not_deletion_permission": True,
        "deletions_performed": 0,
    }
    return records, summary


def to_csv(records):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--summary", type=Path, required=True)
    args = ap.parse_args()
    records, summary = create_inventory()
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.csv.write_text(to_csv(records), encoding="utf-8")
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print("PASS: tracked evidence reverse references;",
          summary["classified_files"], "classified files;",
          summary["manifest_referenced_files"], "files linked from manifests;",
          summary["retention_decisions"])
    print("No deletion or directory migration was performed.")
    print("Identical-content Git blobs:", summary["identical_content_blob_groups"],
          "groups,", summary["additional_paths_with_identical_content"],
          "additional file paths (not deletion candidates).")
    print("Unlinked review by directory:", summary["review_only_by_location"])


if __name__ == "__main__":
    main()
