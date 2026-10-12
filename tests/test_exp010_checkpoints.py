"""Phase 2 EXP-010 saved-solution independent numerical regression."""
import os,subprocess,sys,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'experiments/chatgpt_topology_search/runs/EXP-010'

class TestEXP010(unittest.TestCase):
    def run_script(self,name,*args):
        env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        r=subprocess.run([sys.executable,str(HERE/name),*args],cwd=ROOT,capture_output=True,text=True,
                         timeout=180,env=env)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        return r.stdout

    def test_previous_baseline_is_preserved(self):
        self.assertIn('EXP009-02 regression passed',self.run_script('study.py','--reference-only'))

    def test_Q25_extended_legacy_GJM_checkpoint(self):
        self.assertIn('EXP010-01',self.run_script('verify.py'))

    def test_all_four_mixed_GJM_PCB_C_checkpoints(self):
        s=self.run_script('verify_mixed.py')
        for k in ('EXP010-02','EXP010-03','EXP010-04','EXP010-05'):
            self.assertIn(k,s)
        self.assertIn('"global_optimum_proven": false',s)

    def test_new_topology_engine_reference(self):
        self.assertIn('EXP010-02 reference reproduced',self.run_script('mixed_study.py','--reference-only'))

if __name__=='__main__':unittest.main()