#!/usr/bin/env python3
"""EXP014 independent branch-current 9x9 MNA and dense nodal finite-grid validation.
Does not import optimizer. No rigorous frequency-continuum or physical Q/SRF claim.
"""
import json,csv,math,sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
HERE=Path(__file__).resolve().parent
ROOT=next((p for p in (HERE,*HERE.parents) if (p/'data/bands.csv').exists()),None)
assert ROOT is not None, 'missing data/bands.csv'
BANDS=list(csv.DictReader((ROOT/'data/bands.csv').open()))
CASES=('B71','B12','B28','B13+B14','B26','B8');N=7001

def inc(pair):
 v=np.zeros(5)
 for n,sign in zip(pair,(1,-1)):
  if n: v[int(n)-1]+=sign
 return v

def check(d):
 assert d['phase']=='Phase 2' and d['objective']=='full_lpf'
 assert d['components']['LQP02']=={'count':4,'Q':25}
 assert d['components']['IC_VARIABLE_C']['count']==2
 assert d['setting_order']==list(CASES)
 topo=d['topology'];inds=topo['inductors'];fixed=topo['fixed_capacitors'];tun=topo['variable_capacitors']
 assert len(inds)==4 and len(tun)==2
 L=np.array([z['L_nH'] for z in inds])*1e-9
 assert np.all((L>=.4e-9)&(L<=56e-9+1e-18))
 K=np.eye(4);M=np.diag(L)
 row=[int(z[1:]) for z in topo['physical_chip_row']]
 assert sorted(row)==list(range(4))
 for n,k in enumerate(topo['signed_adjacent_k']):
  assert abs(k)<=.4000000001
  i,j=row[n],row[n+1]
  K[i,j]=K[j,i]=k;M[i,j]=M[j,i]=k*math.sqrt(L[i]*L[j])
 mineig=float(np.linalg.eigvalsh(K).min());assert mineig>0
 B=np.column_stack([inc(z['nodes']) for z in inds]);Z=np.diag(L/25)+1j*M;YL=B@np.linalg.solve(Z,B.T)
 cap_branches=fixed+tun
 BC=[inc(z['nodes']) for z in cap_branches]
 Q=[int(z['Q']) for z in cap_branches]
 assert all(q==80 for q in Q[len(fixed):])
 assert all((q in (40,80)) for q in Q)
 assert all((.1<=z['C_pF']<=100 if z['Q']==80 else .02<=z['C_pF']<=.2) for z in fixed)
 assert 4+sum(z['Q']==80 for z in fixed)*2/3==d['chip_area_cost_units']
 fac=[1/(1/q-1j) for q in Q]
 P=np.zeros((5,5),complex);P[0,0]=.02;P[2,2]=1/(60-40j)
 rhs=np.array([.02,0,0,0,0],complex)
 all_by=[];extremes=[];residual=[];voltage_diff=[];max_IL_mna_diff=0.;point_count=0
 for case in CASES:
  cc=np.array([z['C_pF'] for z in fixed]+d['variable_C_pf_by_setting'][case])*1e-12
  assert all(0<=z<=4 for z in d['variable_C_pf_by_setting'][case]); assert len(cc)==len(cap_branches)
  capY=sum(c*f*np.outer(v,v) for c,f,v in zip(cc,fac,BC))
  group=[];group_ext=[]
  for g,regs in enumerate((('UL','DL'),('H2',),('H3',))):
   found=[];bound=[];segments=[]
   for b in [b for b in BANDS if b['case']==case and b['region'] in regs]:
    F=np.linspace(float(b['low_mhz']),float(b['high_mhz']),N);w=F*2*np.pi*1e6
    A=P[None,:,:]+YL[None,:,:]/w[:,None,None]+w[:,None,None]*capY[None,:,:]
    V=np.linalg.solve(A,np.broadcast_to(rhs,(len(F),5))[...,None])[...,0]
    il=-10*np.log10(np.maximum((200*60/5200)*abs(V[:,2])**2,1e-300))
    idx=int(np.argmax(il) if g==0 else np.argmin(il));found.append((float(il[idx]),float(F[idx])))
    def il_at(f):
     om=2*np.pi*1e6*f
     volt=np.linalg.solve(P+YL/om+om*capY,rhs)[2]
     return float(-10*np.log10(max((200*60/5200)*abs(volt)**2,1e-300)))
    a,c=F[max(0,idx-1)],F[min(N-1,idx+1)]
    if c>a:
     opt=minimize_scalar((lambda f:-il_at(f)) if g==0 else il_at,bounds=(a,c),method='bounded',options={'xatol':1e-9})
     value=il_at(opt.x)
    else:value=float(il[idx])
    bound.append(max(float(il[idx]),value) if g==0 else min(float(il[idx]),value))
    segments.append(F)
   v,critical=(max(found) if g==0 else min(found))
   group.append({'value_db':v,'critical_MHz':critical});group_ext.append(max(bound) if g==0 else min(bound))
   F=np.concatenate(segments)
   for f in (F[0],F[len(F)//2],F[-1],critical):
    om=f*2*np.pi*1e6
    A=np.block([[P+om*capY,B],[-B.T,om*Z]])
    solution=np.linalg.solve(A,np.r_[rhs,np.zeros(4,complex)])
    V,I=solution[:5],solution[5:]
    vnod=np.linalg.solve(P+YL/om+om*capY,rhs)
    voltage_diff.append(float(np.max(abs(vnod-V))))
    Pload=abs(V[2])**2*60/5200
    PL=float(np.real(np.vdot(I,(om*np.diag(L/25))@I)))
    PC=float(sum(abs(vec@V)**2*np.real(om*c*factor) for c,factor,vec in zip(cc,fac,BC)))
    Pref=abs(1-2*V[0])**2/200
    residual.append(abs(.005-Pload-PL-PC-Pref));point_count+=1
  all_by.append(group);extremes.append(group_ext)
 arr=np.array([[x['value_db'] for x in z] for z in all_by]);e=np.array(extremes)
 worst=[float(arr[:,0].max()),float(arr[:,1].min()),float(arr[:,2].min())]
 ex=[float(e[:,0].max()),float(e[:,1].min()),float(e[:,2].min())]
 assert point_count==72 and max(residual)<1e-12 and max(voltage_diff)<1e-10
 assert max(abs(np.array(worst)-np.array(ex)))<1e-5
 assert worst[1]>=30 and worst[2]>=30
 return {'id':d['id'],'worst_IL_db':worst[0],'min_H2_db':worst[1],'min_H3_db':worst[2],'frequency_extremum_checked':ex,'by_setting':{name:grp for name,grp in zip(CASES,all_by)},'samples_per_individual_frequency_interval':N,'independent_9x9_MNA_points':point_count,'max_power_balance_residual_W':max(residual),'max_MNA_voltage_discrepancy_V':max(voltage_diff),'min_K_eigenvalue':mineig,'meets_IL_0p3_and_H2H3_30':bool(worst[0]<=.3 and worst[1]>=30 and worst[2]>=30),'phase3_authorized':False,'real_component_Qf_or_EM_verified':False,'global_optimality_proven':False}

def main():
 for id in ('EXP014-01','EXP014-02','EXP014-03','EXP014-C4-01'):
  fn=HERE/(id+'.json');d=json.loads(fn.read_text())
  result=check(d)
  d['verification']=result
  fn.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
  print(id,'IL',result['worst_IL_db'],'H2',result['min_H2_db'],'H3',result['min_H3_db'],'MNA',result['max_power_balance_residual_W'],flush=True)
if __name__=='__main__':main()