#!/usr/bin/env python3
"""Phase-2 EXP-009 exploratory 2/3 variable-C placement and 3 fixed-C rewires.
Finite-grid SLSQP multi-start, resumable by deterministic job ID; NOT a global bound.
Reference policy stays unchanged. No Phase-3 switched-cap modeling.
"""
import argparse,csv,hashlib,json,os,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[4]
CAND=ROOT/'experiments/chatgpt_topology_search/runs/EXP-008/C6-02.json'
BANDS=ROOT/'data/bands.csv'
POLICY=ROOT/'data/design_constraints.json'
CASES=('B71','B12','B28','B13+B14','B26','B8')
ROW=(1,2,3,0)
LINDS=((0,1),(2,3),(1,4),(1,2))
BASE_FIXED=((0,2),(4,-1),(0,1))
BASE_TUNE=((3,-1),(4,-1),(1,2))
E_OPTIONS={
 'L0':(0,1),'L1':(2,3),'L2':(1,4),'L3':(1,2),
 'bridge_input_out':(0,2),'bridge_input_n5':(0,4),'bridge_out_n5':(2,4),
 'shunt_n2':(1,-1),'shunt_out':(2,-1),'shunt_input':(0,-1),
 'shunt_n4':(3,-1),'shunt_n5':(4,-1),
}
FIXED_OPTIONS=(
 ((1,2),(2,3),(0,4),(1,4),(1,-1),(2,-1),(0,-1),(3,-1),(4,-1),(2,4)),
 ((1,-1),(2,-1),(3,-1),(0,-1),(2,4),(1,4),(2,3),(1,2)),
 ((1,2),(2,3),(1,4),(0,4),(2,4),(1,-1),(2,-1),(0,-1)),
)

def jobs():
 jobs=[]
 def add(label,kind,cs=BASE_FIXED,tunes=BASE_TUNE):
  jobs.append({'id':len(jobs),'name':label,'kind':kind,
               'fixed_edges':list(cs),'variable_edges':list(tunes)})
 add('baseline_C6_02','baseline')
 for key,edge in E_OPTIONS.items():
  if edge not in BASE_TUNE[0:2] and edge!=BASE_TUNE[2]:
   add('variable_Cv2_to_'+key,'variable_moved',tunes=BASE_TUNE[:2]+(edge,))
 for label,subset in [('ground_ground',(0,1)),('ground_L3',(0,2)),('otherground_L3',(1,2))]:
  add('two_tunable_'+label,'two_variable',tunes=tuple(BASE_TUNE[i] for i in subset))
 for i,choices in enumerate(FIXED_OPTIONS):
  for edge in choices:
   if edge in BASE_FIXED:continue
   new=list(BASE_FIXED);new[i]=edge
   add('fixed_C%d_to_%s_%s'%(i,*edge),'fixed_moved',cs=tuple(new))
 return jobs

def outer(edge):
 vec=np.zeros(5)
 for n,s in zip(edge,(1,-1)):
  if n>=0:vec[n]+=s
 return np.outer(vec,vec)

class Model:
 def __init__(self,job,bands):
  self.job=job;self.nvar=len(job['variable_edges'])
  self.B=np.zeros((5,4))
  for i,(a,b) in enumerate(LINDS):self.B[a,i]+=1;self.B[b,i]-=1
  self.Dfix=np.array([outer(e) for e in job['fixed_edges']])
  self.Dvar=np.array([outer(e) for e in job['variable_edges']])
  self.ports=np.zeros((5,5),complex);self.ports[0,0]=1/50;self.ports[2,2]=1/(60-40j)
  self.src=np.array([1/50,0,0,0,0],complex)
  self.bands=bands;self.grids={}
 def grids_for(self,n):
  if n not in self.grids:
   self.grids[n]=[[np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),n)*2*np.pi*1e6
     for r in self.bands if r['case']==case and r['region'] in regions])
     for regions in (('UL','DL'),('H2',),('H3',))] for case in CASES]
  return self.grids[n]
 def metrics(self,x,n):
  l=np.exp(x[:4])*1e-9;c=np.exp(x[4:7])*1e-12;k=x[7:10]
  tc=x[10:-1].reshape(6,self.nvar)*1e-12
  K=np.eye(4);M=np.diag(l.astype(complex))
  for i,ki in enumerate(k):
   a,b=ROW[i:i+2];K[a,b]=K[b,a]=ki;M[a,b]=M[b,a]=ki*np.sqrt(l[a]*l[b])
  if np.linalg.eigvalsh(K).min()<=1e-5:return np.full((6,3),1e3)
  coil=self.B@np.linalg.solve(np.diag(l/25)+1j*M,self.B.T)
  cyfix=np.einsum('a,abc->bc',c/(1/80-1j),self.Dfix)
  cyvar=np.einsum('sa,abc->sbc',tc/(1/80-1j),self.Dvar)
  out=np.empty((6,3))
  for i,segments in enumerate(self.grids_for(n)):
   Ycap=cyfix+cyvar[i]
   for j,w in enumerate(segments):
    Y=self.ports[None,:,:]+coil[None,:,:]/w[:,None,None]+w[:,None,None]*Ycap[None,:,:]
    v=np.linalg.solve(Y,np.broadcast_to(self.src,(len(w),5))[...,None])[...,0]
    att=-10*np.log10(np.maximum(200*60/5200*np.abs(v[:,2])**2,1e-300))
    out[i,j]=att.max() if j==0 else att.min()
  return out
 def bounds(self):
  return [(np.log(.4),np.log(27))]*4+[(np.log(.1),np.log(100))]*3+[(-.4,.4)]*3+[(0,4)]*(6*self.nvar)+[(0,2)]
 def initial(self,ref,seed,perturb=.04):
  rng=np.random.default_rng(seed)
  l=np.array(ref['L_nH']);c=np.array(ref['fixed_C_pf']);k=np.array(ref['neighbor_k'])
  base=np.array([ref['variable_C_pf_by_setting'][key] for key in CASES])
  t=np.empty((6,self.nvar))
  for j,edge in enumerate(self.job['variable_edges']):
   t[:,j]=base[:,BASE_TUNE.index(tuple(edge))] if tuple(edge) in BASE_TUNE else np.maximum(.05,base[:,2]*.8)
  l*=np.exp(rng.normal(0,perturb,4));c*=np.exp(rng.normal(0,perturb,3))
  k+=rng.normal(0,.05*bool(perturb),3);t+=rng.normal(0,perturb,(6,self.nvar))
  x=np.r_[np.log(l),np.log(c),k,t.ravel(),.55]
  return np.clip(x,[a for a,b in self.bounds()],[b for a,b in self.bounds()])

def optimize(model,reference,seed,points,verify,maxiter,atten,perturb):
 x0=model.initial(reference,seed,perturb)
 cache=[None,None];evals=[0];begin=time.monotonic()
 def metrics(x):
  if cache[0] is None or not np.array_equal(x,cache[0]):
   cache[0]=x.copy();cache[1]=model.metrics(x,points);evals[0]+=1
  return cache[1]
 def constraints(x):
  met=metrics(x);return np.r_[x[-1]-met[:,0],met[:,1]-atten,met[:,2]-atten]
 opt=minimize(lambda v:v[-1],x0,method='SLSQP',bounds=model.bounds(),
              constraints=[{'type':'ineq','fun':constraints}],
              options={'maxiter':maxiter,'ftol':1e-9})
 metrics_verified=model.metrics(opt.x,verify)
 return {'seed':seed,'iterations':int(opt.nit),'nfev':int(opt.nfev),'model_evals':evals[0],
         'seconds':round(time.monotonic()-begin,3),'converged':bool(opt.success),
         'message':str(opt.message),'x':opt.x.tolist(),
         'max_IL_db':float(metrics_verified[:,0].max()),
         'min_H2_db':float(metrics_verified[:,1].min()),
         'min_H3_db':float(metrics_verified[:,2].min()),
         'setting_metrics':metrics_verified.tolist(),
         'valid_30dB_on_verification_grid':bool(metrics_verified[:,1:].min()>=30.0),
         'meets_optimization_target_on_grid':bool(metrics_verified[:,1:].min()>=atten),
         'independent_MNA_verified':False,'globally_optimal':False}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--reference-only',action='store_true');p.add_argument('--shard-count',type=int,default=1)
 p.add_argument('--shard-index',type=int,default=0);p.add_argument('--max-new-jobs',type=int,default=2)
 p.add_argument('--starts',type=int,default=1);p.add_argument('--maxiter',type=int,default=120)
 p.add_argument('--points',type=int,default=13);p.add_argument('--verify-points',type=int,default=201)
 p.add_argument('--atten',type=float,default=30.045);p.add_argument('--seed',type=int,default=20261012)
 p.add_argument('--checkpoint',type=Path);args=p.parse_args()
 assert args.shard_count>=1 and 0<=args.shard_index<args.shard_count
 assert 1<=args.starts<=20 and args.points>=3 and args.verify_points>=3
 assert 30<=args.atten<=35 and args.maxiter>=1 and args.max_new_jobs>=1
 ref=json.loads(CAND.read_text());bands=list(csv.DictReader(BANDS.open(newline='')))
 joblist=jobs();b=Model(joblist[0],bands);x=np.r_[np.log(ref['L_nH']),np.log(ref['fixed_C_pf']),ref['neighbor_k'],
   np.array([ref['variable_C_pf_by_setting'][case] for case in CASES]).ravel(),.4]
 measured=b.metrics(x,201)
 assert abs(measured[:,0].max()-ref['verification']['worst_IL_db'])<1e-5
 assert abs(measured[:,1].min()-ref['verification']['min_H2_db'])<1e-5
 assert abs(measured[:,2].min()-ref['verification']['min_H3_db'])<1e-5
 print('reference C6-02 reproduced; jobs=',len(joblist),'worstIL=',measured[:,0].max(),flush=True)
 if args.reference_only:return
 fingerprint=hashlib.sha256((CAND.read_bytes()+BANDS.read_bytes()+
    (POLICY.read_bytes() if POLICY else b'')+Path(__file__).read_bytes()+
    json.dumps({'shards':args.shard_count,'starts':args.starts,'iterations':args.maxiter,
         'points':args.points,'verify':args.verify_points,'atten':args.atten,'seed':args.seed},sort_keys=True).encode())).hexdigest()
 assigned=[j for j in joblist if j['id']%args.shard_count==args.shard_index]
 state={'fingerprint':fingerprint,'commit':os.environ.get('GITHUB_SHA','local'),
        'shard_index':args.shard_index,'shard_count':args.shard_count,'assigned_count':len(assigned),
        'completed_ids':[],'failures':[],'runs':[],'unfinished':True}
 if args.checkpoint and args.checkpoint.exists():
  existing=json.loads(args.checkpoint.read_text())
  if existing['fingerprint']!=fingerprint:raise RuntimeError('Checkpoint fingerprint mismatch')
  state=existing
 start=time.monotonic();nnew=0
 for j in assigned:
  if j['id'] in state['completed_ids']:continue
  if nnew>=args.max_new_jobs:break
  for s in range(args.starts):
   sd=args.seed+10000*j['id']+s
   try:
    m=Model(j,bands)
    res=optimize(m,ref,sd,args.points,args.verify_points,args.maxiter,args.atten,0 if s==0 and j['id']==0 else .04 if s==0 else .12)
    state['runs'].append({'job':j,**res})
   except Exception as ex:
    state['failures'].append({'job_id':j['id'],'seed':sd,'error':repr(ex)})
  state['completed_ids'].append(j['id']);nnew+=1
  state['unfinished']=len(state['completed_ids'])<len(assigned)
  state['run_seconds']=round(time.monotonic()-start,2)
  if args.checkpoint:
   args.checkpoint.parent.mkdir(parents=True,exist_ok=True)
   temp=args.checkpoint.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(args.checkpoint)
  print('checkpoint',j['id'],j['name'],'completed',len(state['completed_ids']),len(assigned),flush=True)
 print('shard done. successful verified 30dB',sum(z['valid_30dB_on_verification_grid'] for z in state['runs']),
       'of',len(state['runs']),'runs; failed',len(state['failures']),'unfinished',state['unfinished'])

if __name__=='__main__':main()