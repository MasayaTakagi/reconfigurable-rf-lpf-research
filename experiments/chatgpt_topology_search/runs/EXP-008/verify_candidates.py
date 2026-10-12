#!/usr/bin/env python3
"""Phase 2 EXP-008 independent finite-grid and 9x9 MNA candidate regression."""
import csv
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CASES=('B71','B12','B28','B13+B14','B26','B8')
GRID=7001

def edge(a,b):
    v=np.zeros(5)
    if a:v[a-1]+=1
    if b:v[b-1]-=1
    return v

def circuit(d):
    e=d['inductor_edges']; c=d['fixed_capacitor_edges']; t=d['variable_capacitor_edges']
    Bs=np.column_stack([edge(*e[f'L{i}']) for i in range(4)])
    L=np.array(d['L_nH'])*1e-9
    M=np.diag(L.astype(complex)); K=np.eye(4)
    for j,k in enumerate(d['neighbor_k']):
        a,b=(1,2,3,0)[j:j+2]
        K[a,b]=K[b,a]=k;M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
    assert np.linalg.eigvalsh(K).min()>0
    Z0=np.diag(L/d['Q']['LQP02'])+1j*M
    coils=Bs@np.linalg.solve(Z0,Bs.T)
    capkeys=('Cf1','Cf2','Cf3')
    capedges=[edge(*c[k]) for k in capkeys]
    varnames=('Cv0','Cv1','Cv2')
    varedges=[edge(*t[k]) for k in varnames]
    def capmat(setting):
        fixed=np.array(d['fixed_C_pf'])*1e-12
        var=np.array(d['variable_C_pf_by_setting'][setting])*1e-12
        assert len(var)==3 and np.min(var)>=0 and np.max(var)<=4e-12
        return sum((cc/(1/80-1j))*np.outer(vec,vec) for cc,vec in zip(np.r_[fixed,var],capedges+varedges)),np.r_[fixed,var],capedges+varedges
    ports=np.zeros((5,5),complex);ports[0,0]=1/50;ports[2,2]=1/(60-40j)
    rhs=np.array([1/50,0,0,0,0],complex)
    return Bs,L,Z0,coils,capmat,ports,rhs,K

def attenuation(omega,coils,caps,ports,rhs):
    Y=ports[None,:,:]+coils[None,:,:]/omega[:,None,None]+omega[:,None,None]*caps[None,:,:]
    v=np.linalg.solve(Y,np.broadcast_to(rhs,(len(omega),5))[...,None])[...,0]
    return -10*np.log10(np.maximum(200*(60/5200)*abs(v[:,2])**2,1e-300))

def check(d,bands):
    Bs,L,Z0,coils,capmat,ports,rhs,K=circuit(d)
    maxima=[];minh2=[];minh3=[];balance=[];mna_errors=[]
    for case in CASES:
        caps,values,all_edges=capmat(case)
        groups=[]
        for regions in [('UL','DL'),('H2',),('H3',)]:
            om=np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),GRID)*2*np.pi*1e6
                for r in bands if r['case']==case and r['region'] in regions])
            att=attenuation(om,coils,caps,ports,rhs)
            groups.append(att)
            for w in (om[0],om[len(om)//2],om[-1]):
                A=np.block([[ports+w*caps,Bs],[-Bs.T,w*Z0]])
                source=np.r_[rhs,np.zeros(4,complex)]
                u=np.linalg.solve(A,source)
                voltage=u[:5];il=-10*np.log10(200*(60/5200)*abs(voltage[2])**2)
                direct=attenuation(np.array([w]),coils,caps,ports,rhs)[0]
                mna_errors.append(abs(il-direct))
                load=abs(voltage[2])**2*60/5200
                l_loss=np.real(np.vdot(u[5:],(w*np.real(Z0))@u[5:]))
                cap_loss=sum(abs(vec@voltage)**2*np.real(w*cc/(1/80-1j)) for cc,vec in zip(values,all_edges))
                reflected=abs(1-2*voltage[0])**2/(4*50)
                balance.append(abs(1/(4*50)-load-l_loss-cap_loss-reflected))
        maxima.append(float(groups[0].max()));minh2.append(float(groups[1].min()));minh3.append(float(groups[2].min()))
    metrics=d['verification']
    measured=[max(maxima),min(minh2),min(minh3)]
    expected=[metrics['worst_IL_db'],metrics['min_H2_db'],metrics['min_H3_db']]
    assert np.max(np.abs(np.array(measured)-expected))<1e-5,(d['id'],measured,expected)
    assert min(minh2+minh3)+1e-7>=d['rejection_target_db'],d['id']
    assert len(balance)==54 and max(balance)<1e-12 and max(mna_errors)<1e-8
    assert abs(d['chip_area_cost_units']-6.)<1e-10
    return d['id'],measured,max(balance),max(mna_errors)

def main():
    with (ROOT/'data'/'bands.csv').open(newline='') as h:
        bands=list(csv.DictReader(h))
    for name in ('C6-01','C6-02','C6-35'):
        path=HERE/(name+'.json')
        print(check(json.loads(path.read_text()),bands))
if __name__=='__main__':main()
