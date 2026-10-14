"""Integrity tests for preserved Phase 2 archives; no extraction or RF claims."""
import unittest

from scripts.verify_archived_evidence_packages import (
    _safe_relative, check_checkpoint_zip, check_source_archive,
)


class ArchivedEvidenceIntegrityTests(unittest.TestCase):
    def test_saved_source_pr38_checksums(self):
        summary = check_source_archive()
        self.assertEqual(18, summary["sha256_entries_verified"])
        self.assertTrue(summary["files_unchanged"])

    def test_r1_zip_structure_and_crc(self):
        summary = check_checkpoint_zip()
        self.assertGreater(summary["zip_member_count"], 0)
        self.assertTrue(summary["all_zip_crc_passed"])
        self.assertFalse(summary["zip_extraction_performed"])
        self.assertFalse(summary["rf_validation_performed"])

    def test_unsafe_archive_paths_not_accepted(self):
        for p in ("", "/absolute", "../escape", "x/../../escape",
                  "x/../y", "x\\escape"):
            with self.subTest(path=p):
                with self.assertRaises(ValueError):
                    _safe_relative(p)


if __name__ == "__main__":
    unittest.main()
