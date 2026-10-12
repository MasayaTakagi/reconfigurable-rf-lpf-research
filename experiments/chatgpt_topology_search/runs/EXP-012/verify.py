#!/usr/bin/env python3
"""EXP012: independently recheck five saved cost-reduction local candidates.

7001 samples per individual band interval (5x5 elimination) + 54 independent
8x8 or 9x9 current-augmented MNA spot solves per candidate. The main study
results and implementation/emittance assumptions are not independent physics.
"""
import json
import numpy as np
from pathlib import Path
from search_cost import Model, LEDGES, CASES, BANDS
HERE=Path(__file__).resolve().parent

def verify(d,pts=7001,mna=True):
    inds=[LEDGES.index(tuple(x)) for x in d['inductor_edges']]
    cQ=[80]*d['n_GJM']+[40]*d['n_PCB_C']
    cr=[(.1,100)]*d['n_GJM']+[(.02,.2)]*d['n_PCB_C']
    mod=Model(inds=inds,ledges=d['inductor_edges'],cedges=d['fixed_capacitor_edges'],var_edges=d['variable_capacitor_edges'],fixed_q=cQ,fixed_ranges=cr,qL=d['L_Q'],n=9)
    val=d['values'];var=np.array([val['tunable_C_pF_by_setting'][s] for s in CASES]);assert var.shape==(6,mod.nv)
    x=np.r_[np.log(val['L_nH']),np.log(val['fixed_C_pF']),val['signed_neighbor_k'],var.ravel(),.4]
    assert len(x)==len(mod.bounds) and np.min(var)>=-1e-12 and np.max(var)<=4+1e-12
    L,M,Z,Zi,YL,K=mod._network(x);assert np.linalg.eigvalsh(K).min()>0
    got=mod.metrics(x,n=pts)
    if pts==7001:
        expected=d['refined_full_grid']
        assert abs(got['IL']-expected['IL_db'])<1e-6
        assert abs(got['H2']-expected['min_H2_db'])<1e-6
        assert abs(got['H3']-expected['min_H3_db'])<1e-6
    assert (got['IL']<=.3 and min(got['H2'],got['H3'])>=30)==d['meets_IL_le_0.30_and_both_H_ge_30']
    if not mna:return got
    fixed=np.exp(x[mod.nl:mod.kstart])*1e-12;cv=var*1e-12
    balances=[];v_errors=[]
    for si,case in enumerate(CASES):
        caps=np.r_[fixed,cv[si]]
        YC=np.einsum('i,i,ijk->jk',caps,mod.cfac,mod.O)
        for group in [('UL','DL'),('H2',),('H3',)]:
            freqs=np.concatenate([np.linspace(float(b['low_mhz']),float(b['high_mhz']),11)
                                  for b in BANDS if b['case']==case and b['region'] in group])
            for fm in (freqs[0],freqs[len(freqs)//2],freqs[-1]):
                w=2*np.pi*fm*1e6
                A=np.block([[mod.port+w*YC,mod.B],[-mod.B.T,w*Z]])
                u=np.linalg.solve(A,np.r_[mod.source,np.zeros(mod.nl,complex)])
                v,I=u[:5],u[5:]
                vred=np.linalg.solve(mod.port+YL/w+w*YC,mod.source)
                v_errors.append(np.max(abs(v-vred)))
                Pl=abs(v[2])**2*60/5200
                Pind=float(np.real(np.vdot(I,(w*np.diag(L/mod.qL))@I)))
                Pc=float(sum(abs(mod.VC[j]@v)**2*np.real(w*c*mod.cfac[j]) for j,c in enumerate(caps)))
                Pref=abs(1-2*v[0])**2/200
                balances.append(abs(.005-Pl-Pind-Pc-Pref))
    assert len(balances)==54 and max(balances)<1e-12 and max(v_errors)<1e-9
    return {'IL':got['IL'],'H2':got['H2'],'H3':got['H3'],'max_power_balance_W':max(balances),'max_MNA_V_error':max(v_errors),'K_min_eigenvalue':float(np.linalg.eigvalsh(K).min())}

def main():
    records=json.loads((HERE/'independent_shortlist.json').read_text())['verified']
    for d in records:
        result=verify(d)
        print(d['id'],'area',d['chip_cost'],'nCv',d['n_variable_C'],'IL',result['IL'],'H2',result['H2'],'H3',result['H3'],'MNA checked 54','meets_all',d['meets_IL_le_0.30_and_both_H_ge_30'],flush=True)

if __name__=='__main__':main()