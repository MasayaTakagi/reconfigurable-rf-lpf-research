import os,sys,json,time,argparse
from pathlib import Path
import numpy as np
from sweep import make_model
from model013 import CASES
p=argparse.ArgumentParser();p.add_argument('--source',default='physical_row');p.add_argument('--n-best',type=int,default=6);p.add_argument('--grid',type=int,default=61);p.add_argument('--maxiter',type=int,default=240);p.add_argument('--jitter',type=int,default=2);a=p.parse_args()
fn=Path(__file__).parent/(a.source+'.jsonl');rs=[json.loads(l) for l in fn.read_text().splitlines() if l.strip()];feasible=[x for x in rs if 'IL' in x['run'] and min(x['run']['H2'],x['run']['H3'])>=30.0]
base=sorted(feasible,key=lambda x:x['run']['IL'])[:a.n_best];out=Path(__file__).parent/('refine_'+a.source+'.jsonl');done=set()
if out.exists():
 for l in out.read_text().splitlines():
  z=json.loads(l);done.add((z['source_idx'],z['run_idx']))
for j,z in enumerate(base):
 for t in range(a.jitter):
  if (j,t) in done:continue
  mod=make_model(z['job'],a.grid)
  x=np.array(z['run']['x'],float)
  if t:
   rng=np.random.default_rng(20261012+j*103+t)
   x[:4]+=rng.normal(0,.012,4);x[4:mod.kstart]+=rng.normal(0,.03,mod.nc)
   x[mod.kstart:mod.vstart]+=rng.normal(0,.008,3)
   x[mod.vstart:-1]+=rng.normal(0,.012,18)
  x=np.clip(x,np.array(mod.bounds)[:,0]+1e-11,np.array(mod.bounds)[:,1]-1e-11)
  r=mod.optimize(x,goal=30.00005,maxiter=a.maxiter)
  m=mod.metrics(np.array(r['x']),n=1001)
  v=dict(source=a.source,source_idx=j,run_idx=t,base=z['job'],source_trial=z['job_index'],res=r,verification_1001=m)
  with out.open('a') as f:f.write(json.dumps(v)+'\n')
  print(a.source,j,t,'IL201',r['IL'],'H',min(r['H2'],r['H3']),'IL1001',m['IL'],'H1001',min(m['H2'],m['H3']),'success',r['success'],flush=True)