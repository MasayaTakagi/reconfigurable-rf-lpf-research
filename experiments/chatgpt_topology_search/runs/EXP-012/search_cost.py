import numpy as np, csv, json, time, sys, argparse, itertools, os
from pathlib import Path
from scipy.optimize import minimize
HERE=Path(__file__).resolve().parent
BANDS=list(csv.DictReader((Path(__file__).resolve().parents[4]/'data/bands.csv').open()))
CASES=['B71','B12','B28','B13+B14','B26','B8']
LBASE=np.array([3.4084616011657642,55.99999999977252,8.04453326111069,4.853728404004065])
KBASE=np.array([0.012921955677951433,-0.3731669847779207,.4])
VBASE=np.array([[.2655710118970864,1.4905637169005168,.926012967688509],[.23319316276592664,1.4447089109110012,.7909183255681816],[.23985905343565994,1.325692834408903,.6926177929900169],[.17773375234919175,1.2653835161596694,.47218527998014626],[.15563317025942675,1.1786053852732299,.3056833282662742],[.12656459961354002,1.0422793219599482,0.]])
LEDGES=[(1,2),(3,4),(2,5),(2,3)]
CVEDGES=[(4,0),(5,0),(2,3)]
ALL_EDGES=[(a,b) for a in range(1,6) for b in range(a)]

def inc(edge):
 v=np.zeros(5)
 a,b=edge
 if a:v[a-1]+=1
 if b:v[b-1]-=1
 return v
class Model:
 def __init__(self,inds=tuple(range(4)),ledges=None,cedges=((1,2),),var_edges=((4,0),(5,0)),n=11,qL=None,fixed_q=None,fixed_ranges=None):
  self.inds=list(inds);self.nl=len(inds);self.ledges=[tuple(e) for e in (ledges or [LEDGES[i] for i in inds])]
  self.cedges=list(cedges);self.var_edges=list(var_edges);self.nc=len(cedges);self.nv=len(var_edges);self.n=n
  self.fixed_q=list(fixed_q or [80]*self.nc);self.fixed_ranges=list(fixed_ranges or [(0.1,100)]*self.nc)
  self.row=[x for x in [1,2,3,0] if x in inds]
  self.neighbor=[(self.row[i],self.row[i+1]) for i in range(len(self.row)-1)]
  self.ix={original:i for i,original in enumerate(inds)}
  self.qL=np.array(qL or [25]*self.nl)
  self.B=np.column_stack([inc(e) for e in self.ledges])
  self.VC=np.array([inc(e) for e in self.cedges+self.var_edges])
  self.O=self.VC[:,:,None]*self.VC[:,None,:]
  self.cfac=1/(1/np.array(self.fixed_q+[80]*self.nv)-1j)
  self.port=np.zeros((5,5),complex);self.port[0,0]=1/50;self.port[2,2]=1/(60-40j)
  self.source=np.array([.02,0,0,0,0],complex);self.eout=np.array([0,0,1,0,0],complex)
  self.kstart=self.nl+self.nc;self.vstart=self.kstart+len(self.neighbor)
  self.bounds=[(np.log(.4),np.log(56))]*self.nl+[(np.log(z[0]),np.log(z[1])) for z in self.fixed_ranges]+[(-.4,.4)]*len(self.neighbor)+[(0,4)]*(6*self.nv)+[(0,2)]
  obs=[]
  for si,case in enumerate(CASES):
   for b in BANDS:
    if b['case']!=case:continue
    reg=b['region'];passband=reg in ('UL','DL')
    for f in np.linspace(float(b['low_mhz']),float(b['high_mhz']),n):obs.append((si,passband,f))
  self.cases=np.array([z[0] for z in obs],int);self.passband=np.array([z[1] for z in obs],bool);self.omega=2*np.pi*1e6*np.array([z[2] for z in obs]);self.cache=None
 def project(self,which=(0,1),cfix=.780468567289133,pert=0):
  L=LBASE[self.inds];K=[]
  for a,b in self.neighbor:
   if (a,b) in [(1,2),(2,3),(3,0)]: K.append(KBASE[[(1,2),(2,3),(3,0)].index((a,b))])
   else:K.append(0.)
  t=np.array([[VBASE[si,j] if self.var_edges[jj]==CVEDGES[j] else .3 for jj,j in enumerate(which)] for si in range(6)]) if len(which)==self.nv else np.full((6,self.nv),.3)
  # more principled mapping by edge
  for jj,e in enumerate(self.var_edges):
   if e in CVEDGES:t[:,jj]=VBASE[:,CVEDGES.index(e)]
  return np.r_[np.log(L),np.log(np.array([cfix if q==80 else .02005 for q in self.fixed_q])),K,t.ravel(),.34]
 def _network(self,x):
  L=np.exp(x[:self.nl])*1e-9
  M=np.diag(L.astype(complex));K=np.eye(self.nl)
  for j,(a,b) in enumerate(self.neighbor):
   z=x[self.kstart+j]; ai,bi=self.ix[a],self.ix[b]
   M[ai,bi]=M[bi,ai]=z*np.sqrt(L[ai]*L[bi]);K[ai,bi]=K[bi,ai]=z
  if np.linalg.eigvalsh(K).min()<1e-8:raise ValueError('Non positive K')
  Z=np.diag(L/self.qL)+1j*M;Zi=np.linalg.inv(Z)
  YL=self.B@Zi@self.B.T
  return L,M,Z,Zi,YL,K
 def _ev(self,x):
  if self.cache is not None and np.array_equal(self.cache[0],x):return self.cache[1:]
  L,M,Z,Zi,YL,K=self._network(x)
  Cfix=np.exp(x[self.nl:self.kstart])*1e-12;CV=x[self.vstart:-1].reshape(6,self.nv)*1e-12
  cap=np.concatenate([np.broadcast_to(Cfix,(len(self.omega),self.nc)),CV[self.cases]],axis=1)
  Ycap=np.einsum('ni,i,ijk->njk',cap,self.cfac,self.O)
  mat=self.port[None,:,:]+YL[None,:,:]/self.omega[:,None,None]+self.omega[:,None,None]*Ycap
  V=np.linalg.solve(mat,np.broadcast_to(self.source,(len(mat),5))[...,None])[...,0]
  W=np.linalg.solve(mat.transpose(0,2,1),np.broadcast_to(self.eout,(len(mat),5))[...,None])[...,0]
  o=V[:,2]
  il=-10*np.log10(np.maximum(200*60/5200*abs(o)**2,1e-300))
  mul=(20/np.log(10))/np.where(abs(o)>1e-200,o,1e-200+0j)
  jac=np.zeros((len(mat),len(x)))
  R=W@self.B@Zi;D=V@self.B@Zi
  for i in range(self.nl):
   z=(L[i]/self.qL[i]+1j*L[i])*R[:,i]*D[:,i]
   for a,b in self.neighbor:
    ia,ib=self.ix[a],self.ix[b]
    if i==ia or i==ib:z+=.5j*M[ia,ib]*(R[:,ia]*D[:,ib]+R[:,ib]*D[:,ia])
   jac[:,i]=np.real(-mul*z/self.omega)
  E=W@self.VC.T;F=V@self.VC.T
  dcap=mul[:,None]*self.omega[:,None]*E*F*self.cfac[None,:]*1e-12
  for i in range(self.nc):jac[:,self.nl+i]=np.real(dcap[:,i]*np.exp(x[self.nl+i]))
  for j,(a,b) in enumerate(self.neighbor):
   ia,ib=self.ix[a],self.ix[b]
   z=1j*np.sqrt(L[ia]*L[ib])*(R[:,ia]*D[:,ib]+R[:,ib]*D[:,ia])
   jac[:,self.kstart+j]=np.real(-mul*z/self.omega)
  for si in range(6):
   idx=np.where(self.cases==si)[0]
   jac[idx,self.vstart+si*self.nv:self.vstart+(si+1)*self.nv]=np.real(dcap[idx,self.nc:])
  self.cache=(x.copy(),il,jac)
  return il,jac
 def cons(self,x,goal):
  il,_=self._ev(x)
  return np.where(self.passband,x[-1]-il,il-goal)
 def cj(self,x,goal):
  il,jac=self._ev(x);j=jac.copy();j[self.passband,:]*=-1;j[self.passband,-1]=1;return j
 def metrics(self,x,n=201):
  L,M,Z,Zi,YL,K=self._network(x)
  Cf=np.exp(x[self.nl:self.kstart])*1e-12;Cv=x[self.vstart:-1].reshape(6,self.nv)*1e-12
  out=np.zeros((6,3)); worst=[]
  for si,case in enumerate(CASES):
   C=np.r_[Cf,Cv[si]];Ycap=np.einsum('i,i,ijk->jk',C,self.cfac,self.O)
   for gi,regs in enumerate((('UL','DL'),('H2',),('H3',))):
    frequencies=np.concatenate([np.linspace(float(b['low_mhz']),float(b['high_mhz']),n) for b in BANDS if b['case']==case and b['region'] in regs]);ws=2*np.pi*1e6*frequencies
    m=self.port[None,:,:]+YL[None,:,:]/ws[:,None,None]+ws[:,None,None]*Ycap[None,:,:]
    V=np.linalg.solve(m,np.broadcast_to(self.source,(len(ws),5))[...,None])[...,0]
    att=-10*np.log10(np.maximum(200*60/5200*abs(V[:,2])**2,1e-300))
    index=int(np.argmax(att) if gi==0 else np.argmin(att))
    out[si,gi]=att[index];worst.append((case,('pass','H2','H3')[gi],float(frequencies[index]),float(att[index])))
  return {'IL':float(np.max(out[:,0])),'H2':float(np.min(out[:,1])),'H3':float(np.min(out[:,2])),'bysetting':out.tolist(),'critical':worst}
 def optimize(self,x,goal=30.002,maxiter=120):
  self.cache=None;st=time.monotonic()
  def fun(y):return y[-1]
  def grad(y):return np.r_[np.zeros(len(y)-1),1.]
  r=minimize(fun,x,method='SLSQP',jac=grad,bounds=self.bounds,constraints=[{'type':'ineq','fun':lambda y:self.cons(y,goal),'jac':lambda y:self.cj(y,goal)}],options={'ftol':1e-9,'maxiter':maxiter})
  z=self.metrics(r.x,n=201)
  z.update(x=r.x.tolist(),niter=int(r.nit),status=int(r.status),message=r.message,success=bool(r.success),seconds=round(time.monotonic()-st,3))
  return z

def unit():
 m=Model(var_edges=CVEDGES,n=5);x=m.project(which=[0,1,2]);v,j=m._ev(x);z=[]
 for i in range(len(x)-1):
  xx=x.copy();xx[i]+=1e-6;yy=x.copy();yy[i]-=1e-6
  fd=(m._ev(xx)[0]-m._ev(yy)[0])/2e-6
  z.append(float(np.max(abs(fd-j[:,i]))))
 print('TEST max abs Jacobian err',max(z),'IL range',min(v),max(v));assert max(z)<0.002
 print('reference metrics',m.metrics(x,n=101))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--unit',action='store_true');p.add_argument('--mode',default='pairs');p.add_argument('--maxiter',type=int,default=140);p.add_argument('--grid',type=int,default=9);p.add_argument('--starts',type=int,default=1);p.add_argument('--limit',type=int,default=1000);p.add_argument('--shards',type=int,default=1);p.add_argument('--shard-index',type=int,default=0);p.add_argument('--checkpoint',type=str,default='');a=p.parse_args()
 assert 1<=a.shards and 0<=a.shard_index<a.shards
 if a.unit:unit();exit()
 jobs=[]
 if a.mode=='pairs':
  for ee in itertools.combinations(CVEDGES,2):jobs.append((tuple(range(4)),tuple(LEDGES),((1,2),),ee))
 elif a.mode=='two_ground':
  for ee in itertools.combinations([(a,0) for a in range(1,6)],2):jobs.append((tuple(range(4)),tuple(LEDGES),((1,2),),ee))
 elif a.mode=='no_fixed':
  for ee in itertools.combinations(CVEDGES,2):jobs.append((tuple(range(4)),tuple(LEDGES),(),ee))
 elif a.mode=='three_L':
  for drop in range(4):
   for ee in itertools.combinations(CVEDGES,2):jobs.append((tuple(i for i in range(4) if i!=drop),tuple(LEDGES[i] for i in range(4) if i!=drop),((1,2),),ee))
 elif a.mode=='zero_gjm_three_cv':
  jobs.append((tuple(range(4)),tuple(LEDGES),(),tuple(CVEDGES)))
 elif a.mode=='three_l_three_cv':
  for drop in range(4):jobs.append((tuple(i for i in range(4) if i!=drop),tuple(LEDGES[i] for i in range(4) if i!=drop),((1,2),),tuple(CVEDGES)))
 elif a.mode=='three_l_zero_gjm_three_cv':
  for drop in range(4):jobs.append((tuple(i for i in range(4) if i!=drop),tuple(LEDGES[i] for i in range(4) if i!=drop),(),tuple(CVEDGES)))
 elif a.mode=='two_cv_fixed_rewire':
  for ee in itertools.combinations(CVEDGES,2):
   for ce in ALL_EDGES:jobs.append((tuple(range(4)),tuple(LEDGES),(ce,),ee))
 elif a.mode=='two_cv_two_gjm':
  for ee in itertools.combinations(CVEDGES,2):
   for ce in ALL_EDGES:jobs.append((tuple(range(4)),tuple(LEDGES),((1,2),ce),ee))
 elif a.mode=='two_cv_all_edges':
  for ee in itertools.combinations(ALL_EDGES,2):jobs.append((tuple(range(4)),tuple(LEDGES),((1,2),),ee))
 elif a.mode=='all_edges':
  for ee in itertools.combinations(ALL_EDGES,2):jobs.append((tuple(range(4)),tuple(LEDGES),((1,2),),ee))
 else:raise ValueError(a.mode)
 results=[];output=Path(a.checkpoint) if a.checkpoint else HERE/('screen_'+a.mode+'.json')
 output.parent.mkdir(parents=True,exist_ok=True)
 if output.exists():
  old=json.loads(output.read_text());assert old['params']['mode']==a.mode and old['params']['shard_index']==a.shard_index and old['params']['shards']==a.shards,'resume mode/shard mismatch';results=old['trials'];done=set((z['job_index'],z['start']) for z in results)
 else:done=set()
 for ji,job in enumerate(jobs[:a.limit]):
  if ji%a.shards!=a.shard_index:continue
  for st in range(a.starts):
   if (ji,st) in done:continue
   mod=Model(inds=job[0],ledges=job[1],cedges=job[2],var_edges=job[3],n=a.grid)
   x=mod.project();seed=20261012+917*ji+st*313
   if st:
    rng=np.random.default_rng(seed);x[:mod.nl]+=rng.normal(0,.1,mod.nl)
    x[mod.nl:mod.kstart]+=rng.normal(0,.1,mod.nc)
    x[mod.kstart:mod.vstart]+=rng.normal(0,.03,len(mod.neighbor))
    x[mod.vstart:-1]+=rng.normal(0,.06,6*mod.nv)
   x=np.clip(x,np.array(mod.bounds)[:,0]+1e-8,np.array(mod.bounds)[:,1]-1e-8)
   try:r=mod.optimize(x,maxiter=a.maxiter)
   except Exception as e:r={'error':repr(e)}
   r.update(job_index=ji,start=st,job={'L':[LEDGES[i] for i in job[0]],'GJM':job[2],'Cv':job[3]})
   results.append(r)
   temp=output.with_suffix(output.suffix+'.tmp');temp.write_text(json.dumps({'mode':a.mode,'n_jobs':len(jobs),'params':vars(a),'trials':results,'source_file':'search_cost.py','optimizer_seed_rule':'20261012+917*job_index+start*313','commit_sha':os.getenv('GITHUB_SHA','not-provided')},indent=2));temp.replace(output)
   if 'IL' in r:
    print(a.mode,ji,st,'IL',round(r['IL'],8),'H2',round(r['H2'],5),'H3',round(r['H3'],5),'iter',r['niter'],'s',r['seconds'],flush=True)
   else:print(a.mode,ji,'ERROR',str(r),flush=True)
 good=[z for z in results if 'IL' in z and min(z['H2'],z['H3'])>=30 and z['IL']<=.30]
 print('SEARCH DONE',a.mode,len(results),'FEASIBLE',len(good),'bestIL',min([v['IL'] for v in good],default=None))