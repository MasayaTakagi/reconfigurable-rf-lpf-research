"""Phase 2 RF-T004 EXP-022 finite-grid numerical reproducibility regression."""
import csv
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments/chatgpt_topology_search/runs/EXP-022"


class TestEXP022Archive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        target = EXP / "audit_archive.py"
        spec = importlib.util.spec_from_file_location("exp022_archive_audit", target)
        cls.verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.verifier)
        with (ROOT / "data/bands.csv").open(encoding="utf-8", newline="") as f:
            cls.bands = list(csv.DictReader(f))

    def test_saved_candidates_nominal_model_and_independent_mna(self):
        for name, worst_il, min_harm in (
            ("C-H30p0002", 0.3054812436663839, 30.0002),
            ("C-H30p02", 0.3057201115558825, 30.02),
        ):
            with self.subTest(candidate=name):
                candidate = json.loads((EXP / (name + ".json")).read_text(encoding="utf-8"))
                observed = self.verifier.audit(candidate, self.bands)
                self.assertTrue(observed["saved_metrics_match_canonical_model"])
                self.assertTrue(observed["meets_minimum_30dB"])
                self.assertFalse(observed["meets_IL_0p30dB"])
                self.assertEqual(observed["independent_branch_MNA_points"], 84)
                self.assertAlmostEqual(observed["recomputed_max_IL_db"], worst_il, delta=2e-5)
                self.assertAlmostEqual(min(observed["recomputed_min_H2_db"],
                                           observed["recomputed_min_H3_db"]),
                                       min_harm, delta=2e-5)


if __name__ == "__main__":
    unittest.main()
