#!/usr/bin/env python3
"""EXP-011 genuine compact-part-count LPF analytic-Jacobian local minimax engine.
Phase2: 4 LQP02 Q25, n GJM Q80, n PCB fixed C Q40, three IC C Q80.
No global optimality claims; repeated random starts and deterministic resumable shards.
"""
import argparse,csv,hashlib,json,os,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CASES=('B71','B12','B28','B13+B14','B26','B8')
ALL_EDGES=tuple((a,b) for a in range(1,6) for b in range(a+1,6))+tuple((a,0) for a in range(1,6))

def incidence(edge):
 v=np.zeros(5)
 for n,s in zip(edge,(1,-1)):
  if n>0:v[n-1]+=s
 return v

class Compact:
 def __init__(self,d,bands,points=31,gjm_edges=None,pcb_edges=None,var_edges=None,inductor_edges=None):
  top=d['topology'];self.points=points;self.bands=bands
  self.L_edges=tuple(map(tuple,inductor_edges if inductor_edges is not None else [x['nodes'] for x in top['inductors']]))
  self.gjm_edges=tuple(map(tuple,gjm_edges if gjm_edges is not None else [x['nodes'] for x in top['fixed_capacitors']]))
  self.pcb_edges=tuple(map(tuple,pcb_edges if pcb_edges is not None else [x['nodes'] for x in top['pcb_pattern_capacitors']]))
  self.var_edges=tuple(map(tuple,var_edges if var_edges is not None else [x['nodes'] for x in top['variable_capacitors']]))
  self.row=tuple(int(x[1:]) for x in top['physical_chip_row'])
  self.nf=len(self.gjm_edges);self.npcb=len(self.pcb_edges);self.ncap=self.nf+self.npcb
  self.n=4+self.ncap+3+18+1;self.kstart=4+self.ncap;self.vstart=self.kstart+3
  self.B=np.stack([incidence(e) for e in self.L_edges],axis=1)
  self.VC=np.stack([incidence(e) for e in self.gjm_edges+self.pcb_edges+self.var_edges])
  self.outer=self.VC[:,:,None]*self.VC[:,None,:]
  self.Q=np.array([80]*self.nf+[40]*self.npcb+[80]*3)
  self.Qfactor=1/(1/self.Q-1j)
  self.port=np.zeros((5,5),complex);self.port[0,0]=1/50;self.port[2,2]=1/(60-40j)
  self.src=np.array([1/50,0,0,0,0],complex);self.eout=np.array([0,0,1,0,0],complex)
  self.bounds=([(np.log(.4),np.log(56))]*4+[(np.log(.1),np.log(100))]*self.nf+
               [(np.log(.02),np.log(.2))]*self.npcb+[(-.4,.4)]*3+[(0,4)]*18+[(0,1.5)])
  self.cache=None;self.evaluations=0
  self._build_grid()
 def _build_grid(self):
  obs=[]
  for casei,case in enumerate(CASES):
   for rg in ('UL','DL','H2','H3'):
    for r in self.bands:
     if r['case']==case and r['region']==rg:
      for f in np.linspace(float(r['low_mhz']),float(r['high_mhz']),self.points):obs.append((casei,rg,float(f)))
  self.case=np.array([v[0] for v in obs],int)
  self.passband=np.array([v[1] in ('UL','DL') for v in obs],bool)
  self.omega=np.array([v[2] for v in obs])*2*np.pi*1e6
 def ref_x(self,d):
  top=d['topology'];fromd=dict((tuple(z['nodes']),z['C_pF']) for z in top['fixed_capacitors']+top['pcb_pattern_capacitors'])
  C=[fromd.get(edge, .1000001 if i<self.nf else .0200001) for i,edge in enumerate(self.gjm_edges+self.pcb_edges)]
  ref=np.r_[np.log([z['L_nH'] for z in top['inductors']]),np.log(C),top['signed_adjacent_k'],
       np.array([d['variable_C_pf_by_setting'][s] for s in CASES]).ravel(),.30]
  assert len(ref)==self.n
  return np.clip(ref,np.array(self.bounds)[:,0]+1e-10,np.array(self.bounds)[:,1]-1e-10)
 def network(self,x):
  L=np.exp(x[:4])*1e-9
  K=np.eye(4);M=np.diag(L.astype(complex))
  for j,k in enumerate(x[self.kstart:self.vstart]):
   a,b=self.row[j:j+2];M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b]);K[a,b]=K[b,a]=k
  if np.linalg.eigvalsh(K).min()<1e-5:raise ValueError('non-SPD')
  Z=np.diag(L/25)+1j*M;Zi=np.linalg.inv(Z)
  coil=self.B@Zi@self.B.T
  Cfix=np.exp(x[4:self.kstart])*1e-12
  Cv=x[self.vstart:-1].reshape(6,3)*1e-12
  return L,M,Z,Zi,coil,Cfix,Cv
 def _eval(self,x):
  if self.cache is not None and np.array_equal(self.cache[0],x):return self.cache[1:]
  self.evaluations+=1
  L,M,Z,Zi,coil,Cfix,Cv=self.network(x)
  cap=np.concatenate([np.broadcast_to(Cfix,(len(self.omega),self.ncap)),Cv[self.case]],axis=1)
  Ycap=np.einsum('ni,i,ijk->njk',cap,self.Qfactor,self.outer)
  omega=self.omega
  Y=self.port[None,:,:]+coil[None,:,:]/omega[:,None,None]+omega[:,None,None]*Ycap
  V=np.linalg.solve(Y,np.broadcast_to(self.src,(len(Y),5))[...,None])[...,0]
  W=np.linalg.solve(Y.transpose(0,2,1),np.broadcast_to(self.eout,(len(Y),5))[...,None])[...,0]
  out=V[:,2]
  ildb=-10*np.log10(np.maximum(200*60/5200*abs(out)**2,1e-300))
  mul=(20/np.log(10))/np.where(np.abs(out)>1e-200,out,1e-200+0j)
  jac=np.zeros((len(Y),self.n))
  R=W@self.B@Zi;D=V@self.B@Zi
  neighbors=[self.row[i:i+2] for i in range(3)]
  for i in range(4):
   z=(L[i]/25+1j*L[i])*R[:,i]*D[:,i]
   for a,b in neighbors:
    if i==a or i==b:
     z+=.5j*M[a,b]*(R[:,a]*D[:,b]+R[:,b]*D[:,a])
   jac[:,i]=np.real(-mul*z/omega)
  E=W@self.VC.T;F=V@self.VC.T
  dc=mul[:,None]*omega[:,None]*E*F*self.Qfactor[None,:]*1e-12
  for i in range(self.ncap):jac[:,4+i]=np.real(dc[:,i]*np.exp(x[4+i]))
  for i,(a,b) in enumerate(neighbors):
   z=1j*np.sqrt(L[a]*L[b])*(R[:,a]*D[:,b]+R[:,b]*D[:,a])
   jac[:,self.kstart+i]=np.real(-mul*z/omega)
  for ci in range(6):
   idx=np.flatnonzero(self.case==ci)
   jac[idx,self.vstart+3*ci:self.vstart+3*ci+3]=np.real(dc[idx,self.ncap:])
  self.cache=(x.copy(),ildb,jac)
  return ildb,jac
 def constraints(self,x,target):
  il,jac=self._eval(x)
  return np.where(self.passband,x[-1]-il,il-target)
 def constraints_jac(self,x):
  il,jac=self._eval(x);c=jac.copy();c[self.passband,:]*=-1;c[self.passband,-1]=1;return c
 def grid_metrics(self,x,n=201):
  L,M,Z,Zi,coil,Cfix,Cv=self.network(x);out=np.empty((6,3))
  for ci,case in enumerate(CASES):
   C=np.r_[Cfix,Cv[ci]];Cmat=np.einsum('i,i,ijk->jk',C,self.Qfactor,self.outer)
   for typ,regs in enumerate((('UL','DL'),('H2',),('H3',))):
    ws=np.concatenate([np.linspace(float(b['low_mhz']),float(b['high_mhz']),n)*2*np.pi*1e6 for b in self.bands if b['case']==case and b['region'] in regs])
    A=self.port[None,:,:]+coil[None,:,:]/ws[:,None,None]+ws[:,None,None]*Cmat[None,:,:]
    v=np.linalg.solve(A,np.broadcast_to(self.src,(len(ws),5))[...,None])[...,0]
    db=-10*np.log10(np.maximum(200*60/5200*abs(v[:,2])**2,1e-300))
    out[ci,typ]=db.max() if typ==0 else db.min()
  return out
 def optimize(self,x,target=30.0001,maxiter=200):
  t=time.monotonic();self.evaluations=0;self.cache=None
  r=minimize(lambda x:x[-1],x,method='SLSQP',jac=lambda x:np.r_[np.zeros(self.n-1),1.],bounds=self.bounds,
    constraints=[{'type':'ineq','fun':lambda a:self.constraints(a,target),'jac':self.constraints_jac}],
    options={'maxiter':maxiter,'ftol':1e-10})
  m=self.grid_metrics(r.x,201)
  return {'x':r.x.tolist(),'IL201':float(m[:,0].max()),'H2min201':float(m[:,1].min()),'H3min201':float(m[:,2].min()),'settings201':m.tolist(),
    'iterations':int(r.nit),'evaluations':self.evaluations,'time_seconds':float(time.monotonic()-t),'converged':bool(r.success),'termination':str(r.message),
    'partial_frequency_grid_points_per_interval':self.points,'constraint_target_db':target,'global_bound_proved':False}

def jobs(family,d):
 top=d['topology'];f=[tuple(z['nodes']) for z in top['fixed_capacitors']]
 pcb=[tuple(z['nodes']) for z in top['pcb_pattern_capacitors']];var=[tuple(z['nodes']) for z in top['variable_capacitors']]
 if family=='baseline':return [dict(gjm_edges=f,pcb_edges=pcb,var_edges=var)]
 if family=='ind_edges':
  edges=[tuple(z['nodes']) for z in top['inductors']]
  return [dict(gjm_edges=f,pcb_edges=pcb,var_edges=var,inductor_edges=edges[:i]+[e]+edges[i+1:]) for i in range(4) for e in ALL_EDGES if e!=edges[i]]
 if family=='fixed_gjm':return [dict(gjm_edges=[e],pcb_edges=pcb,var_edges=var) for e in ALL_EDGES]
 if family=='var3':return [dict(gjm_edges=f,pcb_edges=pcb,var_edges=var[:2]+[e]) for e in ALL_EDGES if 0 not in e and e!=var[2]]
 if family=='pcb1':return [dict(gjm_edges=f,pcb_edges=[e],var_edges=var) for e in ALL_EDGES]
 if family=='gjm2':return [dict(gjm_edges=f+[e],pcb_edges=pcb,var_edges=var) for e in ALL_EDGES if e not in f]
 raise ValueError('unknown family')

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',default=str(HERE/'EXP011-01.json'));p.add_argument('--family',choices=['baseline','fixed_gjm','var3','pcb1','gjm2','ind_edges'],default='baseline');p.add_argument('--starts',type=int,default=2);p.add_argument('--max-new-jobs',type=int,default=4);p.add_argument('--shards',type=int,default=1);p.add_argument('--shard-index',type=int,default=0);p.add_argument('--points',type=int,default=31);p.add_argument('--iterations',type=int,default=160);p.add_argument('--rejection',type=float,default=30.001);p.add_argument('--seed',type=int,default=20261012);p.add_argument('--checkpoint',default='');p.add_argument('--check-jac',action='store_true');a=p.parse_args()
 d=json.loads(Path(a.candidate).read_text());BANDS=list(csv.DictReader((ROOT/'data/bands.csv').open()))
 refmodel=Compact(d,BANDS,points=a.points);ref=refmodel.ref_x(d)
 if a.check_jac:
  z,j=refmodel._eval(ref)
  tests=[]
  for i in range(len(ref)-1):
   y=ref.copy();zv=ref.copy();y[i]+=1e-6;zv[i]-=1e-6
   approx=(refmodel._eval(y)[0]-refmodel._eval(zv)[0])/2e-6
   tests.append(float(np.max(abs(j[:,i]-approx))/max(1,float(np.max(abs(approx))))))
  print('max_relative_gradient_error',max(tests));assert max(tests)<1e-4;return
 jbs=jobs(a.family,d);assert 1<=a.starts<=100 and 0<=a.shard_index<a.shards
 settings={k:v for k,v in vars(a).items() if k not in ('checkpoint','max_new_jobs')}
 fingerprint=hashlib.sha256(Path(__file__).read_bytes()+Path(a.candidate).read_bytes()+(ROOT/'data/bands.csv').read_bytes()+json.dumps(settings,sort_keys=True).encode()).hexdigest()
 out=Path(a.checkpoint) if a.checkpoint else None
 state={'fingerprint':fingerprint,'settings':settings,'total_jobs':len(jbs),'completed':[],'records':[],'failures':[], 'unfinished':True,'commit_sha':os.getenv('GITHUB_SHA','not-provided')}
 if out and out.exists():
  old=json.loads(out.read_text());assert old['fingerprint']==fingerprint,'Resume version mismatch';state=old
 count=0
 for idx,job in enumerate(jbs):
  if idx%a.shards!=a.shard_index or idx in state['completed']:continue
  if count>=a.max_new_jobs:break
  mod=Compact(d,BANDS,points=a.points,**job)
  for si in range(a.starts):
   seed=a.seed+1021*idx+si*1033;rng=np.random.default_rng(seed)
   x=mod.ref_x(d)
   if si:
    sd=.035+si*.035
    x[:4]+=rng.normal(0,sd,4);x[4:mod.kstart]+=rng.normal(0,sd,mod.ncap)
    x[mod.kstart:mod.vstart]+=rng.normal(0,min(.035,sd/3),3)
    x[mod.vstart:-1]+=rng.normal(0,sd/3,18)
   x=np.clip(x,np.array(mod.bounds)[:,0]+1e-9,np.array(mod.bounds)[:,1]-1e-9)
   try:state['records'].append({'job_index':idx,'job':job,'seed':seed,'run':mod.optimize(x,a.rejection,a.iterations)})
   except Exception as e:state['failures'].append({'job_index':idx,'seed':seed,'error':repr(e)})
  state['completed'].append(idx);count+=1
  state['unfinished']=len([i for i in range(len(jbs)) if i%a.shards==a.shard_index and i not in state['completed']])>0
  if out:
   out.parent.mkdir(parents=True,exist_ok=True);t=out.with_suffix('.tmp');t.write_text(json.dumps(state,indent=2)+'\n');t.replace(out)
  accepted=[z['run']['IL201'] for z in state['records'] if min(z['run']['H2min201'],z['run']['H3min201'])>=a.rejection-1e-8]
  print('job',idx,'completed',len(state['completed']),'best_201grid',min(accepted,default=None),'errors',len(state['failures']),flush=True)
 print('assigned completed',len(state['completed']),'out of',len([i for i in range(len(jbs)) if i%a.shards==a.shard_index]),'unfinished',state['unfinished'])
if __name__=='__main__':main()