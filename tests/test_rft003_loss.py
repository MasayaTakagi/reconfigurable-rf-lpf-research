"""Numerical power-accounting smoke for RF-T003 loss study."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))
from analyze_rft003_loss import run

class TestRFT003LossStudy(unittest.TestCase):
    def test_3C_reference_and_per_component_power_conservation(self):
        r=run(5)
        self.assertEqual(len(r["circuits"]),3)
        t=r["circuits"]["RF-T003_2C_HV"]["by_case"]
        h=r["circuits"]["EXP015_3C_HQ"]["by_case"]
        v=r["circuits"]["EXP015_3C_HV"]["by_case"]
        for c in t:
            self.assertAlmostEqual(sum(t[c]["P_inductor_mW"])+sum(t[c]["P_capacitor_mW"]),
                                   t[c]["P_heat_total_mW"],places=8)
            self.assertAlmostEqual(5.,t[c]["P_heat_total_mW"]
                 +t[c]["P_reflected_mW"]+t[c]["P_load_mW"],places=8)
            self.assertLess(t[c]["max_MNA_delta_dB"],1e-8)
        self.assertAlmostEqual(t["B28"]["IL_dB"],0.376495318564264,delta=2e-6)
        self.assertAlmostEqual(t["B8"]["IL_dB"],0.376495318564264,delta=2e-6)
        self.assertAlmostEqual(h["B28"]["IL_dB"],0.3019453791082774,delta=2e-6)
        self.assertAlmostEqual(v["B28"]["IL_dB"],0.32140280187014103,delta=2e-6)
        self.assertGreater(t["B28"]["P_inductor_mW"][3],.18)
        self.assertGreater(t["B28"]["P_inductor_total_mW"],
                           t["B28"]["P_capacitor_total_mW"])

if __name__=="__main__":
    unittest.main()
