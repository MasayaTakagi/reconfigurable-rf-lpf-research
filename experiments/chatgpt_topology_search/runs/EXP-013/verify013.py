#!/usr/bin/env python3
"""Validate EXP013 row candidate with 7001/interval and separately augmented 9x9 MNA at 54 points."""
import csv,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
from model013 import Model,BANDS,CASES

def check(d,n=7001):
 top=d['topology'];ind=[tuple(z['nodes']) for z in top['inductors']];pcb=[tuple(z['nodes']) for z in top['pcb_capacitors']];var=[tuple(z['nodes']) for z in top['tunable_capacitors']]
 model=Model(ledges=ind,cedges=pcb,var_edges=var,n=9,fixed_q=[40]*len(pcb),fixed_ranges=[(.02,.2)]*len(pcb))
 row=top['physical_chip_row'];model.row=row;model.neighbor=[(row[i],row[i+1]) for i in range(len(row)-1)]
 V=np.array([d['variable_C_pf_by_setting'][s] for s in CASES]);assert V.shape==(6,3) and V.min()>=-1e-14 and V.max()<=4+1e-14
 x=np.r_[np.log([z['L_nH'] for z in top['inductors']]),np.log([z['C_pF'] for z in top['pcb_capacitors']]),top['signed_adjacent_k'],V.ravel(),.35]
 if len(x)!=len(model.bounds):raise ValueError('bad vector')
 L,M,Z,Zi,YL,K=model._network(x)
 assert np.linalg.eigvalsh(K).min()>0
 dense=model.metrics(x,n=n)
 spot_diff=[];balance=[]
 cf=np.exp(x[model.nl:model.kstart])*1e-12
 for si,s in enumerate(CASES):
  C=np.r_[cf,V[si]*1e-12];Cy=np.einsum('i,i,ijk->jk',C,model.cfac,model.O)
  for regs in [('UL','DL'),('H2',),('H3',)]:
   fq=np.concatenate([np.linspace(float(b['low_mhz']),float(b['high_mhz']),11) for b in BANDS if b['case']==s and b['region'] in regs]);
   for f in (fq[0],fq[len(fq)//2],fq[-1]):
    w=2*np.pi*1e6*f
    full=np.block([[model.port+w*Cy,model.B],[-model.B.T,w*Z]])
    sol=np.linalg.solve(full,np.r_[model.source,np.zeros(4,complex)]);v=sol[:5];curr=sol[5:]
    ref=np.linalg.solve(model.port+YL/w+w*Cy,model.source)
    spot_diff.append(float(abs(ref[2]-v[2])))
    output=abs(v[2])**2*60/5200;indloss=np.real(np.vdot(curr,w*np.diag(L/25)@curr));caploss=sum(abs(model.VC[j]@v)**2*np.real(w*C[j]*model.cfac[j]) for j in range(len(C)));refl=abs(1-2*v[0])**2/200
    balance.append(float(abs(.005-output-indloss-caploss-refl)))
 assert len(spot_diff)==54 and max(spot_diff)<1e-10 and max(balance)<1e-12
 return {'dense':dense,'independent_MNA_spots':54,'max_mna_output_V_difference':max(spot_diff),'max_power_balance_residual_W':max(balance),'min_K_eigenvalue':float(np.linalg.eigvalsh(K).min()),'meets_both_harmonics':bool(dense['H2']>=30 and dense['H3']>=30),'meets_target':bool(dense['IL']<=.30 and dense['H2']>=30 and dense['H3']>=30),'grid_points_per_each_interval':n}

def main():
 d=json.loads((HERE/'EXP013-ROW-01.json').read_text());r=check(d);want=d['verified_dense_metrics'];assert abs(r['dense']['IL']-want['IL_db'])<1e-7 and abs(r['dense']['H2']-want['min_H2_db'])<1e-7 and abs(r['dense']['H3']-want['min_H3_db'])<1e-7
 print(json.dumps({k:v for k,v in r.items() if k!='dense'}|{'IL':r['dense']['IL'],'H2':r['dense']['H2'],'H3':r['dense']['H3']},indent=2))
if __name__=='__main__':main()