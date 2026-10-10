import sys,os,time,json
import numpy as np
from numba import njit
from scipy.optimize import minimize
sys.path[:0]=['/mnt/data/lpf_next']
from explore import *
OUT='/mnt/data/lpf_phase2_extension';Q=np.array([25.,25.,25.,25.,80.]);base=json.load(open(OUT+'/first.json'))

@njit(cache=True)
def transfer5L(x, freq, B, ser,Cedges, node):
 L=x[:4];k=x[4:10];L5=x[10];C=x[11:16];n=B.shape[1]
 result=np.empty(len(freq),dtype=np.float64)
 for i in range(len(freq)):
  w=2*np.pi*freq[i]*1e6
  Z=np.zeros((4,4),dtype=np.complex128)
  for j in range(4):
   Z[j,j]=w*L[j]*1e-9*(1j+1/Q[j])
   if ser[j]:Z[j,j]+=(1/Q[4]-1j)/(w*C[j]*1e-12)
  for j in range(6):
   a=COUPLES[j,0];b=COUPLES[j,1]
   z=1j*w*k[j]*np.sqrt(L[a]*L[b])*1e-9
   Z[a,b]=z;Z[b,a]=z
  Y=B.T@np.linalg.solve(Z,B)
  for j in range(Cedges.shape[0]):
   c=int(Cedges[j,0]);a=int(Cedges[j,1]);b=int(Cedges[j,2]);y=w*C[c]*1e-12/(1/Q[4]-1j)
   if a>=0:Y[a,a]+=y
   if b>=0:Y[b,b]+=y
   if a>=0 and b>=0:Y[a,b]-=y;Y[b,a]-=y
  Z5=w*L5*1e-9*(1j+1/12)+(1/80-1j)/(w*C[4]*1e-12)
  Y[node,node]+=1/Z5
  Y[0,0]+=1/50;Y[n-1,n-1]+=1/(60-40j)
  rhs=np.zeros(n,dtype=np.complex128);rhs[0]=1/50
  v=np.linalg.solve(Y,rhs)
  eta=4*50*(60/5200)*abs(v[n-1])**2
  result[i]=-10*np.log10(max(eta,1e-100))
 return result

def optimize(x0,node=1,tar=35.05,maxiter=200):
 tp=three_series(2);B,ser,Cedges=tp
 bd=[(.4,27)]*4+[(-.25,.25) if j in (2,3) else (-.16,.16) for j in range(6)]+[(.2,3.)]+[(.1,100.)]*30
 x=np.clip(x0,np.array(bd)[:,0],np.array(bd)[:,1]);z=np.r_[x,1.]
 def freq(xx,j,ff):
  ind=11+j*5
  xin=np.r_[xx[:11],xx[ind:ind+5]]
  return transfer5L(xin,ff,B,ser,Cedges,node)
 def cons(z):
  xx=z[:-1];t=z[-1];o=[]
  for i,(fp,f2,f3) in enumerate(MED):
   o.extend(t-freq(xx,i,fp));o.extend(freq(xx,i,f2)-tar);o.extend(freq(xx,i,f3)-tar)
  o.append(psd(xx[4:10])-.01)
  return np.asarray(o)
 start=time.time()
 r=minimize(lambda z:z[-1],z,bounds=bd+[(0,5)],constraints=[dict(type='ineq',fun=cons)],method='SLSQP',options=dict(maxiter=maxiter,ftol=2e-9))
 xx=r.x[:-1];vals=[]
 for j,(p,s,t) in enumerate(DENSE):vals.append((float(np.max(freq(xx,j,p))),float(np.min(freq(xx,j,s))),float(np.min(freq(xx,j,t)))))
 il=max(v[0] for v in vals);h2=min(v[1] for v in vals);h3=min(v[2] for v in vals)
 return dict(IL=il,H2=h2,H3=h3,feasible=bool(h2>=tar-.015 and h3>=tar-.015 and il<r.x[-1]+.02 and psd(xx[4:10])>=.009),x=xx.tolist(),node=node,L5=xx[10],C5=xx[15::5].tolist(),success=bool(r.success),sec=time.time()-start,perband=dict(zip(NAMES,vals)))

if __name__=='__main__':
 ss=np.array(base['x']);a=[]
 for node in [0,1,2,3]:
  for lv in [1.,2.5]:
   # initialize C5 near 2.6GHz for node1, near 1.8GHz for node2
   cval=1. if lv==2.5 else 4.
   z=np.r_[ss[:10],lv, np.array([np.r_[ss[10+4*j:14+4*j],cval] for j in range(6)]).reshape(-1)]
   r=optimize(z,node,maxiter=220)
   a.append(r)
   print('PCB',node,lv,'IL',round(r['IL'],6),'H2',round(r['H2'],3),'H3',round(r['H3'],3),'ok',r['feasible'],'L5',round(r['L5'],3),'seconds',round(r['sec'],1),flush=True)
   json.dump(a,open(OUT+'/pcb_shunt_results.json','w'),indent=1)
