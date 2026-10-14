"""Phase 2 status/provenance guardrails; reads historical evidence only.

Does not re-run RF optimization or rewrite old experiments.
"""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(relpath):
    with (ROOT / relpath).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class Phase2CurrentStatusTests(unittest.TestCase):
    def test_current_frontmatter_indicates_merged_prs_but_preserves_history(self):
        roadmap = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
        current, historic = roadmap.split("## 以下は過去時点の記録（現行ステータスではない）", 1)
        self.assertIn("Phase 2 現行状況", current)
        self.assertIn("PR #48", current)
        self.assertIn("PR #52", current)
        self.assertIn("IL≤0.30dB", current)
        self.assertIn("Phase 3", current)
        self.assertIn("未merge", historic)

    def test_exp017_near_0301_is_report_only_and_never_promoted_to_catalog(self):
        source = (ROOT / "experiments/chatgpt_topology_search/runs/EXP-017/README.md").read_text(encoding="utf-8")
        self.assertIn("30dB必須条件での近接値", source)
        self.assertIn("0.301248245", source)
        issues = {x["issue_id"]: x for x in read_csv("data/research_review_issues.csv")}
        self.assertTrue(issues["RG-001"]["status"].startswith("open_"))
        self.assertEqual("EXP-017", issues["RG-001"]["affected_experiments"])
        self.assertIn("ZIP", issues["RG-001"]["problem"])
        curated = read_csv("data/research_candidate_register.csv")
        self.assertFalse(any(abs(float(x["worst_il_db"]) - 0.301248245) < 1e-6 for x in curated))
        older = json.loads((ROOT / "data/validation/exp017_20261012/checkpoints.json").read_text(encoding="utf-8"))
        self.assertEqual("RF-F001", older["candidate"]["formal_constraint_reference"])
        self.assertEqual("NONCANONICAL_UNAPPROVED", older["candidate"]["constraint_status"])

    def test_review_gates_are_traceable_without_fabricating_missing_metadata(self):
        issues = {x["issue_id"]: x for x in read_csv("data/research_review_issues.csv")}
        self.assertEqual(10, len(issues))
        self.assertIn("RG-009", issues)
        self.assertIn("RG-010", issues)
        inventory = read_csv("data/experiment_evidence_inventory.csv")
        self.assertEqual(39, len(inventory))
        self.assertEqual(25, sum(x["seed_recorded"] == "false" for x in inventory))
        self.assertEqual(15, sum(x["execution_sha_recorded"] == "false" for x in inventory))
        self.assertEqual(16, sum(x["environment_recorded"] == "false" for x in inventory))
        self.assertEqual(6, sum(x["registered_evidence_count"] == "0" for x in inventory))


if __name__ == "__main__":
    unittest.main()
