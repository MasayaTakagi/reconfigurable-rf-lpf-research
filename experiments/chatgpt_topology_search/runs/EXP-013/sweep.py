#!/usr/bin/env python3
"""Phase2 EXP-013 reproducible finite local study, fixed area cost=4."""
import os,sys,json,time,itertools,argparse,hashlib
from pathlib import Path
import numpy as np
from model013 import Model, ALL_EDGES, LEDGES, CASES
HERE=Path(__file__).parent
BASE=json.loads((HERE.parent/'EXP-012'/'C4-PCB-01.json').read_text())
L0=np.array(BASE['values']['L_nH']);K0=np.array(BASE['values']['signed_neighbor_k'])
VV=np.array([BASE['values']['tunable_C_pF_by_setting'][c] for c in CASES]);
LROW=(1,2,3,0); VE=[(4,0),(5,0),(3,1)]; PE=(4,3)

def makejobs(group):
 if group=='pcb1':return [dict(pcb=(e,)) for e in ALL_EDGES]
 if group=='pcb2':return [dict(pcb=(PE,e)) for e in ALL_EDGES if e!=PE]
 if group=='pcb3':return [dict(pcb=(PE,)+z) for z in itertools.combinations([e for e in ALL_EDGES if e!=PE],2)]
 if group=='pcb2_all':return [dict(pcb=z) for z in itertools.combinations(ALL_EDGES,2)]
 if group=='physical_row':return [dict(row=r) for r in itertools.permutations(range(4)) if r!=LROW and r[0]<r[-1]]
 if group=='var3':return [dict(var=(VE[0],VE[1],e)) for e in ALL_EDGES if 0 not in e and e!=VE[2]]
 if group=='var1_var3':return [dict(var=(e,VE[1],VE[2])) for e in ALL_EDGES if e!=VE[0]]
 if group=='var2_var3':return [dict(var=(VE[0],e,VE[2])) for e in ALL_EDGES if e!=VE[1]]
 if group=='ind1':return [dict(ledges=tuple(LEDGES[:i]+[e]+LEDGES[i+1:])) for i in range(4) for e in ALL_EDGES if e!=LEDGES[i]]
 if group=='indpair_main':
  candidates0=[(1,2),(1,3),(1,4),(1,5),(2,3),(2,4),(2,5)]
  candidates3=[(2,3),(1,3),(2,4),(2,5),(3,4),(3,5),(1,4)]
  return [dict(ledges=(a,LEDGES[1],LEDGES[2],b)) for a in candidates0 for b in candidates3 if a!=LEDGES[0] or b!=LEDGES[3]]
 if group=='baseline':return [dict()]
 if group=='pcb3_seed':return [dict(pcb=(PE,)+z) for z in itertools.combinations([e for e in ALL_EDGES if e!=PE],2)]
 raise ValueError(group)

def make_model(job,grid):
 p=job.get('pcb',(PE,));v=job.get('var',VE);ledges=job.get('ledges',LEDGES)
 m=Model(ledges=ledges,cedges=p,var_edges=v,n=grid,fixed_q=[40]*len(p),fixed_ranges=[(.02,.2)]*len(p));row=list(job.get('row',LROW));m.row=row;m.neighbor=[(row[i],row[i+1]) for i in range(3)];return m

def x0(m,seed,idx):
 x=np.r_[np.log(L0),np.log([.02000005 if e==PE else .020001 for e in m.cedges]),np.zeros(3),np.zeros((6,3)).ravel(),.30482]
 kmap={frozenset(LROW[i:i+2]):K0[i] for i in range(3)}
 for i,(a,b) in enumerate(m.neighbor):
  z=kmap.get(frozenset((a,b)),0)
  x[m.kstart+i]=z
 for j,e in enumerate(m.var_edges):
  if e in VE:x[m.vstart+j::3][:6]=VV[:,VE.index(e)]
  elif (e[1],e[0]) in VE:x[m.vstart+j::3][:6]=VV[:,VE.index((e[1],e[0]))]
  else:x[m.vstart+j::3][:6]=.15
 if idx:
  rng=np.random.default_rng(seed)
  x[:4]+=rng.normal(0,.07,4)
  x[4:m.kstart]+=rng.normal(0,.1,m.nc)
  x[m.kstart:m.vstart]+=rng.normal(0,.02,3)
  x[m.vstart:-1]+=rng.normal(0,.035,18)
  x[-1]=.32
 return np.clip(x,np.array(m.bounds)[:,0]+1e-10,np.array(m.bounds)[:,1]-1e-10)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--group',required=True);ap.add_argument('--first',type=int,default=0);ap.add_argument('--last',type=int,default=-1);ap.add_argument('--starts',type=int,default=2);ap.add_argument('--grid',type=int,default=21);ap.add_argument('--maxiter',type=int,default=140);ap.add_argument('--target',type=float,default=30.0001);ap.add_argument('--out',default='');a=ap.parse_args()
 jobs=makejobs(a.group);out=Path(a.out or (HERE/(a.group+'.jsonl')));out.parent.mkdir(parents=True,exist_ok=True)
 hist=[];done=set()
 if out.exists():
  for line in out.read_text().splitlines():
   try:r=json.loads(line);hist.append(r);done.add((r['job_index'],r['start']))
   except:pass
 start=a.first;end=len(jobs) if a.last<0 else min(a.last,len(jobs));begin=time.time()
 for ji in range(start,end):
  job=jobs[ji]
  for si in range(a.starts):
   if (ji,si) in done:continue
   seed=20261012+ji*917+si*131
   try:
    m=make_model(job,a.grid);x=x0(m,seed,si)
    r=m.optimize(x,goal=a.target,maxiter=a.maxiter)
   except Exception as e:r={'error':str(e)}
   record={'group':a.group,'job_index':ji,'job':job,'start':si,'seed':seed,'grid':a.grid,'maxiter':a.maxiter,'goal':a.target,'run':r}
   with out.open('a') as f:f.write(json.dumps(record,allow_nan=False)+'\n')
   hist.append(record)
   if 'IL' in r:
    print(a.group,ji,si,'IL',round(r['IL'],7),'H',round(min(r['H2'],r['H3']),6),'nit',r['niter'],'conv',r['success'],flush=True)
   else:print(a.group,ji,si,'ERROR',r['error'],flush=True)
 feasible=[z for z in hist if 'IL' in z['run'] and min(z['run']['H2'],z['run']['H3'])>=30]
 vals=sorted(feasible,key=lambda x:x['run']['IL'])
 print('DONE',a.group,'attempted',len(hist),'feasible',len(feasible),'best',[(x['job_index'],x['start'],x['run']['IL']) for x in vals[:4]],'elapsed',round(time.time()-begin,2),flush=True)
if __name__=='__main__':main()