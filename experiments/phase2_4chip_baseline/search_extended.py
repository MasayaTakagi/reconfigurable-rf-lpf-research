import os,sys,json,itertools,time,traceback
import numpy as np
from scipy.optimize import minimize
sys.path[:0]=['/mnt/data/lpf_next','/mnt/data/lpf_limit_study']
from explore import *
OUT='/mnt/data/lpf_phase2_extension';Q=np.array([25.,25.,25.,25.,80.]); ATT=35.05
old=json.load(open('/mnt/data/lpf_limit_study/two_pair_best_refined.json'))
new=json.load(open(OUT+'/first.json'))
strongbase=json.load(open('/mnt/data/lpf_next/target.json'))
s0=np.array(new['x']);s35=np.array(next(q['x'] for q in strongbase if q.get('label')=='allpolish35'))
# x = 4 L, 6 k, 24 C
# stage select sparse 4pt per band, medium 6, verify 41
STAGE=MED

def search(x0,top,pair=(2,3),maxiter=190,atten=ATT,stage=STAGE):
 bd=[(.4,27.)]*4+[(-.25,.25) if i in pair else (-.16,.16) for i in range(6)]+[(.1,100.)]*24
 x=np.clip(np.asarray(x0,dtype=float),np.array(bd)[:,0],np.array(bd)[:,1]);
 z=np.r_[x,max(.3,evaluation(x,top,Q,SMALL)['IL'])]
 def cons(zz):
  x=zz[:-1]; t=zz[-1]; arr=[]
  for i,(fp,f2,f3) in enumerate(stage):
   xi=np.r_[x[:4],x[10+4*i:14+4*i],x[4:10]]
   pp=transfer(xi,fp,*top,Q);hh2=transfer(xi,f2,*top,Q);hh3=transfer(xi,f3,*top,Q)
   arr.extend(t-pp);arr.extend(hh2-atten);arr.extend(hh3-atten)
  arr.append(psd(x[4:10])-.01)
  return np.array(arr)
 t0=time.time()
 try:
  res=minimize(lambda z:z[-1],z,method='SLSQP',bounds=bd+[(0,3)],constraints=[dict(type='ineq',fun=cons)],options=dict(maxiter=maxiter,ftol=1e-8))
  x=res.x[:-1]; v=evaluation(x,top,Q,DENSE)
  # real feasible with margin 0.015 dB and PSD
  feasible=(v['IL']<=res.x[-1]+.025 and v['H2']>=atten-.015 and v['H3']>=atten-.015 and psd(x[4:10])>=.009)
  return dict(IL=v['IL'],H2=v['H2'],H3=v['H3'],feasible=bool(feasible),x=x.tolist(),PSDm=psd(x[4:10]),time=round(time.time()-t0,2),success=bool(res.success),message=str(res.message),iter=int(res.nit),perband=v['perband'],slack=float(min(v['H2'],v['H3'])-atten))
 except Exception as e:
  return dict(IL=99,H2=0,H3=0,feasible=False,error=str(e),time=round(time.time()-t0,2))

def prep(name,top,pairs,seeds,maxiter):
 result=None
 for pair in pairs:
  bestp=None
  for seedname,seed in seeds:
   r=search(seed,top,pair,maxiter=maxiter)
   r.update(topology=name,pair=list(pair),seed=seedname)
   add(r)
   if r['feasible'] and (bestp is None or r['IL']<bestp['IL']):bestp=r
  if bestp and (result is None or bestp['IL']<result['IL']):result=bestp
 return result

hist=[];t0=time.time()
def add(r):
 hist.append(r)
 print('RUN',len(hist),r['topology'],''.join(str(j) for j in r['pair']),r['seed'], 'IL',round(r['IL'],6),'H2/H3',round(r['H2'],4),round(r['H3'],4),'feas',r['feasible'],'sec',r['time'],flush=True)
 if len(hist)%4==0:json.dump(hist,open(OUT+'/search_results.json','w'),indent=1)

if __name__=='__main__':
 # first 15 main-pair options for current topology, warm-start from full baseline and boundary adapted
 main=three_series(2)
 print('START current best',new['IL'],flush=True)
 for pair in itertools.combinations(range(6),2):
  x0=np.array(s0);x1=s35.copy()
  best=prep('3series_middle',main,[pair],[('updated',x0),('old',x1)] if pair==(2,3) else [('updated',x0)],maxiter=140)
 # shunt alternative positions
 for pos in [0,1,3]:
  prior=json.load(open('/mnt/data/lpf_next/batch.json'))
  ss=[(d['IL'],d) for d in prior if d['label']==f'3series_shunt{pos}' and d['target']==35.05]
  ss=sorted(ss,key=lambda e:e[0]);seeds=[('existing',np.array(ss[0][1]['x']))] if ss else [('updated',s0)]
  seeds.append(('updated',s0))
  for pair in [(2,3),(0,3),(2,5)]:prep(f'3series_shunt{pos}',three_series(pos),[pair],seeds,120)
 # alternate 2series 2shunt placement, with extra spare C? each series C in parallel, both shunts series C
 for nodes in [(0,1),(0,2),(1,1),(1,2),(2,2)]:
  for pair in [(2,3),(0,3)]:
   prep(f'2series_nodes{nodes}',two_series(shunts=nodes),[pair],[('old',s0)],120)
 # bridge with C replaced; 3series middle, capacitance edges to non-local nodes
 base={0:(0,1),3:(1,2),2:(2,3)}
 for ci in [0,3,2]:
  for edge in [(0,2),(0,3),(1,3)]:
   ce=base.copy();ce[ci]=edge
   for pair in [(2,3),(0,3)]:
    prep(f'bridge_C{ci+1}_{edge}',three_series(2,ce),[pair],[('old',s0)],120)
 # format
 json.dump(hist,open(OUT+'/search_results.json','w'),indent=1)
 f=sorted([r for r in hist if r['feasible']],key=lambda r:r['IL'])
 print('BEST',[(round(r['IL'],6),r['topology'],r['pair']) for r in f[:15]],'TOTAL',len(hist),'seconds',round(time.time()-t0,1),flush=True)
