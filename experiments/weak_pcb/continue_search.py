import sys,os,json,numpy as np,time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from weak_search import opt, NAMES, SMALL,MED,DENSE
p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'results.json'); history=json.load(open(p)); best=min((j for j in history if j['good']),key=lambda j:j['IL'])
print('START',best['IL'],best['edges'],best['cp'],flush=True)

def extend(prev,newedge=None,newce=None):
 x=np.asarray(prev['x']);np0=len(prev['edges']);ne0=len(prev['extraC']);D0=4+np0+ne0
 xx=np.r_[x[:10],x[10:10+np0], [2.5] if newedge is not None else [],x[10+np0:10+2*np0],[0] if newedge is not None else []]
 xx=np.r_[xx,np.array([np.r_[x[10+2*np0+i*D0:10+2*np0+i*D0+4+np0],[0.1] if newedge is not None else [],x[10+2*np0+i*D0+4+np0:10+2*np0+(i+1)*D0],[.1] if newce is not None else []] for i in range(6)]).ravel()]
 return xx

def go(edges,cp,ces=(),init=None,grid=SMALL,maxiter=180):
 r=opt(edges,cp,ces,initial=init,grid=grid,maxiter=maxiter)
 history.append(r);json.dump(history,open(p,'w'),indent=2)
 print('RUN',len(history),'edges',edges,'cp',cp,'C',ces, 'IL',round(r['IL'],6),'H2',round(r['H2'],3),'H3',round(r['H3'],3),'ok',r['good'],'t',r['time'],flush=True)
 return r

if __name__=='__main__':
 candidate=next((z for z in history if z['edges']==[[1,-1]] and z['good']),best)
 for ci in (0,2,3):go([[1,-1]],[ci],init=np.array(candidate['x']),maxiter=120)
 for ec in [(0,2),(0,3),(1,3),(0,-1),(1,-1),(2,-1)]:
  go([[1,-1]],candidate['cp'],[ec],init=extend(candidate,newce=ec),maxiter=150)
 for nd,ci in [((2,-1),2),((0,2),0),((2,3),2),((1,-1),3),((0,1),0),((1,2),2)]:
  go([[1,-1],list(nd)],[candidate['cp'][0],ci],init=extend(candidate,newedge=nd),maxiter=180)
 feasible=sorted((r for r in history if r['good']),key=lambda r:r['IL'])
 for r in feasible[:3]:
  go(r['edges'],r['cp'],r['extraC'],init=np.array(r['x']),grid=MED,maxiter=260)
 print('BEST',[(round(z['IL'],6),z['edges'],z['cp'],z['extraC']) for z in sorted([z for z in history if z['good']],key=lambda z:z['IL'])[:12]],flush=True)
