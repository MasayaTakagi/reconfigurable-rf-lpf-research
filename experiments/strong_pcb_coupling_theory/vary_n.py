import os,sys,json,numpy as np,time
from scipy.optimize import minimize
from numba import njit
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'prior'))
from explore import SMALL, MED, DENSE, COUPLES, NAMES
from weak_search import SER,BCH
root=os.path.dirname(__file__)
@njit(cache=True)
def response(xx, fs, pcbk, ncoil):
 L=xx[:4];K=xx[4:10];Lone=xx[10];C=xx[11:15]
 y=np.empty(len(fs),np.float64)
 for ix in range(len(fs)):
  w=2*np.pi*fs[ix]*1e6
  Z=np.zeros((4,4),np.complex128)
  for a in range(4):
   Z[a,a]=w*L[a]*1e-9*(1j+1/25.)
   if SER[a]:Z[a,a]+=(1/80.-1j)/(w*C[a]*1e-12)
  for i in range(6):
   a=COUPLES[i,0];b=COUPLES[i,1]
   vv=1j*w*K[i]*np.sqrt(L[a]*L[b])*1e-9
   Z[a,b]=vv;Z[b,a]=vv
  Y=BCH.T@np.linalg.solve(Z,BCH)
  for j,a,b in ((0,0,1),(2,2,3),(3,1,2)):
   yc=w*C[j]*1e-12/(1/80.-1j)
   Y[a,a]+=yc;Y[b,b]+=yc;Y[a,b]-=yc;Y[b,a]-=yc
  # three series aiding PCB coils, same physical L 'Lone', pairwise equal coupling pcbk.
  Leff=Lone*(ncoil*(1+(ncoil-1)*pcbk))
  Rterm=Lone*ncoil/12.
  yp=1/(w*1e-9*(Rterm+1j*Leff))
  Y[2,2]+=yp;Y[3,3]+=yp;Y[2,3]-=yp;Y[3,2]-=yp
  Y[0,0]+=1/50.
  Y[3,3]+=1/(60-40j)
  rhs=np.zeros(4,np.complex128);rhs[0]=1/50.
  v=np.linalg.solve(Y,rhs)
  eta=4*50*(60/5200)*abs(v[3])**2
  y[ix]=-10*np.log10(max(eta,1e-100))
 return y

def metrics(x,k,gr,ncoil):
 y=[]
 for b,(p,f2,f3) in enumerate(gr):
  xx=np.r_[x[:11],x[11+4*b:15+4*b]]
  y.append([float(max(response(xx,p,k,ncoil))),float(min(response(xx,f2,k,ncoil))),float(min(response(xx,f3,k,ncoil)))])
 return np.array(y)

def opt(init, k, ncoil, target=35.15, g=SMALL, maxiter=240, fix_kchip=False):
 xinit=np.array(init)
 if len(xinit)==41: # 5C design from predecessor
  xinit=np.r_[xinit[:11],np.concatenate([xinit[11+b*5:15+b*5] for b in range(6)])]
 assert len(xinit)==35,len(xinit)
 bd=[(.4,27.)]*4+[(-.16,.16)]*6
 bd[4+2]=(-.25,.25);bd[4+3]=(-.25,.25)
 bd+=[(.1,3)]+[(.1,100)]*24+[(0,2)]
 if fix_kchip:
  z0=np.r_[xinit[10:],max(metrics(xinit,k,SMALL,ncoil)[:,0])]
  bounds=bd[10:]
  def unpack(q):return np.r_[xinit[:10],q[:-1]],q[-1]
 else:
  z0=np.r_[xinit,max(metrics(xinit,k,SMALL,ncoil)[:,0])]
  bounds=bd
  def unpack(q):return q[:-1],q[-1]
 z0=np.clip(z0,np.array(bounds)[:,0],np.array(bounds)[:,1])
 def const(q):
  x,t=unpack(q)
  res=[]
  for b,(p,f2,f3) in enumerate(g):
   xx=np.r_[x[:11],x[11+4*b:15+4*b]]
   res.extend(t-response(xx,p,k,ncoil));res.extend(response(xx,f2,k,ncoil)-target);res.extend(response(xx,f3,k,ncoil)-target)
  km=np.eye(4)
  for u,(a,b) in zip(x[4:10],COUPLES):km[a,b]=km[b,a]=u
  res.append(np.linalg.eigvalsh(km)[0]-.02)
  return np.array(res)
 t0=time.time()
 result=minimize(lambda q:q[-1],z0,bounds=bounds,method='SLSQP',constraints=[dict(type='ineq',fun=const)],options=dict(maxiter=maxiter,ftol=2e-9))
 x,t=unpack(result.x)
 mm=metrics(x,k,DENSE,ncoil)
 out={'IL':float(max(mm[:,0])),'H2':float(min(mm[:,1])),'H3':float(min(mm[:,2])),'perband':mm.tolist(),'x':x.tolist(),'k':k,'lone':float(x[10]),'leff':float(x[10]*(ncoil*(1+(ncoil-1)*k))),'qeff':float(12*(1+(ncoil-1)*k)),'success':bool(result.success),'iters':int(result.nit),'time':round(time.time()-t0,1),'target':target}
 return out

if __name__=='__main__':
 prev=json.load(open(root+'/stack_k_sensitivity.json'))
 seed=[v for v in prev if v['k']==.95][0]
 trials=[(2,.9),(2,.98),(3,.95),(4,.65),(4,.8),(4,.9),(5,.55),(5,.7),(5,.8),(5,.9),(6,.5),(6,.6),(6,.7),(6,.8)]
 out=[]
 for n,k in trials:
  init=seed['x'] if not out else (out[-1]['x'] if out[-1]['IL']<.35 else seed['x'])
  rr=opt(init,k,n,target=35.10,g=MED,maxiter=205)
  rr['nPCB']=n;out.append(rr)
  json.dump(out,open(root+'/pcb_stack_count_results.json','w'),indent=2)
  print('N',n,'K',k,'Qeq',rr['qeff'],'IL',round(rr['IL'],6),'H2',round(rr['H2'],3),'H3',round(rr['H3'],3),'LP',round(rr['lone'],3),'T',rr['time'],flush=True)
