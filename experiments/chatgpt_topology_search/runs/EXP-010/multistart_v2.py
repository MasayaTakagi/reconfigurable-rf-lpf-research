#!/usr/bin/env python3
"""EXP010 incremental local multistart from saved verified checkpoints, always Q25, Q80, Q40."""
import json,time,sys,csv,argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT=Path('/mnt/data/_smoke_root/experiments/chatgpt_topology_search/runs/EXP-010')
sys.path.insert(0,str(ROOT))
from mixed_study import Model,jobs,reference_vector,BANDS
P=Path('/mnt/data/exp010')
CASES=('B71','B12','B28','B13+B14','B26','B8')
pa=argparse.ArgumentParser();pa.add_argument('--count',type=int,default=24);pa.add_argument('--start',type=int,default=0);pa.add_argument('--iterations',type=int,default=75);pa.add_argument('--n',type=int,default=13);pa.add_argument('--target',type=float,default=30.007);pa.add_argument('--out',default='multistart_v2.json');args=pa.parse_args()
model=Model(jobs('baseline')[0],list(csv.DictReader(BANDS.open())))
ref=[json.load(open(P/(f'EXP010-0{i}.json'))) for i in range(2,5)]
bounds=model.bounds();lower=np.array([a for a,b in bounds]);upper=np.array([b for a,b in bounds]);output=P/args.out
state={'method':'SLSQP','scope':'Q25 4L 3GJM Q80, Q40 PCB C, 3 C Q80, all six settings; local multistart','target_rejection_db':args.target,'optimization_grid':args.n,'records':[],'unfinished':True}
if output.exists():state=json.load(open(output))
for ix in range(args.start,args.start+args.count):
 if any(rec['index']==ix for rec in state['records']):continue
 rng=np.random.default_rng(20261012+10019*ix)
 base=ref[ix%3];x=reference_vector(base)
 if ix:
  scale=[0.0,.025,.07,.15,.25][(ix//3)%5]
  x[:8]+=rng.normal(0,scale,8)
  x[8:11]+=rng.normal(0,min(.05,.3*scale),3)
  x[11:-1]+=rng.normal(0,scale*.6,18)
  if ix%7==0:
   x[5]=np.log(.1) # Cf2 0.1 pF
 x=np.clip(x,lower+1e-10,upper-1e-10)
 metric_cache=[None,None];evals=0
 def metric(a):
  global evals
  if metric_cache[0] is None or not np.array_equal(a,metric_cache[0]):
   metric_cache[:]=[a.copy(),model.metrics(a,args.n)];evals+=1
  return metric_cache[1]
 def con(a):
  mat=metric(a)
  return np.r_[a[-1]-mat[:,0],mat[:,1]-args.target,mat[:,2]-args.target]
 t=time.monotonic()
 try:
  res=minimize(lambda z:z[-1],x,method='SLSQP',bounds=bounds,constraints=[{'type':'ineq','fun':con}],options={'maxiter':args.iterations,'ftol':1e-9})
  m=model.metrics(res.x,201)
  rec={'index':ix,'seed':20261012+10019*ix,'start_id':base['id'],'result':{'worstIL':float(m[:,0].max()),'minH2':float(m[:,1].min()),'minH3':float(m[:,2].min()),'success':bool(res.success),'message':str(res.message),'nit':int(res.nit),'nfev':int(res.nfev),'metrics201':m.tolist(),'x':res.x.tolist(),'seconds':time.monotonic()-t,'evaluation_count':evals}}
 except Exception as exc:rec={'index':ix,'error':repr(exc),'seconds':time.monotonic()-t}
 state['records'].append(rec);output.write_text(json.dumps(state,indent=2)+'\n')
 if 'result' in rec:
  print(ix,round(rec['result']['worstIL'],9),round(min(rec['result']['minH2'],rec['result']['minH3']),6),rec['result']['success'],round(rec['result']['seconds'],2),flush=True)
 else:print(ix,'failed',rec['error'],flush=True)
state['unfinished']=False;output.write_text(json.dumps(state,indent=2)+'\n')