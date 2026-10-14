"""Regression for source-link audit on manifests with no registered evidence."""
import unittest

from scripts.audit_supplemental_evidence import (
    KNOWN_EMPTY, check_supplemental_evidence, git_blob_sha1,
)


class SupplementalEvidenceTests(unittest.TestCase):
    def test_git_sha_matches_known_vector(self):
        self.assertEqual("ce013625030ba8dba906f756967f9e9ca394464a",
                         git_blob_sha1(b"hello\n"))

    def test_non_promoting_source_links(self):
        self.assertEqual(6, len(KNOWN_EMPTY))
        self.assertEqual([], check_supplemental_evidence())


if __name__ == "__main__":
    unittest.main()
