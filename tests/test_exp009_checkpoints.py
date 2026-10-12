"""EXP-009 independent regression for the 3-variable-C cost-6 study."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "experiments/chatgpt_topology_search/runs/EXP-009"

class TestExp009Phase2(unittest.TestCase):
    def command(self, *args):
        env = os.environ.copy()
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["OMP_NUM_THREADS"] = "1"
        out = subprocess.run([sys.executable, *map(str,args)], cwd=ROOT,
                             env=env, text=True, capture_output=True, timeout=180)
        self.assertEqual(out.returncode,0,out.stdout+"\n"+out.stderr)
        return out.stdout

    def test_original_C6_02_reference_is_not_silently_changed(self):
        self.assertIn("reference C6-02 reproduced",
                      self.command(HERE/"sweep.py","--reference-only"))

    def test_six_setting_dense_and_independent_mna_checkpoints(self):
        text=self.command(HERE/"verify.py")
        for name in ("EXP009-01","EXP009-L15","EXP009-L12"):
            self.assertIn(name,text)

if __name__ == "__main__":
    unittest.main()
