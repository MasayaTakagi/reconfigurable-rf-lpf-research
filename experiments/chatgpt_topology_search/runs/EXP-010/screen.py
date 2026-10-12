"""EXP-010 Phase 2: Q25, LQP02HQ model <=56nH. Local graphs, NOT global bound."""
import os,sys,json,csv,time,itertools
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'EXP-009'
sys.path.insert(0,str(PREV))
from sweep import Model,CASES,LINDS,BASE_TUNE,BASE_FIXED,outer
OUT=HERE/'results'
OUT.mkdir(exist_ok=True)
REF=json.loads((PREV/'EXP009-02.json').read_text())
BANDS=list(csv.DictReader((ROOT/'data/bands.csv').open()))
FIXED=((0,2),(4,-1),(2,3)) # EXP009-02 Cf1 Cf2 Cf3
TUNE=BASE_TUNE
BASE_ROW=(1,2,3,0)
L=np.array([z['L_nH'] for z in REF['topology']['inductors']])
C=np.array([z['C_pF'] for z in REF['topology']['fixed_capacitors']])
K=np.array(REF['topology']['signed_adjacent_k'])
VC=np.array([REF['variable_C_pf_by_setting'][b] for b in CASES])
XBASE=np.r_[np.log(L),np.log(C),K,VC.ravel(),.32]

class CircuitModel(Model):
 def bounds(self):
  b=super().bounds()
  for i in range(4):b[i]=(np.log(.4),np.log(56.))
  return b
 def __init__(self,fix,tun,row=BASE_ROW):
  job={'fixed_edges':fix,'variable_edges':tun}
  super().__init__(job,BANDS)
  self.row=tuple(row)
  self.F=tuple(tuple(e) for e in fix)
  self.T=tuple(tuple(e) for e in tun)
  self.B=np.zeros((5,4))
  for i,(a,b) in enumerate(LINDS):self.B[a,i]+=1;self.B[b,i]-=1
  self.Dfix=np.array([outer(e) for e in self.F]);self.Dvar=np.array([outer(e) for e in self.T])
 def metrics(self,x,n):
  l=np.exp(x[:4])*1e-9;c=np.exp(x[4:7])*1e-12;k=x[7:10]
  tc=x[10:-1].reshape(6,len(self.T))*1e-12
  K=np.eye(4);M=np.diag(l.astype(complex))
  for i,ki in enumerate(k):
   a,b=self.row[i:i+2];K[a,b]=K[b,a]=ki;M[a,b]=M[b,a]=ki*np.sqrt(l[a]*l[b])
  if np.linalg.eigvalsh(K).min()<=1e-5:return np.full((6,3),1e3)
  coil=self.B@np.linalg.solve(np.diag(l/25)+1j*M,self.B.T)
  cyfix=np.einsum('a,abc->bc',c/(1/80-1j),self.Dfix)
  cyvar=np.einsum('sa,abc->sbc',tc/(1/80-1j),self.Dvar)
  out=np.empty((6,3))
  for i,segments in enumerate(self.grids_for(n)):
   cap=cyfix+cyvar[i]
   for j,w in enumerate(segments):
    Y=self.ports[None,:,:]+coil[None,:,:]/w[:,None,None]+w[:,None,None]*cap[None,:,:]
    v=np.linalg.solve(Y,np.broadcast_to(self.src,(len(w),5))[...,None])[...,0]
    att=-10*np.log10(np.maximum(200*60/5200*np.abs(v[:,2])**2,1e-300))
    out[i,j]=att.max() if j==0 else att.min()
  return out
 def xstart(self,seed=0):
  x=XBASE.copy()
  rng=np.random.default_rng(seed)
  # inherited global K on physically common neighboring pairs
  if self.row!=BASE_ROW:
   old=dict((tuple(sorted(BASE_ROW[i:i+2])),K[i]) for i in range(3))
   x[7:10]=[old.get(tuple(sorted(self.row[i:i+2])),0.) for i in range(3)]
  if self.T!=TUNE:
   old={e:ii for ii,e in enumerate(TUNE)}
   vals=np.array([VC[:,old[e]] if e in old else np.clip(VC[:,2]*.9,.02,3.9) for e in self.T]).T
   x[10:-1]=vals.ravel()
  if seed:
   x[:4]+=rng.normal(0,.035,4)
   x[4:7]+=rng.normal(0,.05,3)
   x[7:10]+=rng.normal(0,.025,3)
   x[10:-1]+=rng.normal(0,.03,18)
  lo=np.array([v[0] for v in self.bounds()]);hi=np.array([v[1] for v in self.bounds()])
  return np.clip(x,lo,hi)

def optim(model,x,pts=11,iterations=140,target=30.025):
 bounds=model.bounds();cache=[None,None];nevals=0
 def met(v):
  nonlocal nevals
  if cache[0] is not None and np.array_equal(v,cache[0]):return cache[1]
  nevals+=1; a=model.metrics(v,pts);cache[:]=[v.copy(),a];return a
 def cons(v):
  a=met(v);return np.r_[v[-1]-a[:,0],a[:,1]-target,a[:,2]-target]
 ts=time.monotonic()
 r=minimize(lambda v:v[-1],x,bounds=bounds,method='SLSQP',constraints=[{'type':'ineq','fun':cons}],options={'maxiter':iterations,'ftol':1e-9})
 a=model.metrics(r.x,201)
 return {'x':r.x.tolist(),'worst_IL_db':float(a[:,0].max()),'H2_db':float(a[:,1].min()),'H3_db':float(a[:,2].min()),'success':bool(r.success),'message':str(r.message),'nfev':r.nfev,'nit':r.nit,'evals':nevals,'elapsed_s':round(time.monotonic()-ts,2),'verified_grid':201,'settings':a.tolist()}

EDGES=tuple((a,b) for a in range(-1,5) for b in range(a+1,5) if b>=0) # node order -1 to 4
# canonical 5 nodes 0..4 and GND=-1, all node pairs
EDGES=tuple((a,b) for a in range(5) for b in range(a+1,5))+tuple((a,-1) for a in range(5))

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['c1','c2','row','c3','pair'],default='c1');p.add_argument('--maxiter',type=int,default=110);p.add_argument('--points',type=int,default=11);p.add_argument('--target',type=float,default=30.025);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=100);p.add_argument('--seed',type=int,default=0)
 args=p.parse_args()
 jobs=[]
 if args.stage in ('c1','c2','c3'):
  ii={'c1':0,'c2':1,'c3':2}[args.stage]
  for e in EDGES:
   if e in FIXED:continue
   f=list(FIXED);f[ii]=e
   jobs.append({'name':f'{args.stage}_to_{e[0]}_{e[1]}','fixed':f,'tune':TUNE,'row':BASE_ROW})
 elif args.stage=='row':
  for row in itertools.permutations(range(4)):
   if tuple(row)==BASE_ROW or row[0]>row[-1]:continue
   jobs.append({'name':'row_'+''.join(map(str,row)),'fixed':FIXED,'tune':TUNE,'row':row})
 else:
  opts1=[(0,1),(1,2),(1,3),(2,4),(0,4),(0,-1),(1,-1),(2,-1)]
  opts2=[(1,4),(1,2),(0,4),(0,-1),(1,-1),(2,-1),(3,-1),(2,4)]
  for e1 in opts1:
   for e2 in opts2:
    if e1==e2 or e1 in FIXED[2:] or e2 in FIXED[2:]:continue
    jobs.append({'name':f'pair_{e1[0]}_{e1[1]}__{e2[0]}_{e2[1]}','fixed':[e1,e2,FIXED[2]],'tune':TUNE,'row':BASE_ROW})
 path=OUT/f'{args.stage}_{args.start}.json';acc=[]
 for i,j in enumerate(jobs[args.start:args.start+args.count],start=args.start):
  m=CircuitModel(j['fixed'],j['tune'],j['row']);x=m.xstart(seed=args.seed)
  try:
   r=optim(m,x,pts=args.points,iterations=args.maxiter,target=args.target)
   rec={**j,'index':i,'stage':args.stage,'target':args.target,'points':args.points,'seed':args.seed,'result':r}
   acc.append(rec);path.write_text(json.dumps(acc,indent=2))
   print('DONE',i,j['name'],'IL',round(r['worst_IL_db'],6),'H',round(min(r['H2_db'],r['H3_db']),4),'time',r['elapsed_s'],flush=True)
  except Exception as ex:
   print('FAIL',i,j['name'],repr(ex),flush=True);acc.append({**j,'index':i,'error':repr(ex)})