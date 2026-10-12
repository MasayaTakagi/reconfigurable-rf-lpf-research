#!/usr/bin/env python3
"""Independent current-augmented 9x9 MNA and energy accounting for updated Q-series Phase2 designs."""
import sys,json,glob
from pathlib import Path
import numpy as np
from reopt import OLD,Network,BANDS,CASES,incidence
ROOT=Path(__file__).resolve().parent

def verify(path):
 d=json.loads(Path(path).read_text());ref=OLD[d['base_candidate']]
 row=d['physical_row'];L=np.array(d['L_nH'])*1e-9;q=np.array(d['Q_L'])
 ss=[z[-2:] for z in d['chip_series']];ss=['HV' if s=='HV' else 'HQ' for s in ss]
 # Reject invalid chip-Q/range assignments
 for li,qi,s in zip(d['L_nH'],q,ss):
  if s=='HV': assert .4<=li<=27+1e-7 and qi==25
  if s=='HQ': assert .2<=li<=56+1e-7 and qi==20
 K=np.eye(4);M=np.diag(L)
 for i,k in enumerate(d['signed_neighbor_k']):
  a,b=row[i:i+2];M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b]);K[a,b]=K[b,a]=k
 mine=float(np.linalg.eigvalsh(K).min());assert mine>0 and np.max(np.abs(d['signed_neighbor_k']))<=.4000001
 B=incidence([(1,2),(3,4),(2,5),(2,3)]).T
 E=ref['fixed_edges']+ref['pcb_edges']+ref['cv_edges'];C=np.array(d['fixed_C_pf']);nfix=len(C)
 qC=np.array([80]*len(ref['fixed_edges'])+[40]*len(ref['pcb_edges'])+[80]*len(ref['cv_edges']))
 D=incidence(E)
 port=np.zeros((5,5),complex);port[0,0]=1/50;port[2,2]=1/(60-40j)
 src=np.array([1/50,0,0,0,0],complex)
 maxdiff=0;maxpower=0;maxcap=0;checks=0;crit={}
 for ci,case in enumerate(CASES):
  Cv=np.array(d['Cv_by_setting_pF'][case]);assert Cv.min()>=-1e-6 and Cv.max()<=4+1e-6
  qcase=np.r_[C,Cv];assert np.all(qcase>=-1e-12)
  for region in ['UL','DL','H2','H3']:
   segments=[b for b in BANDS if b['case']==case and b['region']==region]
   f_all=np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),3) for r in segments]);
   sample=np.array([f_all[0],f_all[len(f_all)//2],f_all[-1]])
   for f in sample:
    w=2*np.pi*f*1e6;Yc=np.array([w*cap*1e-12/(1/q-1j) for cap,q in zip(qcase,qC)])
    Ys=port+D.T@np.diag(Yc)@D
    Z=w*(np.diag(L/q)+1j*M)
    A=np.block([[Ys,B],[B.T,-Z]])
    rhs=np.r_[src,np.zeros(4)]
    v=np.linalg.solve(A,rhs);V=v[:5];I=v[5:];full_il=-10*np.log10(200*60/5200*abs(V[2])**2)
    # independent eliminated loop version, using a differently formed reduction
    Vref=np.linalg.solve(Ys+B@np.linalg.solve(Z,B.T),src)
    maxdiff=max(maxdiff,float(np.max(abs(V-Vref))))
    Pav=1/(4*50)
    Pref=abs(V[0]-.5)**2/50
    Pload=abs(V[2])**2*60/5200
    Ploss=np.sum(w*L/q*abs(I)**2)
    Vdif=D@V;Pcap=np.sum(Yc.real*abs(Vdif)**2)
    resid=Pav-Pref-Pload-Ploss-Pcap
    maxpower=max(maxpower,float(abs(resid)));checks+=1
    assert resid<2e-11 and abs(full_il -(-10*np.log10(Pload/Pav)))<1e-8
 assert maxdiff<1e-9 and maxpower<1e-11
 o={'id':Path(path).stem,'independent_MNA':True,'frequency_spots':checks,'max_nodal_voltage_discrepancy':maxdiff,'max_power_residual_W':maxpower,'min_K_eigen':mine,'Q_by_series_verified':True,'L_range_verified':True,'chip_area_cost':4+len(ref['fixed_edges'])*2/3,'SRF_not_verified':True}
 return o
if __name__=='__main__':
 paths=sys.argv[1:] or glob.glob(str(ROOT/'*.json'))
 for path in paths:
  if not (path.endswith('.json') and 'rows.json' not in path):continue
  try:
   result=verify(path)
   out=Path(path).with_name(Path(path).stem+'_independent_MNA.json');out.write_text(json.dumps(result,indent=2)+'\n')
   print(result['id'],'PASS',result['frequency_spots'],'errV',result['max_nodal_voltage_discrepancy'],'power',result['max_power_residual_W'])
  except Exception as e:
   print(path,'FAIL',repr(e));raise