"""Phase 2 CI must run once per PR change and after a main merge."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Phase2WorkflowSchedulingTests(unittest.TestCase):
    def test_full_suite_covers_main_push_and_pull_request_without_double_trigger(self):
        body = (ROOT / ".github/workflows/audit.yml").read_text(encoding="utf-8")
        self.assertIn("on:\n  push:\n    branches:\n      - main\n  pull_request:", body)
        self.assertIn("workflow_dispatch:", body)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", body)
        self.assertIn("python -m unittest discover -s tests -v", body)
        self.assertIn("scripts/audit_branch_retention.py", body)
        self.assertIn("scripts/report_experiment_metadata_gaps.py", body)
        self.assertIn("scripts/triage_unlinked_evidence.py", body)


if __name__ == "__main__":
    unittest.main()
