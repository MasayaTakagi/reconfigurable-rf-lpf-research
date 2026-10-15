"""Recovered formal EXP-017 near-miss is genuine and separately replayed.

Never modifies the original EXP-017 manifest or promotes a 3-C RF-T004 trial.
"""
import csv
import hashlib
import json
import math
import unittest
from pathlib import Path

from scripts.verify_exp017_recovered_mna import replay, CANDIDATE, ROOT


class RecoveredFormalCheckpointTests(unittest.TestCase):
    def test_checkpoint_is_complete_and_not_a_trial_substitute(self):
        candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        self.assertEqual("EXP-017", candidate["experiment_id"])
        self.assertEqual("RF-F002", candidate["constraint_id"])
        self.assertEqual("formal", candidate["constraint_class"])
        self.assertEqual(30, candidate["requirement_db"])
        self.assertEqual(23, len(candidate["x_logL_logC_k_6x2Cv_epi"]))
        self.assertEqual(6, len(candidate["topology"]["variable_setting_order"]))
        self.assertEqual(2, len(candidate["topology"]["variable_capacitor_edges"]))
        self.assertEqual(4, len(candidate["topology"]["inductor_series"]))
        self.assertEqual(157492, candidate["source"]["zip_size_bytes"])
        self.assertEqual("e685e918a4592a9ec53ffb8221c8b4d59fdf8604dd9119cf3cabbf42174a0daf",
                         candidate["source"]["zip_sha256"])
        self.assertFalse(candidate["source"]["raw_original_zip_git_committed"])
        self.assertFalse(candidate["status"]["nominal_IL_le_0p30"])
        self.assertTrue(candidate["status"]["source_vector_recovered"])

    def test_byte_exact_original_source_member_is_now_saved_in_git(self):
        candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        src = candidate["source"]
        original_path = ROOT / src["git_original_member_path"]
        bytes_ = original_path.read_bytes()
        self.assertEqual(2959, len(bytes_))
        self.assertEqual(src["git_original_member_bytes"], len(bytes_))
        self.assertEqual("fa997fb131a1237c41ec8a42ead80e40fe2436275a7e944837afecea9c387896",
                         hashlib.sha256(bytes_).hexdigest())
        self.assertEqual(src["git_original_member_expected_sha256"],
                         hashlib.sha256(bytes_).hexdigest())
        original = json.loads(bytes_)
        self.assertEqual(candidate["x_logL_logC_k_6x2Cv_epi"],
                         original["x_logL_logC_k_6x2Cv_epi"])
        self.assertEqual(18, len(original["nominal_metrics"]["crit"]))
        self.assertTrue(original["solver_success"])
        self.assertFalse(candidate["source"]["raw_original_zip_git_committed"])

    def test_independent_full_six_setting_mna_replay(self):
        r = replay(1001)
        self.assertTrue(r["strict_finite_grid_30db"])
        self.assertFalse(r["il_le_0p30db"])
        self.assertEqual(6, len(r["per_setting"]))
        self.assertEqual(28028, r["evaluated_frequency_samples"])
        self.assertAlmostEqual(0.3012482451489075, r["worst_il_db"], places=7)
        self.assertAlmostEqual(30.004999999986865, r["min_h2_db"], places=5)
        self.assertAlmostEqual(30.004641701571376, r["min_h3_db"], places=5)
        self.assertGreater(r["k_min_eigenvalue"], 0.8)
        self.assertLess(r["max_mna_nodal_il_difference_db"], 1e-7)
        self.assertLess(r["max_power_balance_residual_W"], 1e-12)

    def test_curated_formal_register_and_original_manifest_are_separate(self):
        with (ROOT / "data/research_candidate_register.csv").open(newline="",encoding="utf-8") as f:
            rows=list(csv.DictReader(f))
        rec=[r for r in rows if r["catalog_id"]=="EXP017-LQW4-H30-NEAR"]
        self.assertEqual(1,len(rec))
        self.assertEqual("RF-F002_full_lpf_30_strict_finite_grid", rec[0]["comparison_key"])
        self.assertEqual("formal",rec[0]["constraint_class"])
        self.assertGreater(float(rec[0]["worst_il_db"]), 0.30)
        with (ROOT / "data/validation/exp017_rf_f002_recovered_20261015/summary.json").open() as f:
            summary=json.load(f)
        self.assertFalse(summary["source_zip"]["original_zip_committed_to_git"])
        self.assertTrue(summary["reproductions"][0]["reproduction_within_1e-5_db"])
        self.assertEqual(196028,summary["verification"]["solved_samples"])
        manifest=json.loads((ROOT / "experiments/chatgpt_topology_search/runs/EXP-017/manifest.json").read_text())
        self.assertEqual([],manifest["evidence"])


if __name__ == "__main__":
    unittest.main()
