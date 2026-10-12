#!/usr/bin/env python3
"""Independent Phase 2 EXP010-02 MNA, 6-case full-band verification.
Checks variable Q80 C, GJM Q80, PCB-pattern Q40 and LQP02 Q25;
7001 points per individual band + bounded extremum refinement, 54 independent 9x9
branch-current MNA checks. Not a circuit-continuum proof or EM validation.
"""
import csv,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CASES=('B71','B12','B28','B13+B14','B26','B8')
N=7001

def incidence(edge):
    v=np.zeros(5)
    for n,s in zip(edge,(1,-1)):
        if n>0:v[n-1]+=s
    return v

def analyze(d,bands):
    assert d['phase']=='Phase 2' and abs(d['chip_area_cost_units']-6)<1e-9
    cp=d['components']
    assert cp['LQP02']['count']==4 and cp['LQP02']['Q']==25
    assert cp['GJM01']['count']==3 and cp['GJM01']['Q']==80
    assert cp['IC_VARIABLE_C']['count']==3 and cp['IC_VARIABLE_C']['Q']==80
    assert cp['PCB_PATTERN_C']['count']==1 and cp['PCB_PATTERN_C']['Q']==40
    top=d['topology'];Ls=top['inductors']
    L=np.array([z['L_nH'] for z in Ls])*1e-9
    assert len(L)==4 and np.all((L>=.4e-9-1e-15)&(L<=56e-9+1e-15))
    B=np.column_stack([incidence(z['nodes']) for z in Ls]);K=np.eye(4);M=np.diag(L.astype(complex))
    row=[int(s[1:]) for s in top['physical_chip_row']]
    assert sorted(row)==list(range(4))
    for i,k in enumerate(top['signed_adjacent_k']):
        assert abs(k)<=.40000001
        a,b=row[i:i+2]
        K[a,b]=K[b,a]=k;M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
    mineig=float(np.linalg.eigvalsh(K).min());assert mineig>0
    # 9x9 MNA retains all L branch currents as independent unknowns.
    Zbase=np.diag(L/25)+1j*M
    # Independently reduced nodal solution for dense-grid evaluation.
    YL=B@np.linalg.solve(Zbase,B.T)
    caps=top['fixed_capacitors']+top['pcb_pattern_capacitors']+top['variable_capacitors']
    Vs=[incidence(z['nodes']) for z in caps]
    fixed=np.array([z['C_pF'] for z in top['fixed_capacitors']])*1e-12
    pcb=np.array([z['C_pF'] for z in top['pcb_pattern_capacitors']])*1e-12
    assert len(fixed)==3 and np.min(fixed)>=.1e-12-1e-18 and np.max(fixed)<=100e-12
    assert len(pcb)==1 and .02e-12-1e-20<=pcb[0]<=.2e-12+1e-20
    Q=np.array([80,80,80,40,80,80,80]);assert len(Vs)==len(Q)
    ports=np.zeros((5,5),complex);ports[0,0]=1/50;ports[2,2]=1/(60-40j)
    source=np.array([1/50,0,0,0,0],complex)
    result=[];extreme_result=[];balance=[];voltage_diff=[];spot_count=0
    for case in CASES:
        tun=np.array(d['variable_C_pf_by_setting'][case])*1e-12
        assert len(tun)==3 and np.min(tun)>=-1e-20 and np.max(tun)<=4e-12+1e-20
        Cs=np.r_[fixed,pcb,tun]
        capY=sum((c/(1/q-1j))*np.outer(v,v) for c,q,v in zip(Cs,Q,Vs))
        case_agg=[];case_ext=[]
        for part,types in enumerate((('UL','DL'),('H2',),('H3',))):
            each=[];exts=[]
            for rowb in [r for r in bands if r['case']==case and r['region'] in types]:
                lo,hi=float(rowb['low_mhz']),float(rowb['high_mhz'])
                fmhz=np.linspace(lo,hi,N);w=2*np.pi*1e6*fmhz
                mat=ports[None,:,:]+YL[None,:,:]/w[:,None,None]+w[:,None,None]*capY[None,:,:]
                v=np.linalg.solve(mat,np.broadcast_to(source,(N,5))[...,None])[...,0]
                il=-10*np.log10(np.maximum((200*60/5200)*np.abs(v[:,2])**2,1e-300))
                idx=int(np.argmax(il) if part==0 else np.argmin(il))
                each.append(float(il[idx]))
                # Scalar frequency refinement around each observed worst grid point.
                def il_at(f):
                    omega=2*np.pi*1e6*f
                    y=ports+YL/omega+omega*capY
                    voltage=np.linalg.solve(y,source)[2]
                    return -10*np.log10((200*60/5200)*abs(voltage)**2)
                fa,fb=fmhz[max(0,idx-1)],fmhz[min(N-1,idx+1)]
                if fb>fa:
                    out=minimize_scalar((lambda f:-il_at(f)) if part==0 else il_at,
                                        bounds=(fa,fb),method='bounded',options={'xatol':1e-9})
                    val=float(il_at(out.x))
                else:val=float(il[idx])
                exts.append(max(val,float(il[idx])) if part==0 else min(val,float(il[idx])))
            case_agg.append(max(each) if part==0 else min(each))
            case_ext.append(max(exts) if part==0 else min(exts))
            # 3 selected frequencies per concatenated pass/H2/H3 group, 54 total.
            wgroups=np.concatenate([np.linspace(float(b['low_mhz']),float(b['high_mhz']),N)*2*np.pi*1e6
                                    for b in bands if b['case']==case and b['region'] in types])
            for omega in (wgroups[0],wgroups[len(wgroups)//2],wgroups[-1]):
                A=np.block([[ports+omega*capY,B],[-B.T,omega*Zbase]])
                sol=np.linalg.solve(A,np.r_[source,np.zeros(4,complex)])
                V,I=sol[:5],sol[5:]
                # independent nodal voltage vs current-augmented 9x9 MNA
                Vred=np.linalg.solve(ports+omega*capY+YL/omega,source)
                voltage_diff.append(float(abs(Vred[2]-V[2])))
                Pload=abs(V[2])**2*60/5200
                Pind=float(np.real(np.vdot(I,(omega*np.diag(L/25))@I)))
                Pcap=float(sum(abs(vec@V)**2*np.real(omega*c/(1/q-1j))
                              for c,q,vec in zip(Cs,Q,Vs)))
                Pref=abs(1-2*V[0])**2/200
                balance.append(float(abs(.005-Pload-Pind-Pcap-Pref)))
                spot_count+=1
        result.append(case_agg);extreme_result.append(case_ext)
    arr=np.array(result);ext=np.array(extreme_result)
    got=np.array([arr[:,0].max(),arr[:,1].min(),arr[:,2].min()])
    refined=np.array([ext[:,0].max(),ext[:,1].min(),ext[:,2].min()])
    expected=d['verified_dense_metrics']
    want=np.array([expected['worst_IL_db'],expected['min_H2_db'],expected['min_H3_db']])
    assert np.max(abs(got-want))<1e-6,(got,want)
    assert np.max(abs(refined-got))<1e-5,(got,refined)
    assert got[0]<=.3 and got[1]>=30 and got[2]>=30
    assert refined[0]<=.3 and refined[1]>=30 and refined[2]>=30
    assert spot_count==54 and max(balance)<1e-12 and max(voltage_diff)<1e-11
    return {'id':d['id'],'IL_max_db':float(got[0]),'H2_min_db':float(got[1]),'H3_min_db':float(got[2]),
            'frequency_refined_IL_max_db':float(refined[0]),'frequency_refined_H2_min_db':float(refined[1]),
            'frequency_refined_H3_min_db':float(refined[2]),'K_min_eigenvalue':mineig,
            'MNA_current_augmented_points':spot_count,
            'max_MNA_voltage_discrepancy_V':max(voltage_diff),
            'max_power_balance_residual_W':max(balance),
            'source_power_W':.005,
            'finite_grid_points_per_individual_frequency_interval':N,
            'global_optimum_proven':False,'interval_proof':False,'EM_verification':False}

def main():
    bands=list(csv.DictReader((ROOT/'data/bands.csv').open(newline='')))
    for name in ('EXP010-02','EXP010-03','EXP010-04','EXP010-05'):
        d=json.loads((HERE/(name+'.json')).read_text())
        print(json.dumps(analyze(d,bands),indent=2),flush=True)
if __name__=='__main__':main()