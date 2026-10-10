import os,json,sys,time,numpy as np
from scipy.optimize import minimize
from numba import njit
from explore import three_series, COUPLES, SMALL, MED, DENSE, NAMES, psd
BASE=json.load(open('/mnt/data/pcb_weak_study/first.json'))
BCH,SER,CE=three_series(2)
N=4
@njit(cache=True)
def tr(L,K,LP,kp,C,fs,B,edges,chipids,nP,nC):
 result=np.empty(len(fs),dtype=np.float64)
 for ix in range(len(fs)):
  w=2*np.pi*fs[ix]*1e6
  Z=np.zeros((4+nP,4+nP),dtype=np.complex128)
  for i in range(4):
   Z[i,i]=w*L[i]*1e-9*(1j+1/25.)
   if SER[i]:Z[i,i]+=(1/80.-1j)/(w*C[i]*1e-12)
  for i in range(6):
   a=COUPLES[i,0];b=COUPLES[i,1];v=1j*w*K[i]*np.sqrt(L[a]*L[b])*1e-9
   Z[a,b]=v;Z[b,a]=v
  for i in range(nP):
   Z[4+i,4+i]=w*LP[i]*1e-9*(1j+1/12.)+(1/80.-1j)/(w*C[4+i]*1e-12)
   # weak coupled (chip and PCB only)
   j=chipids[i]
   v=1j*w*kp[i]*np.sqrt(L[j]*LP[i])*1e-9
   Z[4+i,j]=v;Z[j,4+i]=v
  Y=B.T@np.linalg.solve(Z,B)
  for i in range(len(CE)):
   ci=int(CE[i,0]);a=int(CE[i,1]);b=int(CE[i,2]);y=w*C[ci]*1e-12/(1/80.-1j)
   if a>=0:Y[a,a]+=y
   if b>=0:Y[b,b]+=y
   if a>=0 and b>=0:Y[a,b]-=y;Y[b,a]-=y
  for i in range(nC):
   a=int(edges[i,0]);b=int(edges[i,1]);y=w*C[4+nP+i]*1e-12/(1/80.-1j)
   if a>=0:Y[a,a]+=y
   if b>=0:Y[b,b]+=y
   if a>=0 and b>=0:Y[a,b]-=y;Y[b,a]-=y
  Y[0,0]+=1/50.
  Y[3,3]+=1/(60.-40j)
  rhs=np.zeros(4,np.complex128);rhs[0]=1/50.
  v=np.linalg.solve(Y,rhs)
  eta=4*50*(60/5200)*abs(v[-1])**2
  result[ix]=-10*np.log10(max(eta,1e-99))
 return result

def getB(pe):
 b=np.zeros((4+len(pe),4),np.complex128);b[:4]=BCH
 for j,(a,c) in enumerate(pe):
  if a>=0:b[4+j,a]+=1
  if c>=0:b[4+j,c]-=1
 return b

def getpsd(K,kp,cp):
 q=np.eye(4+len(kp))
 for k,(a,b) in zip(K,COUPLES):q[a,b]=q[b,a]=k
 for i,(c,k) in enumerate(zip(cp,kp)):q[c,4+i]=q[4+i,c]=k
 return np.linalg.eigvalsh(q)[0]

def mkstart(edges,cp,cextra,reference=None):
 nP=len(edges); nC=len(cextra);D=4+nP+nC
 b=np.array(BASE['x'] if reference is None else reference)
 if len(b)!=34:raise ValueError
 baseCs=b[10:].reshape(6,4)
 return np.r_[b[:10],np.full(nP,2.5),np.zeros(nP),np.hstack((baseCs,np.full((6,nP),.5),np.full((6,nC),.15))).ravel()]

def opt(edges,cp,cextra=(),initial=None,grid=SMALL,maxiter=135,limited=False,atten=35.05,pcbmax=3.):
 nP=len(edges);nC=len(cextra);D=4+nP+nC
 B=getB(edges);E=np.asarray(cextra,np.int64).reshape(-1,2);cp=np.array(cp,np.int64)
 kb=[(-.16,.16)]*6;kb[2]=(-.25,.25);kb[3]=(-.25,.25)
 bounds=[(.4,27)]*4+kb+[(.1,pcbmax)]*nP+[(-.03,.03)]*nP+[(.1,100)]*(6*D)
 x=mkstart(edges,cp,cextra) if initial is None else np.asarray(initial).copy()
 x=np.clip(x,np.array(bounds)[:,0],np.array(bounds)[:,1])
 xx=np.r_[x,1.0]
 def freq(x,j,f):return tr(x[:4],x[4:10],x[10:10+nP],x[10+nP:10+2*nP],x[10+2*nP+j*D:10+2*nP+(j+1)*D],f,B,E,cp,nP,nC)
 def con(z):
  x=z[:-1];t=z[-1];ret=[]
  for j,(p,h2,h3) in enumerate(grid):
   ret.extend(t-freq(x,j,p))
   ret.extend(freq(x,j,h2)-atten)
   ret.extend(freq(x,j,h3)-atten)
  ret.append(getpsd(x[4:10],x[10+nP:10+2*nP],cp)-.01)
  return np.array(ret)
 st=time.monotonic()
 rr=minimize(lambda x:x[-1],xx,method='SLSQP',bounds=bounds+[(0,3)],constraints=[dict(type='ineq',fun=con)],options=dict(maxiter=maxiter,ftol=3e-9))
 x=rr.x[:-1]
 vals=[(float(max(freq(x,j,p))),float(min(freq(x,j,s))),float(min(freq(x,j,t)))) for j,(p,s,t) in enumerate(DENSE)]
 m=(max(z[0] for z in vals),min(z[1] for z in vals),min(z[2] for z in vals))
 good=bool(m[1]>=atten-.01 and m[2]>=atten-.01 and m[0]<=rr.x[-1]+.02 and getpsd(x[4:10],x[10+nP:10+2*nP],cp)>=.009)
 return dict(edges=edges,cp=cp.tolist(),extraC=cextra,IL=m[0],H2=m[1],H3=m[2],good=good,success=bool(rr.success),time=round(time.monotonic()-st,2),x=x.tolist(),perband=dict(zip(NAMES,vals)),lp=x[10:10+nP].tolist(),kp=x[10+nP:10+2*nP].tolist(),psd=float(getpsd(x[4:10],x[10+nP:10+2*nP],cp)),reason=str(rr.message))

if __name__=='__main__':
 configs=[([(0,2)],[2],[]), ([(1,3)],[3],[]), ([(0,3)],[2],[]), ([(1,2)],[2],[]), ([(2,3)],[2],[]), ([(1,-1)],[1],[]), ([(2,-1)],[2],[]), ([(0,2),(1,3)],[2,3],[]), ([(0,3),(1,-1)],[2,1],[]), ([(1,3),(2,-1)],[3,2],[]), ([(1,3),(2,-1)],[3,2],[(0,2)]), ([(0,2),(1,3)],[2,3],[(0,3)]), ([(0,1),(2,3)],[0,2],[]), ([(0,2),(1,3),(1,-1)],[2,3,1],[])]
 save='/mnt/data/pcb_weak_study/results.json'
 out=[]
 z=mkstart(*configs[0]);BB=getB(configs[0][0]);tr(z[:4],z[4:10],z[10:11],z[11:12],z[12:17],SMALL[0][0],BB,np.empty((0,2),np.int64),np.array([2],np.int64),1,0)
 for ix,(ee,cc,ex) in enumerate(configs):
  v=opt(ee,cc,ex,maxiter=105)
  out.append(v);json.dump(out,open(save,'w'),indent=2)
  print(ix+1,ee,ex,'IL',round(v['IL'],5),'H2',round(v['H2'],3),'H3',round(v['H3'],3),'OK',v['good'],'TIME',v['time'],flush=True)
