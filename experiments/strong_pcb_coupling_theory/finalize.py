import os,json,numpy as np,csv
from variants import opt,eval3,MED,DENSE
root=os.path.dirname(os.path.abspath(__file__))
raw=json.load(open(root+'/topology_results.json'))
refined=json.load(open(root+'/refined_results.json'))
seed=raw[1]
allr=[]
for km in (0.,.05):
 r=opt(seed['edges'],seed['cp'],km=km,seed=seed,grid=MED,maxiter=200)
 print('zero/weak',km,r['IL'],r['H2'],r['H3'],r['k'],r['psd'],flush=True)
 allr.append(r)
 json.dump(allr,open(root+'/zero_results.json','w'),indent=2)
