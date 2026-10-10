import os, sys, json, time, itertools, argparse
import numpy as np
from scipy.optimize import minimize
from numba import njit
NAMES=['B71','B12','B28','B13+14','B26','B8']
BANDS={
 'B71': {'ul':[(663,698)], 'dl':[(617,652)]},
 'B12': {'ul':[(699,716)], 'dl':[(729,746)]},
 'B28': {'ul':[(703,748)], 'dl':[(758,803)]},
 'B13+14':{'ul':[(777,787),(788,798)],'dl':[(746,756),(758,768)]},
 'B26': {'ul':[(814,849)], 'dl':[(859,894)]},
 'B8': {'ul':[(880,915)], 'dl':[(925,960)]}}
COUPLES=np.array([(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)],dtype=np.int64)
# circuit 4 inductors, each with a C: capacitors for shunts are in series; series C is parallel to L; optional C bridges arbitrary nodes.
# branches matrix (4, n_nodes), seriesC[j] true if capacitor in series with inductor, shuntC[j] if cap in parallel with L, bridge C additional definition.
@njit(cache=True)
def transfer(x,ff,B,seriesC,Cedges,Q):
 L=x[:4];C=x[4:8];k=x[8:14]; n=B.shape[1]
 result=np.empty(len(ff),dtype=np.float64)
 for i in range(len(ff)):
  w=2*np.pi*ff[i]*1e6
  Z=np.zeros((4,4),dtype=np.complex128)
  for j in range(4):
   Z[j,j]=w*L[j]*1e-9*(1j+1/Q[j])
   if seriesC[j]: Z[j,j]+=(1/Q[4]-1j)/(w*C[j]*1e-12)
  for j in range(6):
   a=COUPLES[j,0];b=COUPLES[j,1]
   z=1j*w*k[j]*np.sqrt(L[a]*L[b])*1e-9
   Z[a,b]=z;Z[b,a]=z
  YY=B.T@np.linalg.solve(Z,B)
  for j in range(Cedges.shape[0]):
   c=int(Cedges[j,0]);a=int(Cedges[j,1]);b=int(Cedges[j,2]); y=w*C[c]*1e-12/(1/Q[4]-1j)
   if a>=0: YY[a,a]+=y
   if b>=0: YY[b,b]+=y
   if a>=0 and b>=0:YY[a,b]-=y;YY[b,a]-=y
  YY[0,0]+=1/50
  YY[n-1,n-1]+=1/(60-40j)
  rhs=np.zeros(n,dtype=np.complex128);rhs[0]=1/50
  v=np.linalg.solve(YY,rhs)
  eta=4*50*(60/5200)*abs(v[n-1])**2
  result[i]=-10*np.log10(max(eta,1e-100))
 return result

def make_topo(branches, seriesC, edges, n):
 B=np.zeros((4,n),dtype=np.complex128)
 for j,(a,b) in enumerate(branches):
  if a>=0: B[j,a]+=1
  if b>=0: B[j,b]-=1
 return (B,np.array(seriesC,dtype=np.bool_),np.array(edges,dtype=np.int64).reshape((-1,3)))

def three_series(shuntnode=2, cap_map=None, order=(0,3,2)):
 # order is physical L indices, L1=0 L4=3 L3=2; shunt L2=1
 br=[None]*4
 for i,j in enumerate(order):br[j]=(i,i+1)
 br[1]=(shuntnode,-1)
 if cap_map is None:cap_map={j:br[j] for j in order}
 ed=[(j,*cap_map[j]) for j in order]
 return make_topo(br,[False,True,False,False],ed,4)

def two_series(shunts=(0,2), series=(0,3), cap_map=None):
 br=[None]*4
 for edge,j in enumerate(series):br[j]=(edge,edge+1)
 others=[j for j in range(4) if j not in series]
 for j,node in zip(others,shunts):br[j]=(node,-1)
 ed=[(j,*br[j]) for j in series] if cap_map is None else [(j,*cap_map[j]) for j in series]
 iser=[j in others for j in range(4)]
 return make_topo(br,iser,ed,3)

def one_series(shunts=(0,0,1), seriesidx=0):
 br=[None]*4;br[seriesidx]=(0,1)
 others=[j for j in range(4) if j!=seriesidx]
 for j,n in zip(others,shunts):br[j]=(n,-1)
 return make_topo(br,[j!=seriesidx for j in range(4)],[(seriesidx,0,1)],2)

def grids(N=5):
 rr=[]
 for name in NAMES:
  d=BANDS[name]
  def flatten(bands,s):
   return np.unique(np.concatenate([np.linspace(a*s,b*s,N) for a,b in bands]))
  rr.append((flatten(d['ul']+d['dl'],1),flatten(d['ul'],2),flatten(d['ul'],3)))
 return rr
SMALL=grids(3);MED=grids(6);DENSE=grids(41)

def single(i,x,top,Q,points=DENSE):
 fp,f2,f3=points[i]
 z=np.r_[x[:4],x[10+4*i:14+4*i],x[4:10]]
 return (float(max(transfer(z,fp,*top,Q))),float(min(transfer(z,f2,*top,Q))),float(min(transfer(z,f3,*top,Q))))

def evaluation(x,top,Q,points=DENSE):
 out=[single(i,x,top,Q,points) for i in range(6)]
 return dict(IL=max(z[0] for z in out),H2=min(z[1] for z in out),H3=min(z[2] for z in out),perband={nm:dict(IL=z[0],H2=z[1],H3=z[2]) for nm,z in zip(NAMES,out)})

def psd(k):
 A=np.eye(4)
 for i,(a,b) in enumerate(COUPLES):A[a,b]=A[b,a]=k[i]
 return np.linalg.eigvalsh(A)[0]

def opt(v0,top,atten=34.,cmin=.1,cmax=100.,Lmin=.4,Lmax=27., coupling='two',Q=np.array([25.,25.,25.,25.,80.]),stage=SMALL,maxiter=150,ftol=1e-8):
 if coupling=='two': kbd=[(-.03,.03)]*6; kbd[2]=(-.25,.25);kbd[3]=(-.25,.25)
 elif coupling=='all':kbd=[(-.25,.25)]*6
 elif coupling=='one': kbd=[(-.03,.03)]*6;kbd[3]=(-.25,.25)
 elif coupling=='weak':kbd=[(-.03,.03)]*6
 elif isinstance(coupling,list):kbd=coupling
 else:raise ValueError
 bd=[(Lmin,Lmax)]*4+kbd+[(cmin,cmax)]*24
 z=np.clip(np.asarray(v0),np.array(bd)[:,0],np.array(bd)[:,1]); z=np.r_[z,max(.1,evaluation(z,top,Q,SMALL)['IL'])]
 def cons(zz):
  x=zz[:-1]; t=zz[-1]; out=[]
  for i,(fp,f2,f3) in enumerate(stage):
   xi=np.r_[x[:4],x[10+4*i:14+4*i],x[4:10]]
   p=transfer(xi,fp,*top,Q);h2=transfer(xi,f2,*top,Q);h3=transfer(xi,f3,*top,Q)
   out.extend(t-p);out.extend(h2-atten);out.extend(h3-atten)
  return np.asarray(out)
 t0=time.time()
 r=minimize(lambda x:x[-1],z,bounds=bd+[(0,5)],constraints=[dict(type='ineq',fun=cons)],method='SLSQP', options=dict(maxiter=maxiter,ftol=ftol,disp=False))
 x=r.x[:-1]; m=evaluation(x,top,Q,DENSE)
 m.update(x=x.tolist(),iter=int(r.nit),success=bool(r.success),seconds=round(time.time()-t0,2),Pmin=float(psd(x[4:10])),target=atten)
 m['feasible']=m['H2']>=atten-.012 and m['H3']>=atten-.012 and m['IL']<=r.x[-1]+.015 and m['Pmin']>=-.00001
 return m

def seed():
 with open('/mnt/data/lpf_next/confirmed_3series.json') as f:j=json.load(f)
 # past: x = L4 / 6 k / 24 C
 return np.asarray(j['design']['x'])

if __name__=='__main__':
 q=np.array([25.,25.,25.,25.,80.]);x=seed();tp=three_series(2)
 print('REPRO',evaluation(x,tp,q,DENSE), 'PSD',psd(x[4:10]),flush=True)
 for tgt in [34,35.05]:
  m=opt(x,tp,atten=tgt,cmax=100,Q=q,maxiter=90)
  print('test',tgt,{k:v for k,v in m.items() if k not in ('x','perband')},flush=True)
