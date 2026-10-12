#!/usr/bin/env python3
"""Sensitivity ONLY: retune all three C values by setting for hypothetical fixed Q(L1).
L/C/k remain from EXP009-01 and no SRF/parasitics. NOT a manufactured model.
"""
import json, csv, numpy as np
from scipy.optimize import minimize
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CASES=('B71','B12','B28','B13+B14','B26','B8')
bands=list(csv.DictReader((ROOT/'data/bands.csv').open(newline='')))
def pairs(case,regions):
 return [(float(z['low_mhz']),float(z['high_mhz'])) for z in bands if z['case']==case and z['region'] in regions]
DATA=[(case,pairs(case,('UL','DL')),pairs(case,('H2',)),pairs(case,('H3',))) for case in CASES]
ref=json.loads((HERE/'EXP009-01.json').read_text())
T=ref['topology'];L=np.array([c['L_nH'] for c in T['inductors']])*1e-9
B=np.zeros((5,4))
def vect(e):
 v=np.zeros(5)
 for a,s in zip(e,(1,-1)):
  if a>0:v[a-1]+=s
 return v
for i,ind in enumerate(T['inductors']):B[:,i]=vect(ind['nodes'])
Cfixed=[float(z['C_pF']) for z in T['fixed_capacitors']]
Cedges=[vect(z['nodes']) for z in T['fixed_capacitors']]
Vedges=[vect(z['nodes']) for z in T['variable_capacitors']]
M=np.diag(L.astype(complex));order=[int(z[1:]) for z in T['physical_chip_row']]
for i,k in enumerate(T['signed_adjacent_k']):
 a,b=order[i:i+2];M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
ports=np.zeros((5,5),complex);ports[0,0]=1/50;ports[2,2]=1/(60-40j)
src=np.array([1/50,0,0,0,0],complex)
class Retune:
 def __init__(self,Q):
  self.Q=Q;self.inv=B@np.linalg.solve(np.diag(L/np.array(Q))+1j*M,B.T)
  self.cf=sum((c*1e-12/(1/80-1j))*np.outer(e,e) for c,e in zip(Cfixed,Cedges))
  self.vb=np.array([np.outer(e,e)*1e-12/(1/80-1j) for e in Vedges])
  self.cache={}
 def grids(self,N):
  if N not in self.cache:
   self.cache[N]=[[np.concatenate([np.linspace(a,b,N)*2*np.pi*1e6 for a,b in rg]) for rg in [pb,h2,h3]] for _,pb,h2,h3 in DATA]
  return self.cache[N]
 def metric(self,ci,C,N):
  admC=self.cf+np.einsum('i,ijk->jk',C,self.vb)
  out=[]
  for j,w in enumerate(self.grids(N)[ci]):
   A=ports[None,:,:]+self.inv[None,:,:]/w[:,None,None]+w[:,None,None]*admC[None,:,:]
   v=np.linalg.solve(A,np.broadcast_to(src,(len(w),5))[...,None])[...,0]
   at=-10*np.log10(200*60/5200*np.abs(v[:,2])**2)
   out.append(float(at.max() if j==0 else at.min()))
  return out
 def optimize(self,ci,target=30.02,N=71):
  c0=np.array(ref['variable_C_pf_by_setting'][CASES[ci]])
  results=[]
  for scale in [0,.04,.12]:
   rng=np.random.default_rng(20261012+ci+int(1000*scale))
   ini=np.clip(c0+rng.normal(0,scale,3),0,4)
   def cons(v):
    v0=self.metric(ci,v[:3],N)
    return np.array([v[-1]-v0[0],v0[1]-target,v0[2]-target])
   x0=np.r_[ini,max(.5,self.metric(ci,ini,N)[0])]
   ans=minimize(lambda z:z[-1],x0,method='SLSQP',bounds=[(0,4)]*3+[(0,3)],
           constraints=[{'type':'ineq','fun':cons}],options={'maxiter':300,'ftol':1e-10})
   met=self.metric(ci,ans.x[:3],7001)
   results.append({'C_pF':ans.x[:3].tolist(),'IL':met[0],'H2':met[1],'H3':met[2],'success':ans.success,'iters':ans.nit})
  valid=[z for z in results if min(z['H2'],z['H3'])>=30-1e-7]
  return min(valid,key=lambda z:z['IL']) if valid else sorted(results,key=lambda z:min(z['H2'],z['H3']),reverse=True)[0]

out={}
for q in [22,19,16]:
 model=Retune([25,q,25,25]);res=[]
 for i,c in enumerate(CASES):
  j=model.optimize(i,target=30.02,N=71)
  res.append(j);print('Q_L1',q,c,'IL',round(j['IL'],5),'H2',round(j['H2'],5),'H3',round(j['H3'],5),flush=True)
 info={'Q_L1':q,'case_map':dict(zip(CASES,res)),'worstIL':max(z['IL'] for z in res),'H2min':min(z['H2'] for z in res),'H3min':min(z['H3'] for z in res),'all_valid':all(min(z['H2'],z['H3'])>=30-1e-7 for z in res)}
 out[str(q)]=info;(HERE/'q_retune_reproduction.json').write_text(json.dumps(out,indent=2))
 print('SUMMARY',q,info['worstIL'],info['H2min'],info['H3min'],info['all_valid'],flush=True)