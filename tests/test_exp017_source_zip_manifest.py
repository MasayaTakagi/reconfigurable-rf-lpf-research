"""Focused tests for read-only original formal EXP-017 ZIP provenance verification."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.verify_exp017_source_zip import INDEX, verify_archive


class Exp017ZipAuditTests(unittest.TestCase):
    def test_checked_in_inventory_is_self_consistent(self):
        source = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertEqual("RF-F002", source["constraint_id"])
        self.assertEqual("EXP-017", source["experiment_id"])
        self.assertEqual(157492, source["archive"]["size_bytes"])
        self.assertEqual(26, source["archive"]["member_count"])
        self.assertEqual(26, len(source["members"]))
        self.assertEqual(715495, sum(x["size_bytes"] for x in source["members"]))
        self.assertEqual(1, sum(x["git_storage_status"] == "byte_exact_git_copy"
                                for x in source["members"]))
        self.assertFalse(source["archive"]["original_zip_binary_committed_to_git"])

    def test_valid_zip_and_tampering_rejected(self):
        member_name = "EXP-017/example.json"
        member_data = b'{"constraint_id":"RF-F002"}'
        fake = io.BytesIO()
        with zipfile.ZipFile(fake, "w", compression=zipfile.ZIP_DEFLATED) as stream:
            stream.writestr(member_name, member_data)
        source_bytes = fake.getvalue()
        fixture = {
            "schema_version": 1, "experiment_id": "EXP-017", "constraint_id": "RF-F002",
            "archive": {
                "size_bytes": len(source_bytes),
                "sha256": hashlib.sha256(source_bytes).hexdigest(),
                "member_count": 1,
                "total_uncompressed_bytes": len(member_data),
            },
            "members": [{
                "path": member_name, "size_bytes": len(member_data),
                "sha256": hashlib.sha256(member_data).hexdigest(),
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "source.zip"
            file.write_bytes(source_bytes)
            result = verify_archive(file, fixture)
            self.assertTrue(result["all_members_sha256_verified"])
            self.assertEqual(1, result["verified_members"])
            fixture["members"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "member checksum"):
                verify_archive(file, fixture)
            fixture["members"][0]["sha256"] = hashlib.sha256(member_data).hexdigest()
            fixture["members"][0]["path"] = "EXP-017/../escape.json"
            with self.assertRaises(ValueError):
                verify_archive(file, fixture)
            fixture["members"][0]["path"] = member_name
            file.write_bytes(source_bytes + b"x")
            with self.assertRaisesRegex(ValueError, "archive SHA-256"):
                verify_archive(file, fixture)


if __name__ == "__main__":
    unittest.main()
