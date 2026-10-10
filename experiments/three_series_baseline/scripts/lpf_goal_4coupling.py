"""Topology + four-coil pairwise mutual inductance sensitivity; numerical only."""
import sys,os,json,time
import numpy as np
from numba import njit
from scipy.optimize import minimize
sys.path.insert(0,'/mnt/data')
import lpf_reexplore as E
COUPLES=np.array([(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)],dtype=np.int64)
@njit(cache=True)
def transfer(x,ff,B,ser,edges,Q):
 L=x[:4]; C=x[4:8];k=x[8:14]; n=B.shape[1]
 out=np.zeros(len(ff))
 for ii in range(len(ff)):
  w=2*np.pi*ff[ii]*1e6
  zz=np.zeros((4,4),dtype=np.complex128)
  for j in range(4):
   zz[j,j]=w*L[j]*1e-9*(1j+1/Q[j])
   if ser[j]:zz[j,j]+=(1/Q[4]-1j)/(w*C[j]*1e-12)
  for j in range(6):
   a=COUPLES[j,0];b=COUPLES[j,1]
   z=1j*w*k[j]*np.sqrt(L[a]*L[b])*1e-9
   zz[a,b]=z;zz[b,a]=z
  yy=B.T@np.linalg.solve(zz,B)
  for j in range(edges.shape[0]):
   c=int(edges[j,0]); a=int(edges[j,1]);b=int(edges[j,2]);y=1/((1/Q[4]-1j)/(w*C[c]*1e-12))
   if a>=0:yy[a,a]+=y
   if b>=0:yy[b,b]+=y
   if a>=0 and b>=0:yy[a,b]-=y;yy[b,a]-=y
  yy[0,0]+=1/50
  yy[n-1,n-1]+=1/(60-40j)
  rhs=np.zeros(n,dtype=np.complex128);rhs[0]=1/50
  volt=np.linalg.solve(yy,rhs)
  eta=4*50*(60/5200)*abs(volt[n-1])**2
  out[ii]=-10*np.log10(max(eta,1e-100))
 return out

def topo(s2='i',s3='m',c1='a',c4='b'):
 n=3; S={'i':0,'m':1,'o':2}; C={'i':(0,-1),'m':(1,-1),'o':(2,-1),'a':(0,1),'b':(1,2),'x':(0,2)}
 pairs=[(0,1),(S[s2],-1),(S[s3],-1),(1,2)]
 B=np.zeros((4,n),np.complex128)
 for j,(a,b) in enumerate(pairs):
  if a>=0:B[j,a]+=1
  if b>=0:B[j,b]-=1
 return (B,np.array([0,1,1,0],dtype=np.bool_),np.array([(0,*C[c1]),(3,*C[c4])],dtype=np.int64))

def evaluate(v,top,Q,points=E.DENSE):
 B,ser,edges=top;il=0;h2=100;h3=100;by=[]
 for i,(fp,f2,f3) in enumerate(points):
  x=np.r_[v[:4],v[10+4*i:14+4*i],v[4:10]]
  p=transfer(x,fp,B,ser,edges,Q);z2=transfer(x,f2,B,ser,edges,Q);z3=transfer(x,f3,B,ser,edges,Q)
  ii=float(max(p));hh2=float(min(z2));hh3=float(min(z3))
  il=max(il,ii);h2=min(h2,hh2);h3=min(h3,hh3)
  by.append(dict(band=E.NAMES[i],IL=ii,H2=hh2,H3=hh3))
 return dict(IL=il,H2=h2,H3=h3,bands=by)

def optimize(v0,top,Q,kbounds,atten=35.05,cmin=.1,cmax=8.,iter=135,refine=False):
 bd=[(.5,27)]*4+kbounds+[(cmin,cmax)]*24
 x=np.clip(np.array(v0),np.array(bd)[:,0],np.array(bd)[:,1]); t0=time.time()
 x=np.r_[x,max(0.5,evaluate(x,top,Q,E.SMALL)['IL'])]
 pts=E.MED if refine else E.SMALL
 def constr(z):
  out=[];B,ser,edges=top
  for i,(fp,f2,f3) in enumerate(pts):
   xx=np.r_[z[:4],z[10+4*i:14+4*i],z[4:10]]
   p=transfer(xx,fp,B,ser,edges,Q)
   h2=transfer(xx,f2,B,ser,edges,Q)
   h3=transfer(xx,f3,B,ser,edges,Q)
   out.extend(z[-1]-p);out.extend(h2-atten);out.extend(h3-atten)
  return np.asarray(out)
 try:
  r=minimize(lambda z:z[-1],x,bounds=bd+[(0,5)],method='SLSQP',constraints=[dict(type='ineq',fun=constr)],options=dict(maxiter=iter,ftol=2e-8))
  mm=evaluate(r.x[:-1],top,Q,E.DENSE)
  mm.update(x=r.x[:-1].tolist(),valid=bool(mm['H2']>=atten-.018 and mm['H3']>=atten-.018 and np.min(constr(r.x))>-.020),nit=r.nit,sec=round(time.time()-t0,2),success=bool(r.success))
  return mm
 except Exception as ex: return dict(IL=99,valid=False,err=str(ex))

def old2new(v):
 return np.r_[v[:4],v[8],v[9],0.,v[10],0.,0.,v[11:]]

def run():
 prev=json.load(open('/mnt/data/lpf_goal_033_probe.json'))
 seed=next(a for a in prev if a['atten']==35.05 and a['cmin']==.1)
 x0=old2new(seed['x']);Q=np.array([25.,25.,25.,25.,80.])
 patterns=[('i','m','a','b'),('i','o','a','b'),('m','o','a','b'),('i','m','x','b'),('i','m','a','x'),('i','m','x','m'),('i','o','a','x'),('i','m','i','b')]
 # Strong coupling pair options: [02] one primary, [01,02] double strong, [02,03] series+shunt, [02,23] series 4 with shunt 3, [02,12] two shunts
 pairs=[('one',[1]),('fork',[0,1]),('serial',[1,2]),('other',[1,5]),('shunt',[1,3]),('L4_shunt',[1,4])]
 os.makedirs('/mnt/data/lpf_goal',exist_ok=True)
 out=[]
 for ti,pp in enumerate(patterns):
  tp=topo(*pp)
  for st,active in pairs:
   bounds=[(-.03,.03)]*6
   for j in active:bounds[j]=(-.25,.25)
   for att in [35.05,30.5]:
    s=x0.copy();s[4:10]=np.clip(s[4:10],[x[0] for x in bounds],[x[1] for x in bounds]);
    m=optimize(s,tp,Q,bounds,atten=att,cmin=.1,iter=120)
    item={'topology':'_'.join(pp),'coupling':st,'atten':att,**m};out.append(item)
    if m['valid'] and m['IL']<.350: print('PROMISING',ti,pp,st,att,m['IL'],m['H2'],m['H3'],flush=True)
    if m['valid'] and m['IL']<.33 and att>=35: print('GOAL_HIGH_MARGIN',item,flush=True)
    if len(out)%12==0:
     print('PROGRESS',len(out),'best35',[(x['topology'],x['coupling'],round(x['IL'],5)) for x in sorted((y for y in out if y['atten']==35.05 and y['valid']),key=lambda v:v['IL'])[:4]],flush=True)
     json.dump(out,open('/mnt/data/lpf_goal/4coil.json','w'),indent=1)
  
 json.dump(out,open('/mnt/data/lpf_goal/4coil.json','w'),indent=1)
 print('TOP',[(x['topology'],x['coupling'],x['atten'],round(x['IL'],5)) for x in sorted((y for y in out if y['valid']),key=lambda v:v['IL'])[:15]],flush=True)

if __name__=='__main__':run()
