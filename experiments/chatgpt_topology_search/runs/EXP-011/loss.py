import sys,json,numpy as np
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from verify import vedge
for name in ('EXP011-01','EXP011-02'):
 d=json.loads((HERE/(name+'.json')).read_text());top=d['topology']; fmhz=d['verified_dense_metrics']['limiting']['IL']['frequency_mhz'];case=d['verified_dense_metrics']['limiting']['IL']['setting']
 w=2*np.pi*1e6*fmhz; Ls=top['inductors']; L=np.array([z['L_nH'] for z in Ls])*1e-9
 K=np.eye(4);M=np.diag(L)
 row=[int(x[1:]) for x in top['physical_chip_row']]
 for j,k in enumerate(top['signed_adjacent_k']):
  a,b=row[j:j+2];M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b]);K[a,b]=K[b,a]=k
 B=np.column_stack([vedge(z['nodes']) for z in Ls]);Z=np.diag(L/25)+1j*M
 caps=top['fixed_capacitors']+top['variable_capacitors'];Cs=np.r_[[z['C_pF'] for z in top['fixed_capacitors']],d['variable_C_pf_by_setting'][case]]*1e-12
 Cmat=sum(w*c/(1/80-1j)*np.outer(vedge(z['nodes']),vedge(z['nodes'])) for c,z in zip(Cs,caps))
 ports=np.zeros((5,5),complex);ports[0,0]=1/50;ports[2,2]=1/(60-40j)
 A=np.block([[ports+Cmat,B],[-B.T,w*Z]]);s=np.array([.02,0,0,0,0]+[0]*4)
 z=np.linalg.solve(A,s);V=z[:5];I=z[5:]
 load=abs(V[2])**2*60/5200;refl=abs(1-2*V[0])**2/200
 ind=np.array([abs(I[i])**2*w*L[i]/25 for i in range(4)])
 cpower=np.array([abs(vedge(z['nodes'])@V)**2*np.real(w*c/(1/80-1j)) for c,z in zip(Cs,caps)])
 diss=ind.sum()+cpower.sum();Iltotal=-10*np.log10(load/.005);Ilref=-10*np.log10((.005-refl)/.005);Ildiss=-10*np.log10(load/(.005-refl));factor=Ildiss/diss
 record={'id':name,'frequency_MHz':fmhz,'setting':case,'IL_dB':Iltotal,'Pavs_mW':5,'Pload_mW':load*1000,'Pref_mW':refl*1000,'sum_loss_mW':diss*1000,'power_residual_W':.005-load-refl-diss,'reflection_dB':Ilref,'L_by_id_dB':{f'L{i}':float(v*factor) for i,v in enumerate(ind)},'GJM_by_id_dB':{'Cf3':float(cpower[0]*factor)},'IC_C_by_id_dB':{f'Cv{i}':float(z*factor) for i,z in enumerate(cpower[1:])},'sum_all_dB':Ilref+factor*diss,'accounting_not_causal_sensitivity':True}
 (HERE/(name+'-loss.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))