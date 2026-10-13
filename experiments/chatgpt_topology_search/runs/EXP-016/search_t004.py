#!/usr/bin/env python3
"""Finite RF-T004 Phase-2 topology screen, independent of repository solvers.
Assumes fixed Q, nominal zero magnetic coupling and fixed chip parts.
Not a comprehensive graph search or physical implementation verification.
"""
import argparse, json, math, time, os
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, expit

CASES=['B71','B12','B28','B13+B14','B26','B8']
# Exact segmentation of the project's data/bands.csv, MHz.
BANDS={
'B71':{'pass':[(663,698),(617,652)],'H2':[(1326,1396)],'H3':[(1989,2094)]},
'B12':{'pass':[(699,716),(729,746)],'H2':[(1398,1432)],'H3':[(2097,2148)]},
'B28':{'pass':[(703,748),(758,803)],'H2':[(1406,1496)],'H3':[(2109,2244)]},
'B13+B14':{'pass':[(777,787),(788,798),(746,756),(758,768)],'H2':[(1554,1574),(1576,1596)],'H3':[(2331,2361),(2364,2394)]},
'B26':{'pass':[(814,849),(859,894)],'H2':[(1628,1698)],'H3':[(2442,2547)]},
'B8':{'pass':[(880,915),(925,960)],'H2':[(1760,1830)],'H3':[(2640,2745)]},
}
# Nodal branch edges (ground -1); fixed series L, GJM shunts and variable C.
TOPOLOGIES={
 'B-elliptic': dict(n=4,L=[(0,1),(1,2),(2,3)], F=[(1,-1),(2,-1)], V=[(0,1),(1,2),(2,3)]),
 'B-shunt-bridge':dict(n=4,L=[(0,1),(1,2),(2,3)],F=[(1,-1),(2,-1)],V=[(0,2),(1,3),(1,-1)]),
 'B-mixed':dict(n=4,L=[(0,1),(1,2),(2,3)],F=[(1,-1),(2,-1)],V=[(0,1),(2,3),(2,-1)]),
 'A-elliptic-trap':dict(n=5,L=[(0,1),(1,2),(2,3),(2,4)],F=[(1,-1),(2,-1),(4,-1)],V=[(0,1),(2,3),(4,-1)]),
 'A-bridge-trap':dict(n=5,L=[(0,1),(1,2),(2,3),(2,4)],F=[(1,-1),(2,-1),(4,-1)],V=[(0,2),(1,3),(4,-1)]),
 'A-trap-at-1':dict(n=5,L=[(0,1),(1,2),(2,3),(1,4)],F=[(1,-1),(2,-1),(4,-1)],V=[(0,1),(2,3),(4,-1)]),
 'A-series4':dict(n=5,L=[(0,1),(1,2),(2,4),(4,3)],F=[(1,-1),(2,-1),(4,-1)],V=[(0,1),(1,2),(4,3)]),
 'A-series4-alt':dict(n=5,L=[(0,1),(1,2),(2,4),(4,3)],F=[(1,-1),(2,-1),(4,-1)],V=[(0,1),(2,4),(4,3)]),
 'A-two-traps':dict(n=5,L=[(0,1),(1,2),(1,3),(2,4)],F=[(1,-1),(3,-1),(4,-1)],V=[(2,-1),(3,-1),(4,-1)]),
 'A-tuned-notch':dict(n=5,L=[(0,1),(1,2),(2,3),(2,4)],F=[(1,-1),(2,-1),(4,-1)],V=[(1,2),(2,3),(4,-1)]),
 'A-bridged-elliptic':dict(n=5,L=[(0,1),(1,2),(2,3),(2,4)],F=[(1,-1),(2,-1),(4,-1)],V=[(0,1),(1,3),(4,-1)]),
 'A-trap-double-bypass':dict(n=5,L=[(0,1),(1,2),(2,3),(2,4)],F=[(1,-1),(2,-1),(4,-1)],V=[(0,1),(1,2),(4,-1)]),
 'C-bridge-L':dict(n=4,L=[(0,1),(1,2),(2,3),(0,2)],F=[(1,-1),(2,-1),(3,-1)],V=[(0,1),(1,2),(2,3)]),
 'C-bridge-L2':dict(n=4,L=[(0,1),(1,2),(2,3),(1,3)],F=[(1,-1),(2,-1),(3,-1)],V=[(0,1),(1,2),(2,3)]),
 'C-dual-path':dict(n=4,L=[(0,1),(1,3),(0,2),(2,3)],F=[(1,-1),(2,-1),(3,-1)],V=[(0,1),(0,2),(1,2)]),
 'C-dual-path-B':dict(n=4,L=[(0,1),(1,3),(0,2),(2,3)],F=[(1,-1),(2,-1),(1,2)],V=[(0,1),(2,3),(1,2)]),
 'C-dual-trap':dict(n=6,L=[(0,1),(1,2),(2,3),(1,4),(2,5)],F=[(1,-1),(4,-1),(5,-1)],V=[(0,1),(4,-1),(5,-1)]),
 'C-4series-trap':dict(n=6,L=[(0,1),(1,2),(2,4),(4,3),(2,5)],F=[(1,-1),(4,-1),(5,-1)],V=[(0,1),(4,3),(5,-1)]),
}
R_SOURCE=50.; Z_LOAD=60-40j
LOAD_Y=1/Z_LOAD
GT_CONST=4*R_SOURCE*LOAD_Y.real
FAC=20/np.log(10)

class Network:
 def __init__(self,name,pts=7):
  self.name=name; self.top=TOPOLOGIES[name];t=self.top;self.n=t['n'];self.nl=len(t['L']);self.nf=len(t['F']);self.nv=len(t['V']);self.nparam=self.nl+self.nf+6*self.nv
  edges=t['L']+t['F']+t['V'];self.edges=edges
  B=np.zeros((self.n,len(edges)))
  for k,(a,b) in enumerate(edges):
   B[a,k]=1
   if b>=0:B[b,k]=-1
  self.B=B
  self.pmat=[];self.casi=[];self.fmhz=[];self.which=[]
  for ic,case in enumerate(CASES):
   for reg in ('pass','H2','H3'):
    for lo,hi in BANDS[case][reg]:
     for f in np.linspace(lo,hi,pts):
      self.fmhz.append(f);self.casi.append(ic);self.which.append(reg)
  self.fmhz=np.array(self.fmhz);self.casi=np.array(self.casi);self.which=np.array(self.which)
  self.passmask=(self.which=='pass');self.stopmask=~self.passmask;self.ws=self.fmhz*2*np.pi*1e6
  self.source=np.zeros(self.n,dtype=complex);self.source[0]=1/R_SOURCE
  self.bounds=[(0.4,27.)]*self.nl+[(0.12,25.)]*self.nf+[(0.,1.5)]*(6*self.nv)
  self._cached_x=None
 def init(self,rng):
  # Basic cutoff pi-type shunts and series stubs; randomized across band settings.
  z=[]
  z+=list(rng.uniform(4,16,size=self.nl))
  if self.n==5: z[-1]=rng.uniform(4,15)
  z+=list(rng.uniform(0.8,6.,size=self.nf))
  if self.n==5: z[-1]=rng.uniform(0.25,2.0)
  for ci,case in enumerate(CASES):
   f2=np.mean(BANDS[case]['H2'][0]);f3=np.mean(BANDS[case]['H3'][0]);
   for j in range(self.nv):
    va=rng.uniform(.05,1.25)
    if self.top['V'][j] in self.top['L']:
     li=self.top['L'].index(self.top['V'][j]);f=f2 if j%2==0 else f3
     va=min(1.49,max(.01, (1/(2*np.pi*f*1e6)**2/(z[li]*1e-9))*1e12))
    z.append(va)
  return np.array(z)
 def calculate(self,x,grad=False,metadata=False):
  x=np.asarray(x); N=len(self.ws)
  # 1 nH => 1e-9H, 1 pF=>1e-12F
  L=x[:self.nl];F=x[self.nl:self.nl+self.nf];V=x[self.nl+self.nf:].reshape(6,self.nv)[self.casi,:]
  q=np.array([25.]*self.nl+[80.]*self.nf+[50.]*self.nv)
  vals=np.column_stack([np.broadcast_to(L,(N,self.nl)),np.broadcast_to(F,(N,self.nf)),V]);factors=np.r_[np.full(self.nl,1e-9),np.full(self.nf+self.nv,1e-12)]
  zz=self.ws[:,None]*vals*factors[None,:]
  y=np.empty_like(zz,dtype=complex)
  y[:,:self.nl]=1/np.maximum(zz[:,:self.nl],1e-15)/(1j+1/q[:self.nl])[None,:]
  y[:,self.nl:]=zz[:,self.nl:]/(1/q[self.nl:]-1j)[None,:]
  Y=np.einsum('fb,ib,jb->fij',y,self.B,self.B,optimize=True)
  Y[:,0,0]+=1/R_SOURCE;Y[:,3,3]+=LOAD_Y
  rhs=np.zeros((N,self.n,2),dtype=complex);rhs[:,0,0]=1/R_SOURCE;rhs[:,3,1]=1
  sol=np.linalg.solve(Y,rhs);v=sol[:,:,0];adj=sol[:,:,1]
  gt=np.maximum(GT_CONST*np.abs(v[:,3])**2,1e-300)
  ildb=-10*np.log10(gt)
  if not (grad or metadata):return ildb
  if grad:
   e1=v@self.B;e2=adj@self.B
   dy=y/np.maximum(vals,1e-12)
   dy[:,:self.nl]*=-1
   # positive sign for negative dVout: dIL = +(20/log(10))*Re(adjoint*voltage*dy/Vout)
   edge_grad=FAC*np.real(e1*e2*dy/v[:,3,None]); J=np.zeros((N,self.nparam))
   J[:,:self.nl+self.nf]=edge_grad[:,:self.nl+self.nf]
   for ci in range(6):
    ii=self.casi==ci;J[ii,self.nl+self.nf+ci*self.nv:self.nl+self.nf+(ci+1)*self.nv]=edge_grad[ii,self.nl+self.nf:]
   if metadata:return ildb,J,v,Y,y
   return ildb,J
  return ildb,v,Y,y
 def objective(self,x,stop_target=30.,s=0.30,weight=1.0):
  il,J=self.calculate(x,True)
  p=il[self.passmask]; t=stop_target-il[self.stopmask]
  # numerical smooth maximum over pass loss + stop violation (smooth hinge), normalized by length
  # stop_max is a stringent all-band metric; penalize if upper bound exceeded.
  softpass=s*logsumexp(p/s)-s*np.log(len(p));wp=np.exp((p-np.max(p))/s);wp/=wp.sum()
  tsm=s*logsumexp(t/s)-s*np.log(len(t));wt=np.exp((t-np.max(t))/s);wt/=wt.sum()
  positive=s*np.logaddexp(0.,tsm/s)
  value=softpass+weight*positive**2
  D=wp@J[self.passmask,:] -2*weight*positive*expit(tsm/s)*(wt@J[self.stopmask,:])
  return float(value),D
 def metrics(self,x,pts=101,independent=False):
  net=self if pts is None else Network(self.name,pts)
  il=net.calculate(x)
  by={}
  for ci,case in enumerate(CASES):
   sel=net.casi==ci
   by[case]=dict(worst_il_db=float(np.max(il[sel & net.passmask])),min_h2_db=float(np.min(il[sel & (net.which=='H2')])),min_h3_db=float(np.min(il[sel & (net.which=='H3')])))
  return dict(worst_il_db=max(z['worst_il_db'] for z in by.values()),min_h2_db=min(z['min_h2_db'] for z in by.values()),min_h3_db=min(z['min_h3_db'] for z in by.values()),per_setting=by,grid_points_per_interval=pts)
 def validate(self,x):
  il,v,Y,ys=self.calculate(x,metadata=True)
  # Independently build full branch-current MNA with ALL two-terminal passive branches, using KCL and KVL.
  # Branch voltages V_a-V_b = Z_branch * I_branch. Capacitor zero C is an open and omitted.
  probes=np.unique(np.linspace(0,len(il)-1,min(21,len(il))).astype(int));max_diff=0.;max_balance=0.;max_power_excess=0.
  B=self.B; 
  for k in probes:
   active=np.abs(ys[k])>1e-20;bb=B[:,active];zz=1/ys[k,active];n=self.n;m=len(zz)
   A=np.zeros((n+m,n+m),complex)
   A[:n,n:]=bb;A[n:,:n]=bb.T;A[n:,n:]=-np.diag(zz)
   A[0,0]=1/R_SOURCE;A[3,3]=LOAD_Y
   r=np.zeros(n+m,complex);r[0]=1/R_SOURCE
   v2=np.linalg.solve(A,r)[:n]
   max_diff=max(max_diff,float(np.max(np.abs(v2-v[k]))))
   branch_power=float(np.sum(np.abs(bb.T@v2)**2*np.real(1/zz)))
   load_power=float(np.abs(v2[3])**2*LOAD_Y.real)
   src_current=(1-v2[0])/R_SOURCE
   source_delivered=float(np.real(src_current)) # 1 Vrms Thevenin source => Re(Vs Is*)
   src_resistor=float(np.abs(src_current)**2*R_SOURCE)
   bal=abs(source_delivered-src_resistor-load_power-branch_power)
   max_balance=max(max_balance,float(bal))
   # Available source power 1/(4*R_SOURCE)
   max_power_excess=max(max_power_excess,max(0,load_power-1/(4*R_SOURCE)))
  return dict(probe_count=len(probes),mna_voltage_max_abs_diff=max_diff,power_balance_max_abs_w=max_balance,passivity_max_excess_w=max_power_excess,nominal_coupling_all_zero=True,spd_eigenmin_nH=float(np.min(x[:self.nl])),chip_area_units=self.nl+2*self.nf/3)

def main():
 pa=argparse.ArgumentParser();pa.add_argument('--names',nargs='+',default=list(TOPOLOGIES));pa.add_argument('--starts',type=int,default=3);pa.add_argument('--iter',type=int,default=85);pa.add_argument('--points',type=int,default=5);pa.add_argument('--dense',type=int,default=101);pa.add_argument('--seed',type=int,default=20261014);pa.add_argument('--out',default='/mnt/data/rft004_screen_results.json');opt=pa.parse_args()
 rng=np.random.default_rng(opt.seed);allres={};t=time.time()
 for name in opt.names:
  net=Network(name,opt.points);runs=[];print('FAMILY',name,'nparameters',net.nparam,'nfrequencies',len(net.ws),flush=True)
  for start in range(opt.starts):
   x=net.init(rng)
   tracks=[]
   for target,weight in [(20.,.035),(27.,.10),(30.,.20),(30.,1.0),(30.,4.0)]:
    r=minimize(lambda x:net.objective(x,target,weight=weight),x,method='L-BFGS-B',jac=True,bounds=net.bounds,options={'maxiter':opt.iter,'ftol':2e-10,'gtol':1e-5,'maxls':15})
    x=r.x
    mm=net.metrics(x,pts=15)
    tracks.append(dict(target_db=target,penalty_weight=weight,success=bool(r.success),nit=int(r.nit),value=float(r.fun),metrics=mm))
   fine=net.metrics(x,pts=opt.dense)
   maxV=max(0,30-min(fine['min_h2_db'],fine['min_h3_db']))
   runs.append(dict(start=start,x=x.tolist(),screen_metrics=fine,converged_last=tracks[-1]['success'],history=tracks,rank=fine['worst_il_db']+6*maxV**2))
   print(' RESULT',start,'IL',round(fine['worst_il_db'],4),'H2',round(fine['min_h2_db'],3),'H3',round(fine['min_h3_db'],3),'success',tracks[-1]['success'],flush=True)
  best=min(runs,key=lambda r:r['rank']);x=np.asarray(best['x']);best['validation']=net.validate(x);best['component_values']={'LQP02HV_nH':x[:net.nl].tolist(),'GJM01_pF':x[net.nl:net.nl+net.nf].tolist(),'IC_C_pF_by_setting':{c:x[net.nl+net.nf+i*net.nv:net.nl+net.nf+(i+1)*net.nv].tolist() for i,c in enumerate(CASES)}}
  allres[name]=dict(topology=net.top,area_units=net.nl+2*net.nf/3,starts=opt.starts,best=best,all_trial_summaries=[dict(start=r['start'],x=r['x'],metrics=r['screen_metrics'],converged_last=r['converged_last']) for r in runs])
  print(' BEST',name,best['screen_metrics']['worst_il_db'],best['screen_metrics']['min_h2_db'],best['screen_metrics']['min_h3_db'],'valid',best['validation'],flush=True)
 header=dict(study='RF-T004 Phase 2 topology screening only',formal_base='RF-F002',seed=opt.seed,starts_per_topology=opt.starts,iteration_budget_per_penalty_stage=opt.iter,grid_points_per_interval_optimization=opt.points,grid_points_per_interval_postcheck=opt.dense,source_ohms=50,load_ohms=[60,-40],Q=dict(LQP02HV=25,GJM01=80,IC_C=50),couplings='all zero (nominal; legal RF-F002 subset)',data_bands='data/bands.csv exact discrete segments copied',elapsed_sec=time.time()-t,results=allres)
 with open(opt.out,'w') as f:json.dump(header,f,indent=2,ensure_ascii=False)
 print('DONE',opt.out,'secs',header['elapsed_sec'],flush=True)
if __name__=='__main__':main()
