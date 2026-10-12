#!/usr/bin/env python3
"""EXP-009 independent 9x9 MNA, 6-band 7001-per-interval RF numerical checks.
Checks candidate JSON independently of local nonconverged optimizers. No EM claim.
"""
import csv,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CASES=('B71','B12','B28','B13+B14','B26','B8')
N=7001

def nodevec(e):
 v=np.zeros(5)
 for n,s in zip(e,(1,-1)):
  if n>0:v[n-1]+=s
 return v

def evaluate(d,bands):
 assert d['phase']=='Phase 2' and d['chip_area_cost_units']==6
 cp=d['components'];assert cp['LQP02']['count']==4 and cp['GJM01']['count']==3 and cp['IC_VARIABLE_C']['count']==3
 top=d['topology'];Ls=top['inductors'];Cf=top['fixed_capacitors'];Cv=top['variable_capacitors']
 assert [p['id'] for p in Ls]==['L0','L1','L2','L3']
 L=np.array([c['L_nH'] for c in Ls])*1e-9;assert (L>=.4e-9).all() and (L<=56.000001e-9).all()
 indB=np.column_stack([nodevec(c['nodes']) for c in Ls]);K=np.eye(4);M=np.diag(L.astype(complex))
 order=[int(x[1:]) for x in top['physical_chip_row']]
 for i,k in enumerate(top['signed_adjacent_k']):
  assert abs(k)<=.40000001
  a,b=order[i:i+2];K[a,b]=K[b,a]=k;M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
 minK=np.linalg.eigvalsh(K).min();assert minK>0
 q_by_id=d.get('hypothetical_Q_by_inductor_id',{})
 q=np.array([q_by_id.get(c['id'],25) for c in Ls])
 base=np.diag(L/q)+1j*M
 reduced=indB@np.linalg.solve(base,indB.T)
 fixed=np.array([p['C_pF'] for p in Cf])*1e-12
 assert (fixed>0).all() and (fixed<=100e-12).all()
 all_edges=[nodevec(z['nodes']) for z in Cf+Cv]
 ports=np.zeros((5,5),complex);ports[0,0]=1/50;ports[2,2]=1/(60-40j)
 excite=np.array([1/50,0,0,0,0],complex)
 metrics=[];mna_checks=0;max_balance=0.;max_delta=0.
 assert set(d['variable_C_pf_by_setting'])==set(CASES)
 for case in CASES:
  var=np.array(d['variable_C_pf_by_setting'][case])*1e-12
  assert len(var)==3 and var.min()>=-1e-21 and var.max()<=4e-12+1e-21
  allC=np.r_[fixed,var]
  Ycap=sum((c/(1/80-1j))*np.outer(e,e) for c,e in zip(allC,all_edges))
  current=[]
  for regions in (('UL','DL'),('H2',),('H3',)):
   w=np.concatenate([np.linspace(float(row['low_mhz']),float(row['high_mhz']),N)*2*np.pi*1e6 for row in bands if row['case']==case and row['region'] in regions])
   adm=ports[None,:,:]+reduced[None,:,:]/w[:,None,None]+w[:,None,None]*Ycap[None,:,:]
   voltage=np.linalg.solve(adm,np.broadcast_to(excite,(len(w),5))[...,None])[...,0]
   IL=-10*np.log10(np.maximum(200*60/5200*np.abs(voltage[:,2])**2,1e-300))
   current.append(float(IL.max() if regions==('UL','DL') else IL.min()))
   for omega in (w[0],w[len(w)//2],w[-1]):
    A=np.block([[ports+omega*Ycap,indB],[-indB.T,omega*base]])
    vv=np.linalg.solve(A,np.r_[excite,np.zeros(4,complex)])
    node=vv[:5];curr=vv[5:]
    Y=ports+omega*Ycap+reduced/omega
    v0=np.linalg.solve(Y,excite)
    max_delta=max(max_delta,abs(v0[2]-node[2]))
    load=abs(node[2])**2*60/5200
    PL=np.real(np.vdot(curr,(omega*np.diag(L/q))@curr))
    PC=sum(abs(e@node)**2*np.real(omega*c/(1/80-1j)) for c,e in zip(allC,all_edges))
    reflect=abs(1-2*node[0])**2/200
    max_balance=max(max_balance,abs(.005-load-PL-PC-reflect))
    mna_checks+=1
  metrics.append(current)
 arr=np.array(metrics);ref=d['verified_dense_metrics'];observed=np.array([arr[:,0].max(),arr[:,1].min(),arr[:,2].min()]);expected=np.array([ref['worst_IL_db'],ref['min_H2_db'],ref['min_H3_db']])
 assert np.max(np.abs(observed-expected))<1e-6,(d['id'],observed,expected)
 assert arr[:,1:].min()>=30 and max_delta<1e-11 and max_balance<1e-12
 assert mna_checks==54
 return dict(id=d['id'],max_IL_db=float(observed[0]),H2_min_db=float(observed[1]),H3_min_db=float(observed[2]),
   min_K_eigenvalue=float(minK),max_MNA_voltage_difference_V=float(max_delta),
   max_MNA_power_balance_residual_W=float(max_balance),MNA_checks=mna_checks)

def main():
 bands=list(csv.DictReader((ROOT/'data'/'bands.csv').open(newline='')))
 for name in ('EXP010-01',):
  d=json.loads((HERE/(name+'.json')).read_text())
  print(json.dumps(evaluate(d,bands),sort_keys=True),flush=True)
if __name__=='__main__':main()