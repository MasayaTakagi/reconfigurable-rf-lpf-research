import os, json, time, sys, numpy as np
from scipy.optimize import minimize
from coupled_study import x0, tr, evaluate, get_psd, SMALL, MED, DENSE, NAMES, P_PAIRS
root=os.path.dirname(os.path.abspath(__file__))

def opt_global(kmax, init=None, grid=SMALL, iters=135, target=35.05, fixed_L=True, enforce_two=False):
 # vary all C, PCB-PCB mutual k, and optionally all L and all chip couplings
 z0=np.r_[np.zeros(3),x0[16:]] if init is None else np.r_[init['k'],np.array(init['x'])[16:]]
 if not fixed_L:
  z0=np.r_[z0, x0[:16]] if init is None else np.r_[z0, np.array(init['x'])[:16]]
 ndim=len(z0)
 z0=np.r_[z0,max(evaluate(x0,np.zeros(3),SMALL)[:,0])]
 if fixed_L:
  bounds=[(-kmax,kmax)]*3+[(.1,100)]*42+[(0,1.8)]
 else:
  kb=[(-.16,.16)]*6;kb[2]=(-.25,.25);kb[3]=(-.25,.25)
  bounds=[(-kmax,kmax)]*3+[(.1,100)]*42+[(.4,27)]*4+kb+[(.1,3)]*3+[(-.03,.03)]*3+[(0,1.8)]
 def unpack(z):
  # z = kpp (3), Cs (42), (physical first 16), t (1)
  k=z[:3]
  x=np.r_[x0[:16] if fixed_L else z[45:61],z[3:45]]
  return x,k,z[-1]
 def con(z):
  x,k,t=unpack(z)
  a=[]
  for j,(p,s,h) in enumerate(grid):
   xx=x[np.r_[:16,16+7*j:16+7*(j+1)]]
   a.extend(t-tr(xx,k,p)); a.extend(tr(xx,k,s)-target); a.extend(tr(xx,k,h)-target)
  a.append(get_psd(x,k)-.03)
  return np.asarray(a)
 t=time.monotonic()
 res=minimize(lambda z:z[-1],z0,method='SLSQP',bounds=bounds,constraints=[dict(type='ineq',fun=con)],options=dict(maxiter=iters,ftol=1e-8,disp=False))
 x,k,tub=unpack(res.x)
 v=evaluate(x,k,DENSE)
 out={'k':k.tolist(),'x':x.tolist(),'maxIL':float(max(v[:,0])),'minH2':float(min(v[:,1])),'minH3':float(min(v[:,2])),'t':float(tub),'satisfies35':bool(min(v[:,1].min(),v[:,2].min())>=35.0),'target':target,'kmax':kmax,'psd':float(get_psd(x,k)),'success':bool(res.success),'nit':int(res.nit),'elapsed':round(time.monotonic()-t,2),'fixed_L':fixed_L,'grid_size':len(grid[0][0]),'band_metrics':v.tolist(),'message':res.message}
 return out

if __name__=='__main__':
 init=None
 for kmax in (.1,.2,.3):
  r=opt_global(kmax,grid=SMALL,iters=155,init=init,target=35.05,fixed_L=True)
  print('fix',kmax,'IL',r['maxIL'],'H2',r['minH2'],'H3',r['minH3'],'k',r['k'],'PSD',r['psd'],'suc',r['success'],'secs',r['elapsed'],flush=True)
  json.dump(r,open(root+f'/fixed_{kmax}.json','w'),indent=2)
  init=r
 for km in (.2,.3):
  prev=json.load(open(root+f'/fixed_{km}.json'))
  r=opt_global(km,init=prev,grid=SMALL,iters=190,target=35.05,fixed_L=False)
  print('full',km,'IL',r['maxIL'],'H2',r['minH2'],'H3',r['minH3'],'k',r['k'],'PSD',r['psd'],'suc',r['success'],'secs',r['elapsed'],flush=True)
  json.dump(r,open(root+f'/full_{km}.json','w'),indent=2)
