"""W2 regression: source-pinned 24-row structural search and honest unknowns."""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("candidate_topology", ROOT / "scripts/build_phase2_candidate_topology_search.py")
import sys
sys.path.insert(0, str(ROOT / "scripts"))
w2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w2)


class Phase2W2StructureTests(unittest.TestCase):
    def test_24_rows_and_no_fabricated_legacy_topology(self):
        rows, summary = w2.build()
        self.assertEqual(len(rows), 24)
        self.assertEqual(summary["archived_current_rf_candidate_rows_with_reported_signed_k"], 10)
        self.assertEqual(summary["historical_legacy_rows_preserved_as_unknown"], 14)
        older = [r for r in rows if r["structural_metadata_status"] == "legacy_not_extracted"]
        self.assertEqual(len(older), 14)
        self.assertTrue(all(x["coupling_sign_pattern"] == "unknown" and
                            x["inductor_physical_order_as_reported"] == "unknown"
                            for x in older))
        self.assertTrue(all(r["physical_dot_orientation_proven"] == "false" for r in rows))

    def test_three_l_and_four_l_source_signed_k(self):
        rows, _ = w2.build()
        by_id = {r["catalog_id"]: r for r in rows}
        self.assertEqual(by_id["T005_3L_A3_EXP043"]["coupling_sign_pattern"], "+,-")
        self.assertEqual(by_id["T005_3L_A3_EXP043"]["signed_coupling_pair_order"], "L0-Ls;Ls-L1")
        self.assertEqual(by_id["T005_3L_A3p667_EXP045"]["inductor_physical_order_as_reported"], "L0-Ls-L1")
        self.assertEqual(by_id["T005_4L_A6_EXP042"]["signed_coupling_pair_order"], "L0-L1;L1-L3;L3-L2")
        self.assertEqual(by_id["F003_4L_A4p667_EXP047"]["inductor_electrical_edges"],
                         "L0(0,1);L1(1,3);L2(1,4);L3(1,2)")
        self.assertEqual(by_id["F003_4L_A4p667_EXP047"]["coupling_sign_pattern"], "+,+,-")

    def test_checkpoint_sha_change_is_rejected(self):
        original = w2.safe_evidence
        def tamper(root, path):
            if path.endswith("zero_gjm_double.json"):
                return b'{"fake":"tampered"}'
            return original(root, path)
        with patch.object(w2, "safe_evidence", side_effect=tamper):
            with self.assertRaisesRegex(ValueError, "Git blob changed"):
                w2.build()

    def test_checked_in_generated_csv_and_summary_match(self):
        files, _ = w2.make()
        for path, content in files.items():
            with self.subTest(path=path):
                self.assertEqual((ROOT / path).read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
