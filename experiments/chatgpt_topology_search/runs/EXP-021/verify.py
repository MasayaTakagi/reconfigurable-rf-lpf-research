#!/usr/bin/env python3
"""Independent Phase-2 RF-T004 checker for EXP-021; finite mesh only."""
import csv
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CASES=['B71','B12','B28','B13+B14','B26','B8']
GS=1/50
YL=1/(60-40j)
PAVS=1/200

def incidence(edges):
    B=np.zeros((5,len(edges)))
    for i,(a,b) in enumerate(edges):
        B[a,i]=1
        if b!=-1: B[b,i]=-1
    return B

def nodal(fs,c,cv):
    f=np.atleast_1d(np.asarray(fs,float))
    om=2*np.pi*f*1e6
    L=np.asarray(c['L_nH'],float)
    q=np.asarray(c['Q_L'],float)
    M=np.diag(L)
    for i,k in enumerate(c['k_adjacent']):
        M[i,i+1]=M[i+1,i]=k*np.sqrt(L[i]*L[i+1])
    assert np.linalg.eigvalsh(M).min()>0
    H=np.diag(L/q)+1j*M
    top=c['topology']
    BL=incidence(top['L'])
    BC=incidence(top['F']+top['V'])
    cap=np.r_[c['fixed_C_pF'],cv]
    qc=np.r_[np.full(len(top['F']),80.),np.full(len(top['V']),50.)]
    yc=om[:,None]*1e-12*cap[None,:]/(1/qc[None,:]-1j)
    Y=(BL@np.linalg.inv(H)@BL.T)[None,:,:]/(om[:,None,None]*1e-9)
    Y+=np.einsum('fb,ib,jb->fij',yc,BC,BC,optimize=True)
    Y[:,0,0]+=GS
    Y[:,3,3]+=YL
    b=np.zeros((len(f),5),complex)
    b[:,0]=GS
    V=np.linalg.solve(Y,b[...,None])[...,0]
    g=np.maximum(4*50*YL.real*abs(V[:,3])**2,1e-300)
    return -10*np.log10(g),V,H,yc,BL,BC

def independent(f,c,cv):
    _,Vn,H,yc,BL,BC=nodal([f],c,cv)
    active=abs(yc[0])>1e-23
    B=np.column_stack((BL,BC[:,active]))
    nl=len(c['topology']['L'])
    n=B.shape[1]
    Z=np.zeros((n,n),complex)
    Z[:nl,:nl]=2*np.pi*f*1e6*1e-9*H
    Z[nl:,nl:]=np.diag(1/yc[0,active])
    A=np.zeros((5+n,5+n),complex)
    A[:5,5:]=B
    A[5:,:5]=B.T
    A[5:,5:]=-Z
    A[0,0]=GS
    A[3,3]=YL
    rhs=np.zeros(5+n,complex)
    rhs[0]=GS
    sol=np.linalg.solve(A,rhs)
    V,I=sol[:5],sol[5:]
    Isrc=(1-V[0])*GS
    branchloss=np.real(np.vdot(I,Z@I))
    pout=abs(V[3])**2*YL.real
    energyerror=abs(Isrc.real-50*abs(Isrc)**2-branchloss-pout)
    return float(np.max(abs(V-Vn[0]))),float(energyerror),float(max(0,pout-PAVS))

def main():
    doc=json.loads((HERE/'selected_checkpoints.json').read_text(encoding='utf-8'))
    bands=list(csv.DictReader((ROOT/'data/bands.csv').open(encoding='utf-8')))
    assert doc['constraint_id']=='RF-T004'
    for c in doc['candidates']:
        top=c['topology']
        assert len(top['L'])==4 and len(top['V'])<=3
        assert all(.4<=v<=27 for v in c['L_nH'])
        assert all(0<v<=100 for v in c['fixed_C_pF'])
        assert all(0<=v<=1.5 for row in c['variable_C_by_setting_pF'] for v in row)
        assert len(c['variable_C_by_setting_pF'])==6
        assert all(q in (25,33) for q in c['Q_L'])
        assert len(c['k_adjacent'])==3 and max(map(abs,c['k_adjacent']))<=.15+1e-10
        area=sum(3 if q==33 else 1 for q in c['Q_L'])+2*len(top['F'])/3
        assert abs(area-c['area'])<1e-8
        worst,h2,h3=-np.inf,np.inf,np.inf
        maxv=maxw=maxp=0.
        probes=0
        for row in bands:
            i=CASES.index(row['case'])
            lo,hi=float(row['low_mhz']),float(row['high_mhz'])
            cv=c['variable_C_by_setting_pF'][i]
            il,*_=nodal(np.linspace(lo,hi,7001),c,cv)
            if row['type']=='pass': worst=max(worst,float(max(il)))
            elif row['region']=='H2': h2=min(h2,float(min(il)))
            else: h3=min(h3,float(min(il)))
            for f in (lo,(lo+hi)/2,hi):
                dv,dw,dp=independent(f,c,cv)
                maxv=max(maxv,dv)
                maxw=max(maxw,dw)
                maxp=max(maxp,dp)
                probes+=1
        assert probes==84
        assert abs(worst-c['worst_IL_db'])<2e-5
        assert abs(h2-c['min_H2_db'])<2e-5
        assert abs(h3-c['min_H3_db'])<2e-5
        assert maxv<1e-9 and maxw<1e-10 and maxp<1e-10
        print(c['id'],'worst_IL_dB',round(worst,8),'min_H2_dB',round(h2,6),
              'min_H3_dB',round(h3,6),'probes',probes,
              'node_error_V',maxv,'power_balance_W',maxw)
    print('PASS: finite-grid nominal model only; physical implementation unverified.')

if __name__=='__main__':
    main()
