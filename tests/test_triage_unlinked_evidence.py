"""Regression tests for Phase 2 provenance triage; no evidence mutation."""
import unittest
from pathlib import Path

from scripts.triage_unlinked_evidence import (
    EXCLUDE_TEXT_SOURCES, _ref_hits, build_triage, to_csv,
)


class TriageEvidenceTests(unittest.TestCase):
    def test_exact_full_path_not_prefix(self):
        needle = "data/validation/run/example.json"
        self.assertTrue(_ref_hits(f"see " + needle + " in report", needle))
        self.assertFalse(_ref_hits(needle + ".bak", needle))
        self.assertFalse(_ref_hits("copy/" + needle, needle))

    def test_review_does_not_confer_disposition_to_delete(self):
        rows, summary = build_triage()
        self.assertEqual(46, len(rows))
        self.assertEqual(46, summary["classified_rows"])
        self.assertEqual(0, summary["deletions_or_moves_executed"])
        self.assertTrue(summary["all_dispositions_retain"])
        self.assertEqual({"experiment": 18, "legacy_candidate": 2,
                          "validation": 26}, summary["locations"])
        self.assertEqual(
            len({r["review_id"] for r in rows}), len(rows))
        self.assertEqual(
            len({r["path"] for r in rows}), len(rows))
        self.assertTrue(all(
            r["disposition"] == "retain_pending_source_context_review"
            for r in rows))
        self.assertTrue(all(Path(r["path"]).is_relative_to(".") for r in rows))
        self.assertNotIn("data/research_storage_triage.csv",
                         [r["path"] for r in rows])
        self.assertIn("data/research_storage_triage.csv", EXCLUDE_TEXT_SOURCES)
        self.assertEqual(len(rows) + 1, len(to_csv(rows).splitlines()))


if __name__ == "__main__":
    unittest.main()
