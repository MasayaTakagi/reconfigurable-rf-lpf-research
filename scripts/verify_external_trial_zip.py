#!/usr/bin/env python3
"""Read-only SHA-256/CRC audit of an EXTERNAL trial ZIP against its ledger.

Never extracts, executes, rewrites, or promotes the RF-T004 trial as formal.
The ZIP itself is intentionally NOT stored inside the Git repository.
"""
import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/external_trial_zip_manifest_20261015.json"


def verify_zip(path, manifest_path=MANIFEST):
    path = Path(path)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest["constraint_id"] != "RF-T004" or manifest["formal_exp017_30db_vector_recovered"] is not False:
        raise ValueError("Formal/trial scope cannot be changed")
    if manifest["original_archive_held_in_github"] is not False:
        raise ValueError("Do not claim GitHub archive retention")
    if manifest["archive_retention_verified"] is not False:
        raise ValueError("Manifest is provenance only, not a verified durable archive")
    if path.stat().st_size != manifest["raw_bytes"]:
        raise ValueError("Wrong ZIP size")
    with path.open("rb") as fd:
        actual_archive_sha256 = hashlib.file_digest(fd, "sha256").hexdigest()
    if actual_archive_sha256 != manifest["archive_sha256"]:
        raise ValueError("ZIP SHA-256 differs from preserved source")
    checks = {}
    for row in manifest["members"]:
        name = row["path"]
        q = PurePosixPath(name)
        if (not name or "\\" in name or q.is_absolute() or ".." in q.parts or
                name.startswith("./") or name.endswith("/") or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])):
            raise ValueError("Unsafe member path or hash in source manifest")
        if name in checks:
            raise ValueError("Duplicated ZIP member in source manifest")
        if row["bytes"] < 0 or row["bytes"] > 8_000_000:
            raise ValueError("Invalid member size")
        checks[name] = row
    if len(checks) != manifest["members_count"]:
        raise ValueError("Member count disagrees")
    if sum(row["bytes"] for row in checks.values()) != manifest["uncompressed_bytes"]:
        raise ValueError("Uncompressed member size disagrees")
    with zipfile.ZipFile(path) as archive:
        found = archive.infolist()
        if len(found) != manifest["members_count"]:
            raise ValueError("ZIP file count disagrees")
        seen = set()
        for entry in found:
            name = entry.filename
            if name not in checks or name in seen:
                raise ValueError("Unexpected or repeated ZIP entry")
            seen.add(name)
            mode = (entry.external_attr >> 16) & 0o170000
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Refusing symlink ZIP entry")
            row = checks[name]
            if entry.file_size != row["bytes"] or f"{entry.CRC:08x}" != row["crc32"]:
                raise ValueError("ZIP central directory differs for " + name)
            with archive.open(entry) as member:
                content = member.read(row["bytes"] + 1)
            if len(content) != row["bytes"]:
                raise ValueError("Member data size mismatch")
            if hashlib.sha256(content).hexdigest() != row["sha256"]:
                raise ValueError("Member SHA-256 mismatch for " + name)
        if seen != set(checks):
            raise ValueError("Missing member entry")
    return {
        "phase": "Phase 2",
        "archive_sha256": actual_archive_sha256,
        "verified_members": len(checks),
        "verified_uncompressed_bytes": manifest["uncompressed_bytes"],
        "crc_pass": True,
        "member_sha256_pass": True,
        "formal_rf_f002_checkpoint_restored": False,
        "original_zip_is_durably_archived_in_repo": False,
        "raw_archive_files_mutated": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    report = verify_zip(args.zip, args.manifest)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS external trial ZIP SHA-256, 35 member SHA-256 and CRC; not RF-F002 formal")


if __name__ == "__main__":
    main()
