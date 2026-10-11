"""Independent cross-check between CP07 historical and current area-7 model."""
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"experiments/chatgpt_topology_search/runs/EXP-003/verify_legacy_gap.py"
SPEC=importlib.util.spec_from_file_location("legacy_gap_analysis",PATH)
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HistoricalConstraintGapTests(unittest.TestCase):
    def test_legacy_power_and_new_area7_match(self):
        r=MODULE.compute()
        self.assertEqual(set(r),{"legacy_CP07","legacy_row_reoptimized","area7_A7_01"})
        self.assertAlmostEqual(r["legacy_CP07"]["il_db"],0.3289240193235216,places=7)
        self.assertAlmostEqual(r["legacy_row_reoptimized"]["il_db"],0.3376603645361489,places=7)
        self.assertAlmostEqual(r["area7_A7_01"]["il_db"],0.5083889589116496,places=7)
        for data in r.values():
            total=sum(data[x] for x in (
                "p_load_mw_at_1W_Pavs","p_reflected_mw_at_1W_Pavs",
                "p_inductor_mw_at_1W_Pavs","p_capacitor_mw_at_1W_Pavs"))
            self.assertAlmostEqual(total,1000,places=7)

    def test_historical_noncompliance_remains_explicit(self):
        d=MODULE.DATA
        self.assertFalse(d["legacy_CP07"]["valid_for_current_policy"])
        self.assertFalse(d["legacy_with_2026_10_11_row_coupling"]["valid_for_current_policy"])
        self.assertEqual(len(d["legacy_CP07"]["case_map"]),6)
        self.assertGreater(d["legacy_CP07"]["case_map"]["B71"][0],4)


if __name__=="__main__":
    unittest.main()
