#!/usr/bin/env python3
"""Independent mixed L/C/Q 9x9 branch-current MNA, 7001 points per subband (Phase2).
Candidates EXP011-01/02: Q25 inductors, Q80 GJM, Q80 variable IC Cs.
Not an interval guarantee, EM/physical result, or certification of global optimization.
"""
import csv,json,argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
HERE=Path(__file__).resolve().parent
with (HERE.parents[3]/'data/bands.csv').open(newline='') as band_file:
 BANDS=list(csv.DictReader(band_file))
CASES=('B71','B12','B28','B13+B14','B26','B8')
def vedge(ab):
 v=np.zeros(5)
 for i,s in zip(ab,(1,-1)):
  if i:v[i-1]+=s
 return v

def analyze(d,grid=7001,require=True):
 assert d['phase']=='Phase 2' and d['objective']=='full_lpf'
 assert d['components']['LQP02']['Q']==25
 assert d['components']['IC_VARIABLE_C']['Q']==80 and d['components']['IC_VARIABLE_C']['count']==3
 assert d['components']['GJM01']['Q']==80
 assert len(d['topology']['inductors'])==4
 assert len(d['topology']['fixed_capacitors'])==d['components']['GJM01']['count']
 assert len(d['topology']['pcb_pattern_capacitors'])==d['components']['PCB_PATTERN_C']['count']
 assert abs(d['chip_area_cost_units']-(4+2/3*len(d['topology']['fixed_capacitors'])))<1e-10
 Ls=d['topology']['inductors'];L=np.array([e['L_nH'] for e in Ls])*1e-9
 assert np.all(L>=.4e-9-1e-14) and np.all(L<=56e-9+1e-14)
 row=[int(x[1:]) for x in d['topology']['physical_chip_row']];assert sorted(row)==[0,1,2,3]
 K=np.eye(4);M=np.diag(L)
 for j,k in enumerate(d['topology']['signed_adjacent_k']):
  a,b=row[j:j+2];assert abs(k)<=.4000000002
  K[a,b]=K[b,a]=k;M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
 mineig=float(np.linalg.eigvalsh(K).min());assert mineig>0
 Zbase=np.diag(L/25)+1j*M
 B=np.column_stack([vedge(e['nodes']) for e in Ls]);red=B@np.linalg.solve(Zbase,B.T)
 caps=d['topology']['fixed_capacitors']+d['topology']['pcb_pattern_capacitors']+d['topology']['variable_capacitors']
 Cfix=np.array([c['C_pF'] for c in d['topology']['fixed_capacitors']])*1e-12
 Cpcb=np.array([c['C_pF'] for c in d['topology']['pcb_pattern_capacitors']])*1e-12
 Q=np.array([80]*len(Cfix)+[40]*len(Cpcb)+[80]*3)
 assert np.all(Cfix>=.1e-12-1e-20)
 if len(Cpcb):assert np.all(Cpcb>=.02e-12-1e-20) and np.all(Cpcb<=.2e-12+1e-20)
 E=[vedge(c['nodes']) for c in caps]
 port=np.zeros((5,5),complex);port[0,0]=1/50;port[2,2]=1/(60-40j)
 src=np.array([.02,0,0,0,0],complex)
 m=[];per={};max_balance=0;max_diff=0;mna_count=0;worst={'IL':None,'H2':None,'H3':None}
 for case in CASES:
  tune=np.array(d['variable_C_pf_by_setting'][case])*1e-12
  assert len(tune)==3 and np.all(tune>=0) and np.all(tune<=4e-12)
  vals=np.r_[Cfix,Cpcb,tune]
  Ycap=sum(w*c/(1/q-1j) for w,c,q in zip((np.outer(v,v) for v in E),vals,Q))
  values={'IL':(-np.inf,None),'H2':(np.inf,None),'H3':(np.inf,None)}
  for r in [r for r in BANDS if r['case']==case]:
   t='IL' if r['region'] in ('UL','DL') else r['region']
   lo=float(r['low_mhz']);hi=float(r['high_mhz'])
   f=np.linspace(lo,hi,grid);w=2*np.pi*1e6*f
   Y=port[None,:,:]+red[None,:,:]/w[:,None,None]+w[:,None,None]*Ycap[None,:,:]
   voltage=np.linalg.solve(Y,np.broadcast_to(src,(len(w),5))[...,None])[...,0]
   ildb=-10*np.log10(np.maximum(200*60/5200*abs(voltage[:,2])**2,1e-300))
   ix=int(np.argmax(ildb) if t=='IL' else np.argmin(ildb))
   z=float(ildb[ix]);ff=float(f[ix])
   if (t=='IL' and z>values[t][0]) or (t!='IL' and z<values[t][0]):values[t]=(z,ff)
   # bounded local extremum search brackets grid extremum, max 11 local evaluations
   a=f[max(0,ix-1)];b=f[min(grid-1,ix+1)]
   if b>a:
    def fval(fmhz):
     omega=2*np.pi*1e6*fmhz
     v=np.linalg.solve(port+omega*Ycap+red/omega,src)[2]
     return -10*np.log10(200*60/5200*abs(v)**2)
    fopt=minimize_scalar((lambda ff:-fval(ff)) if t=='IL' else fval,bounds=(a,b),method='bounded',options={'xatol':1e-9})
    zz=fval(float(fopt.x))
    if (t=='IL' and zz>values[t][0]) or (t!='IL' and zz<values[t][0]):values[t]=(float(zz),float(fopt.x))
  per[case]={t:{'db':val[0],'frequency_mhz':val[1]} for t,val in values.items()}
  for t in ('IL','H2','H3'):
   if worst[t] is None or (t=='IL' and values[t][0]>worst[t]['db']) or (t!='IL' and values[t][0]<worst[t]['db']):
    worst[t]={'db':values[t][0],'frequency_mhz':values[t][1],'setting':case}
  # independently compute full 9x9 MNA for endpoints, representative centers, H2,H3
  for g in (('UL','DL'),('H2',),('H3',)):
   rg=[r for r in BANDS if r['case']==case and r['region'] in g]
   frequencies=np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),5) for r in rg])
   for fm in [frequencies[0],frequencies[len(frequencies)//2],frequencies[-1]]:
    omega=fm*2*np.pi*1e6
    A=np.block([[port+omega*Ycap,B],[-B.T,omega*Zbase]])
    sol=np.linalg.solve(A,np.r_[src,np.zeros(4,complex)]);V=sol[:5];I=sol[5:]
    Vred=np.linalg.solve(port+omega*Ycap+red/omega,src)
    max_diff=max(max_diff,float(abs(Vred[2]-V[2])))
    Pload=float(abs(V[2])**2*60/5200)
    Ploss=float(np.real(np.vdot(I,(omega*np.diag(L/25))@I)))
    Closs=float(sum(abs(v@V)**2*np.real(omega*c/(1/q-1j)) for v,c,q in zip(E,vals,Q)))
    Pref=float(abs(1-2*V[0])**2/200)
    max_balance=max(max_balance,abs(.005-Pload-Ploss-Closs-Pref));mna_count+=1
 result={'id':d['id'],'worst_IL_db':worst['IL']['db'],'min_H2_db':worst['H2']['db'],'min_H3_db':worst['H3']['db'], 'limiting':worst, 'metrics_by_setting':per, 'min_K_eigenvalue':mineig,'max_power_balance_W':max_balance,'max_MNA_discrepancy_V':max_diff,'independent_9x9_MNA_representative_points':mna_count,'dense_points_per_individual_interval':grid,'numerical_not_EM_verified':True,'not_global_optimality_proven':True,'continuous_interval_proof':False}
 assert max_balance<1e-12 and max_diff<1e-11 and mna_count==54
 if require:assert result['worst_IL_db']<=.30 and result['min_H2_db']>=30 and result['min_H3_db']>=30, result
 return result

def main():
 ar=argparse.ArgumentParser();ar.add_argument('files',nargs='*',default=[]);ar.add_argument('--grid',type=int,default=7001);ar.add_argument('--update',action='store_true');args=ar.parse_args()
 for name in args.files or ['EXP011-01.json','EXP011-02.json']:
  path=Path(name);path=path if path.is_absolute() else HERE/path
  d=json.loads(path.read_text());metrics=analyze(d,args.grid)
  if args.update:
   d['verified_dense_metrics']=metrics;d['verification_status']='independent 9x9 MNA spot + 7001 per individual segment verified; 2nd formulation'
   path.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
  else:
   saved=d.get('verified_dense_metrics',{});assert abs(saved['worst_IL_db']-metrics['worst_IL_db'])<1e-7
   assert abs(saved['min_H2_db']-metrics['min_H2_db'])<1e-7 and abs(saved['min_H3_db']-metrics['min_H3_db'])<1e-7
  print(json.dumps({k:metrics[k] for k in ('id','worst_IL_db','min_H2_db','min_H3_db','limiting','max_power_balance_W','min_K_eigenvalue')},indent=2),flush=True)
if __name__=='__main__':main()