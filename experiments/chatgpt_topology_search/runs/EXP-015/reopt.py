#!/usr/bin/env python3
"""Phase2 HV/HQ Q-aware 5-node 4-coupled-L RF filter optimizer.

This script is a standalone local version. Band specifications from /mnt/data/bands.csv.
"""
import json,csv,time,sys,os
from pathlib import Path
import numpy as np
from scipy.optimize import minimize, minimize_scalar
HERE=Path(__file__).resolve().parent
ROOT=next((candidate for candidate in (HERE, *HERE.parents) if (candidate/'data'/'bands.csv').exists()), Path('/mnt/data'))
CASES=['B71','B12','B28','B13+B14','B26','B8']
BANDS=list(csv.DictReader(((ROOT/'data'/'bands.csv') if (ROOT/'data'/'bands.csv').exists() else (ROOT/'bands.csv')).open()))
OLD={
'EXP011-01':{'name':'EXP011-01','L':[3.4084616011657642,55.99999999977252,8.04453326111069,4.853728404004065],
'row':[1,2,3,0],'k':[.012921955677951433,-.3731669847779207,.4],
'Cfix':[.780468567289133],'fixed_edges':[(1,2)],'pcb_edges':[],
'cv_edges':[(4,0),(5,0),(2,3)],'cv':[[.2655710118970864,1.4905637169005168,.926012967688509],[.23319316276592664,1.4447089109110012,.7909183255681816],[.23985905343565994,1.325692834408903,.6926177929900169],[.17773375234919175,1.2653835161596694,.47218527998014626],[.15563317025942675,1.1786053852732299,.3056833282662742],[.12656459961354002,1.0422793219599482,0]],'reference_IL':.29382173854790583},
'EXP014-02':{'name':'EXP014-02','L':[2.9685359214168363,28.560459616737962,8.662280852957775,5.463426805677166],
'row':[0,1,2,3],'k':[.05231714461325296,-.05159077668427475,-.17001336465204447],
'Cfix':[1.8340100708728058,.8916404466790553,.06357785580353646],
'fixed_edges':[(1,2),(5,0)],'pcb_edges':[(3,1)],
'cv_edges':[(4,0),(2,3)],
'cv':[[.4474724439039603,2.0420047424389107],[.4426163821268361,1.5860599759288996],[.3742595617799691,1.7486539780767993],[.32056593191995164,1.1142518301627],[.2210719671534659,.8603755494141523],[.1666120287805868,.6584794674876233]],'reference_IL':.3431899534191963}}


def yC(q): return 1/(1/q-1j)
def incidence(edges):
 b=np.zeros((len(edges),5))
 for i,(a,c) in enumerate(edges):
  if a:b[i,a-1]+=1
  if c:b[i,c-1]-=1
 return b

class Network:
 def __init__(self,ref,series,grid=7):
  self.ref=ref;self.series=list(series);self.q=np.array([25 if s=='HV' else 20 for s in series],float)
  self.row=ref['row'];self.B=incidence([(1,2),(3,4),(2,5),(2,3)]).T
  self.Cedges=ref['fixed_edges']+ref['pcb_edges']+ref['cv_edges'];self.VC=incidence(self.Cedges)
  self.outer=self.VC[:,:,None]*self.VC[:,None,:]
  self.Q=np.array([80]*len(ref['fixed_edges'])+[40]*len(ref['pcb_edges'])+[80]*len(ref['cv_edges']))
  self.Qf=np.array([yC(q) for q in self.Q]);self.nf=len(ref['fixed_edges'])+len(ref['pcb_edges']);self.ncv=len(ref['cv_edges']);self.nc=len(self.Cedges)
  self.kstart=4+self.nf;self.vstart=self.kstart+3;self.n=self.vstart+6*self.ncv+1
  self.port=np.zeros((5,5),complex);self.port[0,0]=1/50;self.port[2,2]=1/(60-40j)
  self.src=np.array([1/50,0,0,0,0],complex);self.eout=np.array([0,0,1,0,0],complex)
  self.il_grid=[];self.gridtyp=[];self.casi=[]
  for i,case in enumerate(CASES):
   for r in BANDS:
    if r['case']!=case: continue
    for f in np.linspace(float(r['low_mhz']),float(r['high_mhz']),grid):
     self.il_grid.append(f);self.gridtyp.append(r['region'] in ('UL','DL'));self.casi.append(i)
  self.ws=np.array(self.il_grid)*2*np.pi*1e6;self.passband=np.array(self.gridtyp,bool);self.casi=np.array(self.casi,int)
  self.bounds=[]
  for s in series:self.bounds.append((np.log(.4),np.log(27 if s=='HV' else 56)))
  for i in range(self.nf):self.bounds.append((np.log(.1 if i<len(ref['fixed_edges']) else .02),np.log(100 if i<len(ref['fixed_edges']) else .2)))
  self.bounds += [(-.4,.4)]*3+[(0,4)]*(6*self.ncv)+[(0,1.2)]
  self.lo=np.array([a for a,b in self.bounds]);self.hi=np.array([b for a,b in self.bounds]);self.cache=None;self.evals=0
 def init(self,random=None):
  d=self.ref;x=np.r_[np.log(d['L']),np.log(d['Cfix']),d['k'],np.array(d['cv']).ravel(),max(.3,d['reference_IL'])]
  if random is not None:
   rng=np.random.default_rng(random)
   x[:4]+=rng.normal(0,.045,4);x[4:self.kstart]+=rng.normal(0,.04,self.nf)
   x[self.kstart:self.vstart]+=rng.normal(0,.015,3);x[self.vstart:-1]+=rng.normal(0,.04,6*self.ncv)
  return np.maximum(self.lo+1e-9,np.minimum(self.hi-1e-9,x))
 def build(self,x):
  L=np.exp(x[:4])*1e-9;K=np.eye(4);M=np.diag(L.astype(complex))
  for i,k in enumerate(x[self.kstart:self.vstart]):
   a,b=self.row[i:i+2];M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b]);K[a,b]=K[b,a]=k
  if np.linalg.eigvalsh(K).min()<1e-5: raise ValueError('nonSPD')
  Z=np.diag(L/self.q)+1j*M;Zi=np.linalg.inv(Z);coil=self.B@Zi@self.B.T
  cfix=np.exp(x[4:self.kstart])*1e-12
  cv=x[self.vstart:-1].reshape(6,self.ncv)*1e-12
  return L,M,Z,Zi,coil,cfix,cv,K
 def calc(self,x):
  if self.cache is not None and np.array_equal(self.cache[0],x):return self.cache[1:]
  self.evals+=1
  L,M,Z,Zi,coil,CF,Cv,K=self.build(x)
  C=np.concatenate([np.broadcast_to(CF,(len(self.ws),self.nf)),Cv[self.casi]],axis=1)
  Yc=np.einsum('ni,i,ijk->njk',C,self.Qf,self.outer)
  A=self.port[None,:,:]+coil[None,:,:]/self.ws[:,None,None]+self.ws[:,None,None]*Yc
  V=np.linalg.solve(A,np.broadcast_to(self.src,(len(self.ws),5))[...,None])[...,0]
  W=np.linalg.solve(A.transpose(0,2,1),np.broadcast_to(self.eout,(len(self.ws),5))[...,None])[...,0]
  out=V[:,2];ildb=-10*np.log10(np.maximum(200*60/5200*np.abs(out)**2,1e-300))
  mul=(20/np.log(10))/np.where(np.abs(out)>1e-200,out,1e-200+0j)
  jac=np.zeros((len(self.ws),self.n))
  R=W@self.B@Zi;D=V@self.B@Zi
  neighbors=[self.row[i:i+2] for i in range(3)]
  for i in range(4):
   z=(L[i]/self.q[i]+1j*L[i])*R[:,i]*D[:,i]
   for a,b in neighbors:
    if i==a or i==b:z+=.5j*M[a,b]*(R[:,a]*D[:,b]+R[:,b]*D[:,a])
   jac[:,i]=np.real(-mul*z/self.ws)
  E=W@self.VC.T;F=V@self.VC.T
  dc=mul[:,None]*self.ws[:,None]*E*F*self.Qf[None,:]*1e-12
  for i in range(self.nf):jac[:,4+i]=np.real(dc[:,i]*np.exp(x[4+i]))
  for i,(a,b) in enumerate(neighbors):
   z=1j*np.sqrt(L[a]*L[b])*(R[:,a]*D[:,b]+R[:,b]*D[:,a])
   jac[:,self.kstart+i]=np.real(-mul*z/self.ws)
  for ci in range(6):
   idx=np.flatnonzero(self.casi==ci)
   jac[idx,self.vstart+ci*self.ncv:self.vstart+(ci+1)*self.ncv]=np.real(dc[idx,self.nf:])
  self.cache=(x.copy(),ildb,jac);return ildb,jac
 def cons(self,x,target):
  il,j=self.calc(x);return np.where(self.passband,x[-1]-il,il-target)
 def consjac(self,x):
  il,j=self.calc(x);a=j.copy();a[self.passband,:]*=-1;a[self.passband,-1]=1;return a
 def optimize(self,x,target=30.002,maxiter=140):
  self.evals=0;self.cache=None;t=time.time()
  r=minimize(lambda a:a[-1],x,jac=lambda a:np.r_[np.zeros(len(a)-1),1.],method='SLSQP',bounds=self.bounds,
   constraints=[{'type':'ineq','fun':lambda a:self.cons(a,target),'jac':self.consjac}],options={'maxiter':maxiter,'ftol':2e-9})
  m=self.metrics(r.x,31)
  return {'x':r.x.tolist(),'IL':float(np.max(m[:,0])),'H2':float(np.min(m[:,1])),'H3':float(np.min(m[:,2])),
  'by_setting':m.tolist(),'success':bool(r.success),'termination':str(r.message),'iterations':int(r.nit),'evals':self.evals,'secs':round(time.time()-t,3),'target':target}
 def metrics(self,x,pts=301):
  L,M,Z,Zi,coil,CF,Cv,K=self.build(x)
  y=np.empty((6,3));
  for ci,case in enumerate(CASES):
   allC=np.r_[CF,Cv[ci]]
   Ycap=np.einsum('i,i,ijk->jk',allC,self.Qf,self.outer)
   for j,regions in enumerate([('UL','DL'),('H2',),('H3',)]):
    fs=np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),pts) for r in BANDS if r['case']==case and r['region'] in regions]);ws=fs*2*np.pi*1e6
    A=self.port[None,:,:]+coil[None,:,:]/ws[:,None,None]+ws[:,None,None]*Ycap[None,:,:]
    v=np.linalg.solve(A,np.broadcast_to(self.src,(len(ws),5))[...,None])[...,0]
    p=-10*np.log10(np.maximum(200*60/5200*np.abs(v[:,2])**2,1e-300))
    y[ci,j]=np.max(p) if j==0 else np.min(p)
  return y
 def to_result(self,r,dense=True):
  x=np.array(r['x']);m=self.metrics(x,7001 if dense else 301)
  K=self.build(x)[-1];v=x[self.vstart:-1].reshape(6,self.ncv)
  out={k:r[k] for k in ['success','termination','iterations','evals','secs','target']}
  out.update({'base_candidate':self.ref['name'],'chip_series':['LQP02'+s for s in self.series],
  'L_nH':np.exp(x[:4]).tolist(),'Q_L':self.q.tolist(),'fixed_C_pf':np.exp(x[4:self.kstart]).tolist(),
  'signed_neighbor_k':x[self.kstart:self.vstart].tolist(),'physical_row':self.row,
  'variable_C_edges':self.ref['cv_edges'],'fixed_C_edges':self.Cedges[:self.nf],
  'Cv_by_setting_pF':dict(zip(CASES,v.tolist())),'worst_IL_db':float(np.max(m[:,0])),
  'min_H2_db':float(np.min(m[:,1])),'min_H3_db':float(np.min(m[:,2])),
  'per_setting_metrics':dict(zip(CASES,m.tolist())),'min_K_eigenvalue':float(np.min(np.linalg.eigvalsh(K))),
  'samples_per_frequency_interval':7001 if dense else 301,
  'meets_0p30_and_30db':bool(m[:,0].max()<=.30+1e-10 and m[:,1:].min()>=30-1e-9),
  'independent_MNA_done':False,'SRF_EM_verified':False,'global_optimality_proven':False})
  return out


def main():
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--mode',choices=['run','validate'],default='run');a.add_argument('--case',choices=['EXP011-01','EXP014-02']);a.add_argument('--variant',choices=['HV4','HQ1','HQ4']);a.add_argument('--starts',type=int,default=2);a.add_argument('--iters',type=int,default=130);a.add_argument('--grid',type=int,default=7);a.add_argument('--target',type=float,default=30.002);opts=a.parse_args()
 names=[opts.case] if opts.case else list(OLD)
 for name in names:
  ref=OLD[name];variants=[opts.variant] if opts.variant else ['HV4','HQ1']
  for variant in variants:
   if variant=='HV4':series=['HV']*4
   elif variant=='HQ1':series=['HV','HQ','HV','HV']
   else:series=['HQ']*4
   net=Network(ref,series,opts.grid)
   try:old_metrics=net.metrics(net.init(),301);print('INIT',name,variant,'newQIL',float(old_metrics[:,0].max()),'H2',float(old_metrics[:,1].min()),'H3',float(old_metrics[:,2].min()),flush=True)
   except Exception as e:print('INIT_ERR',repr(e),flush=True)
   res=[]
   for k in range(opts.starts):
    x=net.init(random=None if k==0 else 20261012+k*997)
    r=net.optimize(x,opts.target,opts.iters);res.append(r)
    print('START',name,variant,k,'IL',r['IL'],'H2',r['H2'],'H3',r['H3'],'secs',r['secs'],'success',r['success'],flush=True)
   best=min(res,key=lambda r:(max(0,opts.target-min(r['H2'],r['H3']))*5+r['IL']))
   out=net.to_result(best,dense=True)
   p=HERE/(name+'_'+variant+'.json');p.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
   print('DENSE',name,variant,round(out['worst_IL_db'],8),round(out['min_H2_db'],8),round(out['min_H3_db'],8),'SPDMIN',round(out['min_K_eigenvalue'],5),'FILE',str(p),flush=True)
if __name__=='__main__':main()