import numpy as np,json,time,sys
sys.path[:0]=['/mnt/data/lpf_phase2_extension']
from search_extended import search, ATT, Q
sys.path.insert(0,'/mnt/data/lpf_next')
from explore import three_series
p='/mnt/data/lpf_phase2_extension';v=json.load(open(p+'/first.json'));base=np.array(v['x']);
rng=np.random.default_rng(20261010001)
a=[]
for i in range(36):
 x=base.copy();sc=[.03,.12,.30,.50][i%4]; x[:4]*=np.exp(rng.normal(0,sc,4));x[4:10]+=rng.normal(0,sc*.22,6)
 xx=x[10:].reshape(6,4);xx*=np.exp(rng.normal(0,sc,size=(6,1))+rng.normal(0,sc*.5,size=(1,4)))
 r=search(x,three_series(2),pair=(2,3),maxiter=200)
 r['trial']=i;r['sigma']=sc
 a.append(r)
 print('TRIAL',i,'sig',sc,'IL',round(r['IL'],6),'H2/H3',round(r['H2'],3),round(r['H3'],3),'good',r['feasible'],'time',r['time'],flush=True)
 if i%3==2:json.dump(a,open(p+'/multistart.json','w'),indent=1)
json.dump(a,open(p+'/multistart.json','w'),indent=1)
