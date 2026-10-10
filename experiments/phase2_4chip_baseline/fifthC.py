import sys,os,itertools,time,json
import numpy as np
from numba import njit
from scipy.optimize import minimize
sys.path[:0]=['/mnt/data/lpf_next','/mnt/data/lpf_phase2_extension']
from explore import *
OUT='/mnt/data/lpf_phase2_extension';Q=np.array([25.,25.,25.,25.,80.])
reference=json.load(open(OUT+'/first.json'))

@njit(cache=True)
def trans5(x,freq,B,ser,Cedges,pair):
 L=x[:4]; C=x[4:9];ks=x[9:15];n=B.shape[1]
 yyout=np.empty(len(freq),dtype=np.float64)
 for i in range(len(freq)):
  w=2*np.pi*freq[i]*1e6
  Z=np.zeros((4,4),dtype=np.complex128)
  for j in range(4):
   Z[j,j]=w*L[j]*1e-9*(1j+1/Q[j])
   if ser[j]:Z[j,j]+=(1/Q[4]-1j)/(w*C[j]*1e-12)
  for t in range(6):
   a=COUPLES[t,0];b=COUPLES[t,1]
   m=1j*w*ks[t]*np.sqrt(L[a]*L[b])*1e-9
   Z[a,b]=m;Z[b,a]=m
  Y=B.T@np.linalg.solve(Z,B)
  for t in range(Cedges.shape[0]):
   ci=int(Cedges[t,0]);a=int(Cedges[t,1]);b=int(Cedges[t,2]);y=w*C[ci]*1e-12/(1/Q[4]-1j)
   if a>=0:Y[a,a]+=y
   if b>=0:Y[b,b]+=y
   if a>=0 and b>=0:Y[a,b]-=y;Y[b,a]-=y
  a=int(pair[0]);b=int(pair[1]);y=w*C[4]*1e-12/(1/Q[4]-1j)
  if a>=0:Y[a,a]+=y
  if b>=0:Y[b,b]+=y
  if a>=0 and b>=0:Y[a,b]-=y;Y[b,a]-=y
  Y[0,0]+=1/50;Y[n-1,n-1]+=1/(60-40j)
  rhs=np.zeros(n,dtype=np.complex128);rhs[0]=1/50
  v=np.linalg.solve(Y,rhs)
  eta=4*50*(60/5200)*abs(v[n-1])**2
  yyout[i]=-10*np.log10(max(eta,1e-100))
 return yyout

def optimize(v0,bridge=(0,3),cmax=100,tar=35.05,maxiter=220):
 tp=three_series(2)
 B,ser,Cedges=tp; cp=np.array(bridge,dtype=np.int64)
 # x: 4L+6k+6*(4C+extraC)
 bounds=[(.4,27)]*4+[(-.25,.25) if j in (2,3) else (-.16,.16) for j in range(6)]+[(.1,100)]*30
 x=np.clip(v0,np.array(bounds)[:,0],np.array(bounds)[:,1]); z=np.r_[x,1.]
 def freqcase(xx,ii,grid):
  s=10+ii*5
  z2=np.r_[xx[:4],xx[s:s+5],xx[4:10]]
  return trans5(z2,grid,B,ser,Cedges,cp)
 def co(z):
  xx=z[:-1];il=z[-1];out=[]
  for j,(p,s,t) in enumerate(MED):
   out.extend(il-freqcase(xx,j,p));out.extend(freqcase(xx,j,s)-tar);out.extend(freqcase(xx,j,t)-tar)
  out.append(psd(xx[4:10])-.01)
  return np.array(out)
 tim=time.time()
 r=minimize(lambda zz:zz[-1],z,method='SLSQP',bounds=bounds+[(0,5)],constraints=[dict(type='ineq',fun=co)],options=dict(maxiter=maxiter,ftol=3e-9,disp=False))
 x=r.x[:-1]; v=[]
 for j,(p,s,t) in enumerate(DENSE):
  v.append((float(np.max(freqcase(x,j,p))),float(np.min(freqcase(x,j,s))),float(np.min(freqcase(x,j,t)))))
 return dict(IL=max(j[0] for j in v),H2=min(j[1] for j in v),H3=min(j[2] for j in v),feasible=bool(min(j[1] for j in v)>=tar-.012 and min(j[2] for j in v)>=tar-.012 and max(j[0] for j in v)<=r.x[-1]+.02 and psd(x[4:10])>.009),x=x.tolist(),bridge=bridge,sec=time.time()-tim,status=r.message,success=bool(r.success),perband=dict(zip(NAMES,v)),extraC=x[14::5].tolist())

if __name__=='__main__':
 src=np.array(reference['x'])
 def seedinit(cval):
  return np.r_[src[:10],np.array([np.r_[src[10+4*j:14+4*j],cval] for j in range(6)]).ravel()]
 hist=[]
 for edge in [(0,3),(0,2),(1,3),(1,-1),(2,-1),(3,-1),(0,-1)]:
  for name,cv in [('small',.1),('med',2.)]:
   r=optimize(seedinit(cv),bridge=edge,tar=35.05,maxiter=180)
   r['seed']=name;hist.append(r)
   print('RUN',edge,name,'IL',r['IL'],'H2',r['H2'],'H3',r['H3'],'ok',r['feasible'],'time',r['sec'],'extraC',np.round(r['extraC'],3).tolist(),flush=True)
   json.dump(hist,open(OUT+'/fifthC_results.json','w'),indent=1)
