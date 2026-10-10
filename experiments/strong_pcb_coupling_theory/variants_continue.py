import os, sys, time, json, itertools
import numpy as np
from scipy.optimize import minimize
from dynamic import tr, getB, get_psd, SMALL, MED, DENSE, NAMES, P_PAIRS, REF, PRIOR, x0
root=os.path.dirname(os.path.abspath(__file__))

# optimized coupled-L numerics per topology

def get_psd3(x,kpp,cp):
 kk=x[4:10];kp=x[13:16]; coupl=np.array([(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)])
 A=np.eye(7)
 for v,(a,b) in zip(kk,coupl):A[a,b]=A[b,a]=v
 for i in range(3):A[4+i,cp[i]]=A[cp[i],4+i]=kp[i]
 for v,(a,b) in zip(kpp,P_PAIRS):A[4+a,4+b]=A[4+b,4+a]=v
 return np.linalg.eigvalsh(A)[0]

def eval3(x,k,edges,cp,grid=DENSE):
 B=getB(edges);cp=np.array(cp,np.int64);t=[]
 for i,(p,s,h) in enumerate(grid):
  xx=np.r_[x[:16],x[16+7*i:16+7*(i+1)]]
  t.append([max(tr(xx,k,p,B,cp)),min(tr(xx,k,s,B,cp)),min(tr(xx,k,h,B,cp))])
 return np.asarray(t)

def get_seed(edges,cp):
 rec=[r for r in PRIOR if r['edges']==edges and r['cp']==list(cp) and len(r['extraC'])==0]
 if rec:
  r=min(rec,key=lambda q:abs(q['H2']-35.05)+abs(q['H3']-35.05)+10*max(0,q['IL']-.6));return np.asarray(r['x']).copy()
 return x0.copy()

def opt(edges,cp,km=.2,seed=None,grid=SMALL,maxiter=170,fix=False):
 B=getB(edges);cp=np.asarray(cp,np.int64)
 start=get_seed(edges,cp) if seed is None else np.asarray(seed['x'] if isinstance(seed,dict) else seed).copy()
 ks=np.zeros(3) if seed is None else np.asarray(seed['k']).copy()
 z0=np.r_[ks,start[16:],start[:16]] if not fix else np.r_[ks,start[16:]]
 z0=np.r_[z0,max(eval3(start,ks,edges,cp,SMALL)[:,0])]
 kb=[(-.16,.16)]*6;kb[2]=(-.25,.25);kb[3]=(-.25,.25)
 bounds=[(-km,km)]*3+[(.1,100)]*42
 if not fix: bounds+=[(.4,27)]*4+kb+[(.1,3)]*3+[(-.03,.03)]*3
 bounds+=[(0,2)]
 z0=np.clip(z0,np.array(bounds)[:,0],np.array(bounds)[:,1])
 def unpack(z):
  kk=z[:3]
  zz=np.r_[start[:16] if fix else z[45:61],z[3:45]]
  return zz,kk,z[-1]
 def cons(z):
  xx,kk,t=unpack(z)
  out=[]
  for i,(p,s,h) in enumerate(grid):
   local=np.r_[xx[:16],xx[16+7*i:16+7*(i+1)]]
   out.extend(t-tr(local,kk,p,B,cp));out.extend(tr(local,kk,s,B,cp)-35.05);out.extend(tr(local,kk,h,B,cp)-35.05)
  out.append(get_psd3(xx,kk,cp)-.02)
  return np.asarray(out)
 t0=time.monotonic();res=minimize(lambda z:z[-1],z0,method='SLSQP',bounds=bounds,constraints=[dict(type='ineq',fun=cons)],options=dict(maxiter=maxiter,ftol=1e-8))
 xx,kk,t=unpack(res.x);rr=eval3(xx,kk,edges,cp,DENSE)
 out=dict(edges=edges,cp=cp.tolist(),x=xx.tolist(),k=kk.tolist(),IL=float(max(rr[:,0])),H2=float(min(rr[:,1])),H3=float(min(rr[:,2])),psd=float(get_psd3(xx,kk,cp)),t=float(t),success=bool(res.success),iter=res.nit,time=round(time.monotonic()-t0,2),fix=fix,km=km,metrics=rr.tolist(),message=res.message)
 out['good']=bool(out['H2']>=35.0 and out['H3']>=35.0 and out['psd']>.0199)
 return out

if __name__=='__main__':
 E=[[[1,-1],[2,3],[0,2]],
    [[1,-1],[2,3],[1,2]],
    [[1,-1],[2,3],[0,3]],
    [[1,-1],[2,3],[1,3]],
    [[1,-1],[0,2],[1,3]],
    [[1,-1],[0,2],[2,3]],
    [[1,-1],[1,3],[0,2]],
    [[2,-1],[0,2],[2,3]],
    [[2,-1],[0,2],[1,3]],
    [[1,-1],[2,-1],[0,2]],
    [[1,-1],[2,-1],[1,3]],
    [[2,-1],[2,3],[0,2]],
    [[1,-1],[2,3],[0,1]],
    [[0,-1],[2,3],[0,2]],
    [[1,-1],[2,3],[2,-1]],
    [[1,-1],[2,3],[3,-1]]]
 cps=[[1,2,0],[1,2,3],[1,2,0],[1,2,3],[1,0,3],[1,0,2],[1,3,0],[2,0,3],[2,0,3],[1,2,0],[1,2,3],[2,3,0],[1,2,0],[0,2,0],[1,2,2],[1,2,2]]
 allr=json.load(open(root+'/topology_results.json'));log=root+'/topology_log.csv'
 with open(log,'a') as f:
  pass
 for j,(edges,cp) in list(enumerate(zip(E,cps)))[9:]:
  r=opt(edges,cp,.2,maxiter=125,fix=False)
  allr.append(r)
  with open(log,'a') as f:f.write(f'{j},"{edges}","{cp}",{r["IL"]},{r["H2"]},{r["H3"]},{r["psd"]},{r["good"]},{r["time"]}\n')
  json.dump(allr,open(root+'/topology_results.json','w'),indent=2)
  print('t',j,'IL',round(r['IL'],6),'H2',round(r['H2'],3),'H3',round(r['H3'],3),'good',r['good'],'k',np.round(r['k'],3),'time',r['time'],flush=True)
 print('TOP',[(q['IL'],q['edges'],q['good']) for q in sorted(allr,key=lambda a:a['IL'])[:7]],flush=True)
