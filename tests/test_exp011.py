"""Independently recompute Phase2 6-setting 4L/1C/3IC reference at high density."""
import sys,json,unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'experiments/chatgpt_topology_search/runs/EXP-011'

def get_module(file,alias):
 spec=importlib.util.spec_from_file_location(alias,HERE/file)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
class TestExp011(unittest.TestCase):
 def test_dense_and_9x9_mna(self):
  v=get_module('verify.py','exp011_verify')
  for stem in ('EXP011-01','EXP011-02'):
   d=json.loads((HERE/(stem+'.json')).read_text());found=v.analyze(d,grid=7001)
   saved=d['verified_dense_metrics']
   for key in ('worst_IL_db','min_H2_db','min_H3_db'):
    self.assertAlmostEqual(found[key],saved[key],delta=1e-7)
   self.assertLess(found['max_power_balance_W'],1e-12)
   self.assertEqual(found['independent_9x9_MNA_representative_points'],54)
 def test_analytic_jacobian(self):
  import csv
  opt=get_module('compact_search.py','exp011_compact')
  d=json.loads((HERE/'EXP011-01.json').read_text())
  with (ROOT/'data/bands.csv').open(newline='') as band_file:
   bands=list(csv.DictReader(band_file))
  mdl=opt.Compact(d,bands,points=3)
  self.assertEqual(len(opt.jobs('ind_edges',d)),56)
  x=mdl.ref_x(d);_,jac=mdl._eval(x)
  diffs=[]
  for i in (0,1,2,3,4,5,6,7,8,9,12,17,25):
   if i==len(x)-1:continue
   z=x.copy();z[i]+=1e-6
   y=x.copy();y[i]-=1e-6
   finite=(mdl._eval(z)[0]-mdl._eval(y)[0])/2e-6
   diffs.append(max(abs(finite-jac[:,i]))/max(1,max(abs(finite))))
  self.assertLess(float(max(diffs)),2e-4)
if __name__=='__main__':unittest.main()