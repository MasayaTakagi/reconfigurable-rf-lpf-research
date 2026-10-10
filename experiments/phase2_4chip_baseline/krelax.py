import json,numpy as np,sys
sys.path[:0]=['/mnt/data/lpf_limit_study','/mnt/data/lpf_next']
from run_limits import tune
from explore import MED
x=np.array(json.load(open('/mnt/data/lpf_phase2_extension/first.json'))['x']);a=[]
for kmax in [.25,.30,.35,.4,.5]:
 r=tune(x,35.05,kmax,maxiter=280,stage=MED,otherlimit=[.16,[2,3]])
 a.append(r)
 if r['valid']:x=np.array(r['x'])
 print('KRELAX',kmax,r['IL'],r['H2'],r['H3'],r['valid'],'k',np.round(r['x'][4:10],3),flush=True)
 json.dump(a,open('/mnt/data/lpf_phase2_extension/krelax.json','w'),indent=1)
