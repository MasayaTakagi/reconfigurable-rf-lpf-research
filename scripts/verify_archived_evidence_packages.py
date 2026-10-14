#!/usr/bin/env python3
"""Verify integrity of saved source_pr38 checksum manifest and R1 checkpoint ZIP.

This checks bytes, archive paths and ZIP CRC only. It is not numerical RF
verification, and preserves original archive files byte-for-byte.
"""
import hashlib
import json
import posixpath
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA_FILE = "experiments/chatgpt_topology_search/runs/EXP-020/source_pr38/SHA256SUMS"
ZIP_FILE = "data/validation/r1_20261012/completed-checkpoint.zip"


def _safe_relative(path):
    if not path or "\\" in path or path.startswith("/"):
        raise ValueError("Unsafe archive reference: " + path)
    normalized = posixpath.normpath(path)
    if normalized != path or normalized.startswith("../") or normalized == "..":
        raise ValueError("Archive reference traverses outside folder: " + path)
    return path


def check_source_archive(root=ROOT):
    root = Path(root)
    sha_path = root / SHA_FILE
    archive_dir = sha_path.parent
    lines = sha_path.read_text(encoding="utf-8").splitlines()
    hashes = {}
    for line in lines:
        if "  " not in line:
            raise ValueError("Not a SHA256SUMS source line")
        expected, rel = line.split("  ", 1)
        if len(expected) != 64 or any(x not in "0123456789abcdef" for x in expected):
            raise ValueError("SHA-256 digest must contain 64 lowercase hex digits")
        rel = _safe_relative(rel)
        if rel in hashes:
            raise ValueError("Duplicate checksum entry " + rel)
        content = (archive_dir / rel).read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            raise ValueError("Archived SHA256SUMS mismatch: " + rel)
        hashes[rel] = actual
    archived = {
        p.relative_to(archive_dir).as_posix() for p in archive_dir.rglob("*")
        if p.is_file() and p != sha_path
    }
    if archived != set(hashes):
        raise ValueError("SHA256SUMS omits archive files or lists absent files")
    return {"sha256_entries_verified": len(hashes),
            "checksum_file_git_relative_path": SHA_FILE,
            "files_unchanged": True}


def check_checkpoint_zip(root=ROOT):
    archive = Path(root) / ZIP_FILE
    total = archive.stat().st_size
    with zipfile.ZipFile(archive) as package:
        infos = package.infolist()
        if not infos:
            raise ValueError("Checkpoint ZIP empty")
        for member in infos:
            # No extraction; nevertheless reject unsafe members that would
            # make future user extraction ambiguous.
            rel = member.filename.rstrip("/")
            if rel:
                _safe_relative(rel)
        bad = package.testzip()
        if bad is not None:
            raise ValueError("ZIP CRC mismatch: " + bad)
    return {
        "zip_git_relative_path": ZIP_FILE,
        "zip_bytes": total,
        "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "zip_member_count": len(infos),
        "all_zip_crc_passed": True,
        "zip_extraction_performed": False,
        "rf_validation_performed": False,
    }


def main():
    report = {
        "phase": "Phase 2",
        "integrity_scope": "saved_archive_checksums_and_zip_crc_only",
        "pr38_source": check_source_archive(),
        "r1_checkpoint": check_checkpoint_zip(),
        "no_deletion_or_migration": True,
    }
    print("PASS archived provenance integrity:", json.dumps(report,
                                                       ensure_ascii=False))


if __name__ == "__main__":
    main()
