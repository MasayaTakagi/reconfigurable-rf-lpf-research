#!/usr/bin/env python3
"""Phase 2 forensic triage of previously unlinked, tracked research files.

This is a deterministic source inspection and reference search, not proof a
file is unused. No deletion, history rewrite, RF simulation or modification of
original evidence. Full-path text hits are hints, not a semantic provenance
certificate; content-equal Git blobs do not imply interchangeable run roles.
"""
import argparse
import base64
import csv
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_reference_inventory import ROOT, _blob_sha1, _tracked_paths, create_inventory

SNAPSHOT = "data/research_storage_triage.csv"
EXCLUDE_TEXT_SOURCES = {
    SNAPSHOT, "docs/phase2_evidence_triage_20261015.md",
}
TEXT_EXTENSIONS = {".md", ".rst", ".txt", ".py", ".json", ".jsonl",
                   ".csv", ".yaml", ".yml", ".toml", ".log"}
FIELDS = ("review_id", "path", "git_blob_sha1", "bytes", "location",
          "original_storage_class", "source_content_kind", "sample_schema",
          "exact_path_text_ref_count", "exact_path_text_refs",
          "same_blob_other_paths", "same_blob_other_count",
          "review_class", "disposition", "followup_action")


def _safe_read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _source_summary(path, fullpath):
    """Inspect a saved file without computing or interpreting its RF performance."""
    suffix = Path(path).suffix.lower()
    if suffix in (".lock", ".log"):
        return "runtime_or_diagnostic_record", "name_or_extension_only"
    if suffix in (".json", ".jsonl"):
        try:
            if suffix == ".jsonl":
                first = next((s for s in fullpath.read_text(encoding="utf-8").splitlines()
                              if s.strip()), "")
                data = json.loads(first) if first else {}
            else:
                data = json.loads(fullpath.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return "structured_json", ";".join(sorted(map(str, data.keys()))[:10])
            if isinstance(data, list):
                return "structured_json_array", "list_length=" + str(len(data))
            return "structured_json_scalar", type(data).__name__
        except (OSError, ValueError, UnicodeDecodeError):
            return "unparsed_json", "manual_review_required"
    if suffix == ".csv":
        text = _safe_read_text(fullpath)
        if text is None:
            return "unparsed_csv", "manual_review_required"
        try:
            columns = next(csv.reader(io.StringIO(text)), [])
        except csv.Error:
            return "unparsed_csv", "manual_review_required"
        return "tabular_csv", ";".join(columns[:10])
    if suffix in (".md", ".rst", ".txt"):
        return "narrative_or_text", suffix[1:]
    if suffix == ".py":
        return "source_code", "python"
    if suffix in (".yaml", ".yml", ".toml"):
        return "configuration", suffix[1:]
    return "unclassified_file", suffix or "no_extension"


def _ref_hits(text, needle):
    # Avoid accepting a path only because it is a prefix of a longer filename.
    return bool(re.search(r"(?<![\w./-])" + re.escape(needle)
                          + r"(?![\w./-])", text))


def build_triage(root=ROOT, tracked=None):
    root = Path(root)
    if tracked is None:
        tracked = _tracked_paths(root)
    tracked = set(tracked)
    source_records, initial = create_inventory(root, tracked=tracked)
    pending = [row for row in source_records
               if row["review_decision"] == "review_only_no_deletion"]

    # The text search is over tracked narrative/source records. Exclude this
    # generated index and self-referential summary docs from evidence claims.
    texts = {}
    for rel in sorted(tracked):
        if rel in EXCLUDE_TEXT_SOURCES or Path(rel).suffix.lower() not in TEXT_EXTENSIONS:
            continue
        body = _safe_read_text(root / rel)
        if body is not None:
            texts[rel] = body

    blobs = defaultdict(list)
    for rel in sorted(tracked):
        blobs[_blob_sha1((root / rel).read_bytes())].append(rel)

    records = []
    for i, row in enumerate(pending, start=1):
        rel = row["path"]
        assert rel in tracked
        exact_refs = [
            source for source, body in texts.items()
            if source != rel and _ref_hits(body, rel)
        ]
        same_blob = [other for other in blobs[row["git_blob_sha1"]] if other != rel]
        kind, schema = _source_summary(rel, root / rel)
        if exact_refs:
            review_class = "text_linked_requires_semantic_review"
            action = "verify_text_link_role_and_retention"
        elif same_blob:
            review_class = "content_equal_requires_run_role_review"
            action = "compare_duplicate_context_and_commit_lineage"
        elif row["location"] == "validation":
            review_class = "validation_source_not_indexed"
            action = "inspect_run_context_and_manifest_reference"
        elif row["location"] == "experiment":
            review_class = "experiment_source_not_indexed"
            action = "inspect_experiment_provenance_and_source_role"
        else:
            review_class = "other_source_not_indexed"
            action = "confirm_legacy_and_compatibility_dependencies"
        records.append({
            "review_id": f"ST-{i:03d}",
            "path": rel, "git_blob_sha1": row["git_blob_sha1"],
            "bytes": row["bytes"], "location": row["location"],
            "original_storage_class": row["storage_class"],
            "source_content_kind": kind, "sample_schema": schema,
            "exact_path_text_ref_count": len(exact_refs),
            "exact_path_text_refs": ";".join(exact_refs),
            "same_blob_other_paths": ";".join(same_blob),
            "same_blob_other_count": len(same_blob),
            "review_class": review_class,
            "disposition": "retain_pending_source_context_review",
            "followup_action": action,
        })
    counts = Counter(row["review_class"] for row in records)
    summaries = {
        "schema_version": 1, "phase": "Phase 2",
        "scope": "all 46 review_only_no_deletion entries as classified in main PR #51",
        "input_review_file_count": len(pending),
        "classified_rows": len(records),
        "review_classes": dict(sorted(counts.items())),
        "locations": dict(sorted(Counter(x["location"] for x in records).items())),
        "exact_path_text_hits": sum(int(x["exact_path_text_ref_count"]) for x in records),
        "files_with_exact_path_text_hits": sum(bool(x["exact_path_text_ref_count"]) for x in records),
        "files_with_same_blob_elsewhere": sum(bool(x["same_blob_other_count"]) for x in records),
        "all_dispositions_retain": all(x["disposition"] ==
                                       "retain_pending_source_context_review"
                                       for x in records),
        "deletions_or_moves_executed": 0,
        "limitations": [
            "Text search is exact Git-relative pathname string, not manual interpretation.",
            "Git history, external ZIP, original conversations, and untracked files are not searched.",
            "A matching Git blob SHA-1 does not prove the same evidence role or redundant history.",
            "Files remain protected unless a future separate decision authorizes change.",
        ],
        "reference_inventory_input": initial["retention_decisions"],
    }
    return records, summaries


def to_csv(records):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return out.getvalue()


def check_snapshot(root=ROOT):
    root = Path(root)
    expected = (root / SNAPSHOT).read_text(encoding="utf-8")
    records, summary = build_triage(root)
    if expected != to_csv(records):
        raise ValueError("Evidence triage snapshot is stale or was modified")
    if not summary["all_dispositions_retain"]:
        raise ValueError("Source triage inadvertently approved evidence deletion")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, help="Write an individual-row CSV")
    ap.add_argument("--summary", type=Path, help="Write a summary JSON")
    ap.add_argument("--check", action="store_true", help="Fail on outdated committed CSV")
    ap.add_argument("--bootstrap-b64", action="store_true",
                    help="Output base64 CSV once for manual review commit")
    args = ap.parse_args()
    records, summary = build_triage()
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        args.csv.write_text(to_csv(records), encoding="utf-8")
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
    if args.check:
        summary = check_snapshot()
    print("PASS: source-only triage", json.dumps(summary, ensure_ascii=False))
    if args.bootstrap_b64:
        print("TRIAGE_B64_BEGIN")
        print(base64.b64encode(to_csv(records).encode("utf-8")).decode("ascii"))
        print("TRIAGE_B64_END")


if __name__ == "__main__":
    main()
