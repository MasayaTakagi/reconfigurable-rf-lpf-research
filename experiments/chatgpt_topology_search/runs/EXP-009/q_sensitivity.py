import json,numpy as np,csv
from pathlib import Path
from pathlib import Path
CASES=('B71','B12','B28','B13+B14','B26','B8')
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
bands=list(csv.DictReader((ROOT/'data/bands.csv').open(newline='')))
d=json.loads((HERE/'EXP009-01.json').read_text())
def edge(e):
 v=np.zeros(5)
 for n,s in zip(e,[1,-1]):
  if n>0:v[n-1]+=s
 return v
T=d['topology'];L=np.array([z['L_nH'] for z in T['inductors']])*1e-9
B=np.stack([edge(z['nodes']) for z in T['inductors']],axis=1)
M=np.diag(L.astype(complex));order=[int(z[1:]) for z in T['physical_chip_row']]
for i,k in enumerate(T['signed_adjacent_k']):
 a,b=order[i:i+2];M[a,b]=M[b,a]=k*np.sqrt(L[a]*L[b])
fixed=np.array([z['C_pF'] for z in T['fixed_capacitors']])*1e-12
cedges=[edge(z['nodes']) for z in T['fixed_capacitors']+T['variable_capacitors']]
ports=np.zeros((5,5),complex);ports[0,0]=1/50;ports[2,2]=1/(60-40j)
src=np.array([1/50,0,0,0,0],complex)
def metric(qvec,N=1501):
 coil=B@np.linalg.solve(np.diag(L/np.asarray(qvec))+1j*M,B.T)
 out=np.zeros((6,3))
 for i,case in enumerate(CASES):
  var=np.array(d['variable_C_pf_by_setting'][case])*1e-12
  Yc=sum((c/(1/80-1j))*np.outer(vec,vec) for c,vec in zip(np.r_[fixed,var],cedges))
  for j,regions in enumerate([('UL','DL'),('H2',),('H3',)]):
   w=np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),N)*2*np.pi*1e6 for r in bands if r['case']==case and r['region'] in regions])
   Y=ports[None,:,:]+coil[None,:,:]/w[:,None,None]+w[:,None,None]*Yc[None,:,:]
   v=np.linalg.solve(Y,np.broadcast_to(src,(len(w),5))[...,None])[...,0]
   vals=-10*np.log10(200*60/5200*np.abs(v[:,2])**2)
   out[i,j]=max(vals) if j==0 else min(vals)
 return {'scenario_Q_by_L0_L1_L2_L3':qvec,'maxIL':float(out[:,0].max()),'min_H2':float(out[:,1].min()),'min_H3':float(out[:,2].min()),'maxIL_setting':CASES[int(out[:,0].argmax())]}
scenarios=[[25,25,25,25],[25,22,25,25],[25,19,25,25],[25,16,25,25],[20,20,20,20]]
if __name__=='__main__':
 for v in scenarios:print(json.dumps(metric(v,1501),sort_keys=True))