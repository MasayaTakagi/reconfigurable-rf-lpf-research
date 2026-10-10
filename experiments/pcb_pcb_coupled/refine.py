import os,json,sys,numpy as np
from variants import opt,eval3,MED,DENSE
root=os.path.dirname(os.path.abspath(__file__))
recs=json.load(open(root+'/topology_results.json'))
ids=[1,12,0]
out=[]
for idx in ids:
 seed=recs[idx]
 for limit in (.1,.2,.3):
  rr=opt(seed['edges'],seed['cp'],km=limit,seed=seed,grid=MED,maxiter=250)
  out.append({'orig_idx':idx,**rr})
  json.dump(out,open(root+'/refined_results.json','w'),indent=2)
  print('REF',idx,'kmax',limit,'IL',round(rr['IL'],6),'H2',round(rr['H2'],6),'H3',round(rr['H3'],6),'good',rr['good'],'k',np.round(rr['k'],3),'t',rr['time'],flush=True)
