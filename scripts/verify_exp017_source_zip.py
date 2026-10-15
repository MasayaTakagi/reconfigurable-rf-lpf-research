#!/usr/bin/env python3
"""Read-only byte integrity check for the user-provided original EXP-017 ZIP.

Checks all 26 archived entries against the Git-tracked provenance inventory.
Never extracts files, executes embedded scripts, or modifies original data.
Requires user-provided ZIP bytes; GitHub CI does not hold this ZIP.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data/exp017_rf_f002_source_zip_index_20261015.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_archive(archive_path, manifest):
    p = Path(archive_path)
    raw = p.read_bytes()
    archive = manifest["archive"]
    if len(raw) != archive["size_bytes"] or sha256(raw) != archive["sha256"]:
        raise ValueError("Original EXP-017 archive SHA-256 or byte size mismatch")
    expected = manifest["members"]
    if len(expected) != archive["member_count"]:
        raise ValueError("Declared member count mismatch")
    by_name = {record["path"]: record for record in expected}
    if len(by_name) != len(expected) or sum(
            row["size_bytes"] for row in expected) != archive["total_uncompressed_bytes"]:
        raise ValueError("Invalid source provenance inventory")
    with zipfile.ZipFile(p) as container:
        info = container.infolist()
        names = [item.filename for item in info]
        if len(info) != len(expected) or set(names) != set(by_name) or len(names) != len(set(names)):
            raise ValueError("EXP-017 ZIP member set differs from checked-in inventory")
        for item in info:
            name = item.filename
            normalized = PurePosixPath(name)
            if (normalized.is_absolute() or ".." in normalized.parts or
                    "\\" in name or not name.startswith("EXP-017/") or item.is_dir()):
                raise ValueError("Unsafe source ZIP member path: " + name)
            # Avoid extracting untrusted content.
            contents = container.read(item)
            entry = by_name[name]
            if (len(contents) != item.file_size or
                    len(contents) != entry["size_bytes"] or
                    sha256(contents) != entry["sha256"]):
                raise ValueError("Source ZIP member checksum mismatch: " + name)
    return {
        "schema_version": manifest["schema_version"],
        "experiment_id": manifest["experiment_id"],
        "constraint_id": manifest["constraint_id"],
        "archive_sha256": archive["sha256"],
        "archive_bytes": len(raw),
        "verified_members": len(expected),
        "all_members_sha256_verified": True,
        "uncompressed_bytes": sum(entry["size_bytes"] for entry in expected),
        "no_file_extraction_or_script_execution": True,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify EXP-017 RF-F002 original ZIP without extracting it")
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--index", default=INDEX, type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    inventory = json.loads(args.index.read_text(encoding="utf-8"))
    if inventory["constraint_id"] != "RF-F002" or inventory["experiment_id"] != "EXP-017":
        raise SystemExit("Incorrect EXP-017 source inventory")
    result = verify_archive(args.zip, inventory)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS EXP-017 RF-F002 original ZIP:", json.dumps(result))


if __name__ == "__main__":
    main()
