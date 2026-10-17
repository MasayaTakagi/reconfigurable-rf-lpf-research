"""Regression tests for Phase 2 provenance triage; no evidence mutation."""
import unittest
from pathlib import Path

from scripts.triage_unlinked_evidence import (
    EXCLUDE_TEXT_SOURCES, _ref_hits, build_triage, check_snapshot,
    resolved_markdown_references, to_csv,
)


class TriageEvidenceTests(unittest.TestCase):
    def test_exact_full_path_not_prefix(self):
        needle = "data/validation/run/example.json"
        self.assertTrue(_ref_hits(f"see " + needle + " in report", needle))
        self.assertFalse(_ref_hits(needle + ".bak", needle))
        self.assertFalse(_ref_hits("copy/" + needle, needle))

    def test_resolve_relative_markdown_links_without_promoting_web_urls(self):
        tracked = {"docs/source.md", "data/validation/a.json"}
        texts = {"docs/source.md": "[checkpoint](../data/validation/a.json) "
                 "[wrong](https://site.invalid/data/validation/a.json)"}
        refs = resolved_markdown_references(texts, tracked)
        self.assertEqual({"docs/source.md"}, refs["data/validation/a.json"])
        self.assertEqual(1, len(refs))

    def test_checked_in_all_46_paths_match_current_github_tracked_bytes(self):
        summary = check_snapshot()
        self.assertEqual(46, summary["input_review_file_count"])
        self.assertEqual(32, summary["review_classes"]["text_linked_requires_semantic_review"])
        self.assertEqual(9, summary["review_classes"]["content_equal_requires_run_role_review"])
        self.assertEqual(5, summary["review_classes"]["experiment_source_not_indexed"])
        self.assertEqual(26, summary["resolved_markdown_link_hits"])
        self.assertEqual(0, summary["deletions_or_moves_executed"])

    def test_review_does_not_confer_disposition_to_delete(self):
        rows, summary = build_triage()
        self.assertGreaterEqual(len(rows), 46)
        self.assertEqual(len(rows), summary["classified_rows"])
        self.assertEqual(0, summary["deletions_or_moves_executed"])
        self.assertTrue(summary["all_dispositions_retain"])
        self.assertEqual(len(rows), sum(summary["locations"].values()))
        self.assertGreaterEqual(summary["locations"].get("experiment", 0), 18)
        self.assertGreaterEqual(summary["locations"].get("legacy_candidate", 0), 2)
        self.assertGreaterEqual(summary["locations"].get("validation", 0), 26)
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
