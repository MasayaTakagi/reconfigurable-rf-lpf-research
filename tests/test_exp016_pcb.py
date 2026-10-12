"""Numerical regression for saved EXP-016 PCB-C Phase 2 checkpoints."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from verify_exp016_pcb_followup import verify

class TestEXP016PCBCheckpoint(unittest.TestCase):
    def test_both_saved_candidates_with_independent_mna(self):
        # The high-density 7,001-point/interval comparison remains an optional
        # longer verification; this test is a finite segmented smoke.
        with contextlib.redirect_stdout(io.StringIO()) as output:
            verify(5)
        text=output.getvalue()
        self.assertIn("EXP016-PCB-COMPACT-01",text)
        self.assertIn("EXP016-PCB-MARGIN-01",text)

if __name__=="__main__":
    unittest.main()
