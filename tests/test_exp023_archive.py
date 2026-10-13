"""Regression smoke check for EXP-023 RF-F002 4HV / two-tunable checkpoints."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
EXP=ROOT/"experiments/chatgpt_topology_search/runs/EXP-023"
class TestEXP023Archive(unittest.TestCase):
    def test_candidates_and_repository_MNA_smoke(self):
        for label,required_h in (("30DB",30.0),("35DB",35.0)):
            name="RFF002-P2-4L-2C-"+label+"-01.json"
            with self.subTest(candidate=name):
                d=json.loads((EXP/name).read_text(encoding="utf-8"))
                self.assertEqual(d["constraint_id"],"RF-F002")
                self.assertEqual(len(d["topology"]["variable_capacitor_edges"]),2)
                self.assertEqual(d["phase"],"Phase 2")
                env=dict(os.environ, OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1")
                p=subprocess.run([sys.executable,str(EXP/"verify.py"),str(EXP/name),"--points","3"],cwd=ROOT,capture_output=True,text=True,env=env,timeout=120,check=True)
                obs=json.loads(p.stdout)
                self.assertEqual(obs["candidate"],d["candidate_id"])
                self.assertLess(obs["worst_IL_db"],1.0)
                self.assertGreaterEqual(obs["min_H2_db"],required_h-1e-4)
                self.assertGreaterEqual(obs["min_H3_db"],required_h-1e-4)
                self.assertGreater(obs["worst_IL_db"],0.30)

if __name__=="__main__": unittest.main()
