"""Regression guardrails for immutable LPF baselines and extensible index."""
import csv
import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from scripts import audit_results
from scripts import verify_no_pcb_tunable_candidates as baseline

ROOT = Path(__file__).resolve().parents[1]


class BaselinePolicyGuardrails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = baseline.read_policy()
        cls.reference = baseline.read_candidate("LPF-007")

    def test_q_model_regression_is_rejected(self):
        candidate = deepcopy(self.reference)
        candidate["topology"]["inductors"][0]["Q"] = 26
        with self.assertRaisesRegex(AssertionError, "Q changed"):
            baseline.check_baseline_metadata(candidate, self.policy)

    def test_fixed_cap_q_regression_is_rejected(self):
        candidate = deepcopy(self.reference)
        candidate["topology"]["fixed_caps"][0]["Q"] = 81
        with self.assertRaisesRegex(AssertionError, "fixed capacitor Q"):
            baseline.check_baseline_metadata(candidate, self.policy)

    def test_variable_cap_connection_and_limit_are_rejected(self):
        candidate = deepcopy(self.reference)
        candidate["topology"]["variable_caps"][0]["b"] = 1
        with self.assertRaises(AssertionError):
            baseline.check_baseline_metadata(candidate, self.policy)
        candidate = deepcopy(self.reference)
        candidate["ic_variable_C_pf_by_setting"]["B8"][0] = 4.1
        with self.assertRaises(AssertionError):
            baseline.check_baseline_metadata(candidate, self.policy)

    def test_saved_performance_cannot_be_rebaselined_silently(self):
        candidate = deepcopy(self.reference)
        candidate["performance"]["worst_IL_db"] += 0.0001
        with self.assertRaisesRegex(AssertionError, "saved reference metric"):
            baseline.check_baseline_metadata(candidate, self.policy)


class CandidateIndexGuardrails(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path in ("data/design_constraints.json", "data/bands.csv",
                     "data/candidate_index.csv", "docs/specification.md",
                     "docs/historical_results.md", "candidates/LPF-007.json",
                     "candidates/LPF-008.json"):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, target)

    def _audit(self):
        with patch.object(audit_results, "ROOT", self.root):
            return audit_results.audit()

    def _add_candidate(self, name):
        item = json.loads((self.root / "candidates/LPF-007.json").read_text())
        item["candidate_id"] = name
        (self.root / "candidates" / (name + ".json")).write_text(json.dumps(item))
        index = self.root / "data/candidate_index.csv"
        with index.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows.append(dict(rows[0], candidate_id=name, evidence=f"candidates/{name}.json"))
        with index.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_additional_current_policy_candidate_does_not_require_audit_edit(self):
        self._add_candidate("LPF-TEST-ADDED")
        self.assertEqual(self._audit(), [])

    def test_duplicate_index_row_is_rejected(self):
        index = self.root / "data/candidate_index.csv"
        with index.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows.append(dict(rows[0]))
        with index.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        self.assertTrue(any("Duplicate candidate" in msg for msg in self._audit()))

    def test_missing_required_baseline_is_rejected(self):
        index = self.root / "data/candidate_index.csv"
        with index.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        with index.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerow(rows[0])
        self.assertTrue(any("Required baseline missing" in msg for msg in self._audit()))


if __name__ == "__main__":
    unittest.main()
