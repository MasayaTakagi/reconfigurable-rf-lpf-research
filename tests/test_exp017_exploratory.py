"""EXP-017 numerical replay smoke; records remain NONCANONICAL/UNAPPROVED."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from verify_exp017_candidate import verify

class EXP017BridgeTrialSmoke(unittest.TestCase):
    def test_exp017_stays_nonformal_and_passes_independent_nodal(self):
        with contextlib.redirect_stdout(io.StringIO()):
            x=verify(5)
        self.assertLess(x["worst_IL_db"],.5)
        self.assertGreaterEqual(x["min_H2_db"],35.0-1e-5)
        self.assertGreaterEqual(x["min_H3_db"],35.0-1e-5)
        self.assertLess(x["independent_max_IL_difference_db"],1e-8)
        self.assertEqual(x["independent_check_points"],84)
if __name__=="__main__":
    unittest.main()
