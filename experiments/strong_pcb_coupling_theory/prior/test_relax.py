import os,json,numpy as np
from weak_vary import opt
from explore import MED, SMALL
p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'results.json');j=json.load(open(p));best=min((r for r in j if r['good']),key=lambda r:r['IL'])
for limit in [3.,4.,5.,7.]:
 r=opt(best['edges'],best['cp'],best['extraC'],initial=np.array(best['x']),grid=MED,maxiter=210,pcbmax=limit)
 print(limit, r['IL'],r['H2'],r['H3'],r['lp'],r['kp'],r['good'],r['time'],flush=True)
 json.dump(r,open('/mnt/data/pcb_weak_study/relax_'+str(limit)+'.json','w'),indent=2)
