import numpy as np,json,sys
sys.path.insert(0,'/mnt/data/lpf_phase2_extension')
from search_extended import search
sys.path.insert(0,'/mnt/data/lpf_next')
from explore import three_series
src=json.load(open('/mnt/data/lpf_phase2_extension/first.json'));x=np.array(src['x']);out=[]
for tar in [35.05,35.,34.5,34.,33.5,33.,32.5,31.,30.05]:
 r=search(x,three_series(2),pair=(2,3),maxiter=210,atten=tar)
 if r['feasible']:x=np.array(r['x'])
 r['target']=tar;out.append(r)
 print('FRONT',tar,round(r['IL'],6),round(r['H2'],5),round(r['H3'],5),'ok',r['feasible'],flush=True)
 json.dump(out,open('/mnt/data/lpf_phase2_extension/frontier.json','w'),indent=1)
