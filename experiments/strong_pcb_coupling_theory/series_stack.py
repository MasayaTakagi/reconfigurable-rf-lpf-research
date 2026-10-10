import os, numpy as np,json,time
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"prior"))
from numba import njit
from scipy.optimize import minimize
from prior.explore import SMALL, MED, DENSE, COUPLES, NAMES
from prior.weak_search import SER, BCH
ROOT=os.path.dirname(os.path.abspath(__file__))
base=json.load(open(ROOT+'/base_search.json'))
ref=min([r for r in base if r.get('feasible') and r.get('topology')=='3series_middle'],key=lambda r:r['IL'])
X=np.array(ref['x'],dtype=np.float64)
chip_bounds=[(.4,27)]*4+[((-.25,.25) if i in (2,3) else (-.16,.16)) for i in range(6)]
# Perfectly aligned, passive but near-singular PCB-PCB coupling, k=0.98
kpc=.98
stack_multiplier=3+6*kpc # each PCB-L contributes one value lp, cross three pairs
qpcb=12*(1+2*kpc)
@njit(cache=True)
def trstack(xx,fs,ba,bb,serie):
 # xx: chip L[4], k[6], pcb per-coil L, C[5]
 L=xx[:4];K=xx[4:10];Lone=xx[10];C=xx[11:16]
 y=np.empty(len(fs),np.float64)
 for ix in range(len(fs)):
  w=2*np.pi*fs[ix]*1e6
  Z=np.zeros((4,4),np.complex128)
  for a in range(4):
   Z[a,a]=w*L[a]*1e-9*(1j+1/25.)
   if SER[a]:Z[a,a]+=(1/80-1j)/(w*C[a]*1e-12)
  for p in range(6):
   a=COUPLES[p,0];b=COUPLES[p,1]
   v=1j*w*K[p]*np.sqrt(L[a]*L[b])*1e-9
   Z[a,b]=v; Z[b,a]=v
  Y=BCH.T@np.linalg.solve(Z,BCH)
  for a,i,j in ((0,0,1),(2,2,3),(3,1,2)):
   v=w*C[a]*1e-12/(1/80-1j)
   Y[i,i]+=v;Y[j,j]+=v;Y[i,j]-=v;Y[j,i]-=v
  # three PCB-L in aiding series, with (optionally) a series capacitor C5
  zpcb=w*Lone*1e-9*(3/12+1j*stack_multiplier)
  if serie:
   zpcb+=(1/80-1j)/(w*C[4]*1e-12)
  yp=1/zpcb
  if ba>=0:Y[ba,ba]+=yp
  if bb>=0:Y[bb,bb]+=yp
  if ba>=0 and bb>=0:
   Y[ba,bb]-=yp;Y[bb,ba]-=yp
  Y[0,0]+=1/50
  Y[3,3]+=1/(60-40j)
  s=np.zeros(4,np.complex128);s[0]=1/50
  v=np.linalg.solve(Y,s)
  eta=4*50*(60/5200)*abs(v[3])**2
  y[ix]=-10*np.log10(max(eta,1e-100))
 return y

def evalx(z,edge,serie,grid=MED):
 out=[]
 for j,(passf,h2,h3) in enumerate(grid):
  xx=np.r_[z[:11],z[11+5*j:11+5*(j+1)]]
  out.append([max(trstack(xx,passf,*edge,serie)),min(trstack(xx,h2,*edge,serie)),min(trstack(xx,h3,*edge,serie))])
 return np.array(out)

def optim(edge,serie=True, init=None, maxiter=160, grid=SMALL, tmin=35.05, fixchip=False):
 seed=np.r_[X[:10],.5,np.array([np.r_[X[10+j*4:14+j*4],2.5] for j in range(6)]).ravel()]
 if init is not None:seed=np.array(init['x'],dtype=float)
 if fixchip:
  z0=np.r_[seed[10:],max(evalx(seed,edge,serie,SMALL)[:,0])]
  bounds=[(.1,3)] + [( .1,100)]*30+[(0,2)]
  def parse(z):return np.r_[seed[:10],z[:-1]],z[-1]
 else:
  z0=np.r_[seed,max(evalx(seed,edge,serie,SMALL)[:,0])]
  bounds=chip_bounds+[(.1,3)] +[(.1,100)]*30+[(0,2)]
  def parse(z):return z[:-1],z[-1]
 def con(z):
  xx,t=parse(z);result=[]
  for b,(passf,h2,h3) in enumerate(grid):
   qq=np.r_[xx[:11],xx[11+5*b:11+5*(b+1)]]
   result.extend(t-trstack(qq,passf,*edge,serie))
   result.extend(trstack(qq,h2,*edge,serie)-tmin)
   result.extend(trstack(qq,h3,*edge,serie)-tmin)
  A=np.eye(4)
  for k,(a,b) in zip(xx[4:10],COUPLES):A[a,b]=A[b,a]=k
  result.append(np.linalg.eigvalsh(A)[0]-.02)
  return np.asarray(result)
 z0=np.clip(z0,np.array(bounds)[:,0],np.array(bounds)[:,1])
 st=time.time()
 rr=minimize(lambda z:z[-1],z0,method='SLSQP',bounds=bounds,constraints=[{'type':'ineq','fun':con}],options={'maxiter':maxiter,'ftol':1e-8})
 z,t=parse(rr.x);metrics=evalx(z,edge,serie,DENSE)
 return dict(edge=edge,series_cap=serie,x=z.tolist(),maxIL=float(np.max(metrics[:,0])),minH2=float(np.min(metrics[:,1])),minH3=float(np.min(metrics[:,2])),metrics=metrics.tolist(),time=round(time.time()-st,1),nit=int(rr.nit),success=bool(rr.success),message=rr.message, Lpcb_effective_nH=float(z[10]*stack_multiplier),Qpcb_effective=float(qpcb))

if __name__=='__main__':
 out=[]
 for edge in [(2,3),(1,2),(0,1),(0,2),(1,3),(2,-1),(1,-1),(0,3)]:
  for s in [True,False]:
   r=optim(edge,s,maxiter=110)
   out.append(r);json.dump(out,open(ROOT+'/series_stack_results.json','w'),indent=2)
   print('EDGE',edge,'Cser',s,'IL',round(r['maxIL'],6),'H2',round(r['minH2'],3),'H3',round(r['minH3'],3),'L_eff',round(r['Lpcb_effective_nH'],3),'suc',r['success'],'secs',r['time'],flush=True)
