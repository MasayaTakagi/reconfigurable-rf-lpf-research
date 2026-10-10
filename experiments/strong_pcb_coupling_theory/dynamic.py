import os, sys, json, time, itertools
import numpy as np
from scipy.optimize import minimize
from numba import njit
root=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,root+'/prior')
from explore import COUPLES, NAMES, BANDS, SMALL, MED, DENSE
from weak_search import getB, tr as transfer_old, SER
PRIOR=json.load(open(root+'/prior/results.json'))
REF=min((d for d in PRIOR if d['good'] and len(d['edges'])==3 and len(d['extraC'])==0), key=lambda r:r['IL'])
E=np.asarray(REF['edges'],np.int64).reshape(-1,2)
CP=np.asarray(REF['cp'],np.int64)
B=getB(REF['edges'])
N=3; D=7
P_PAIRS=np.array([(0,1),(0,2),(1,2)],np.int64)
@njit(cache=True)
def tr(x,kpp,fs,BB,CCI):
 # x old layout: L[4], k_chip[6], L_pcb[3], k_cp[3], six bands C[6*7] passed separately
 L=x[:4]; K=x[4:10]; LP=x[10:13]; kp=x[13:16]; C=x[16:]
 result=np.empty(len(fs),np.float64)
 for ix in range(len(fs)):
  w=2*np.pi*fs[ix]*1e6
  Z=np.zeros((7,7),np.complex128)
  for i in range(4):
   Z[i,i]=w*L[i]*1e-9*(1j+1/25.)
   if SER[i]:Z[i,i]+=(1/80.-1j)/(w*C[i]*1e-12)
  for i in range(6):
   a=COUPLES[i,0];b=COUPLES[i,1]
   z=1j*w*K[i]*np.sqrt(L[a]*L[b])*1e-9
   Z[a,b]=z;Z[b,a]=z
  for i in range(3):
   Z[4+i,4+i]=w*LP[i]*1e-9*(1j+1/12.)+(1/80.-1j)/(w*C[4+i]*1e-12)
   j=CCI[i]; zz=1j*w*kp[i]*np.sqrt(L[j]*LP[i])*1e-9
   Z[4+i,j]=zz;Z[j,4+i]=zz
  for i in range(3):
   a=P_PAIRS[i,0];b=P_PAIRS[i,1]
   zz=1j*w*kpp[i]*np.sqrt(LP[a]*LP[b])*1e-9
   Z[4+a,4+b]=zz;Z[4+b,4+a]=zz
  Y=BB.T@np.linalg.solve(Z,BB)
    # first four fixed chip capacitor edges from three_series(2): 0:0-1, 2:2-3, 3:1-2 (all shunted across chip), 1 is in series with chip
  for c,a,bb in ((0,0,1),(2,2,3),(3,1,2)):
   y=w*C[c]*1e-12/(1/80.-1j)
   Y[a,a]+=y;Y[bb,bb]+=y;Y[a,bb]-=y;Y[bb,a]-=y
  Y[0,0]+=1/50.
  Y[3,3]+=1/(60.-40j)
  rhs=np.zeros(4,np.complex128);rhs[0]=1/50.
  v=np.linalg.solve(Y,rhs)
  eta=4*50*(60/5200)*abs(v[3])**2
  result[ix]=-10*np.log10(max(eta,1e-100))
 return result

def get_psd(x,kpp):
 k=x[4:10];kp=x[13:16]
 A=np.eye(7)
 for v,(i,j) in zip(k, COUPLES):A[i,j]=A[j,i]=v
 for a in range(3):A[4+a,CP[a]]=A[CP[a],4+a]=kp[a]
 for v,(a,b) in zip(kpp,P_PAIRS):A[4+a,4+b]=A[4+b,4+a]=v
 return np.linalg.eigvalsh(A)[0]

x0=np.asarray(REF['x'],np.float64)
@njit(cache=True)
def unpack_c(xold,j):return xold[16+7*j:16+7*(j+1)]

def evaluate(x,k,gr=DENSE):
 out=[]
 for j,(pp,hh2,hh3) in enumerate(gr):
  xx=np.r_[x[:16],x[16+7*j:16+7*(j+1)]]
  p=tr(xx,k,pp);h2=tr(xx,k,hh2);h3=tr(xx,k,hh3)
  out.append([max(p),min(h2),min(h3)])
 return np.array(out)

def opt_band(x0,k,band,atten=35.05,grid=SMALL,maxiter=70):
 # per band opt capacitors with fixed L and all coupling
 pp,hh2,hh3=grid[band]
 z0=np.r_[x0[16+7*band:16+7*(band+1)], .6]
 def fd(q,ff):return tr(np.r_[x0[:16],q[:7]],k,ff)
 def const(z):return np.r_[z[7]-fd(z,pp),fd(z,hh2)-atten,fd(z,hh3)-atten]
 z0[7]=max(fd(z0,pp))
 res=minimize(lambda z:z[7],z0,bounds=[(.1,100)]*7+[(0,3)],constraints=[dict(type='ineq',fun=const)],method='SLSQP',options=dict(maxiter=maxiter,ftol=1e-8))
 return res.x[:7],res

def opt_separate(start,k,atten=35.05,grid=SMALL,maxiter=70):
 x=start.copy();res=[]
 for j in range(6):
  c,r=opt_band(x,k,j,atten,grid,maxiter);x[16+7*j:16+7*(j+1)]=c;res.append(r.success)
 return x,evaluate(x,k,DENSE),res

