import json,sys,numpy as np
sys.path.insert(0,'/mnt/data')
from lpf_goal_4coupling import transfer
from lpf_sixband import BANDS
import lpf_reexplore as e
j=json.load(open('/mnt/data/lpf_goal/confirmed_3series.json'))
x=np.array(j['design']['x']);Q=np.array([25]*4+[80.]);
B=np.array([[1,-1,0,0],[0,0,1,0],[0,0,1,-1],[0,1,-1,0]],dtype=np.complex128)
ser=np.array([False,True,False,False]); ed=np.array([(0,0,1),(2,2,3),(3,1,2)],dtype=np.int64)
grid=[]
for name in e.NAMES:
 d=BANDS[name]
 grid.append((np.unique(np.concatenate([np.linspace(a,b,17) for a,b in d['ul']+d['dl']])),np.unique(np.concatenate([np.linspace(2*a,2*b,17) for a,b in d['ul']])),np.unique(np.concatenate([np.linspace(3*a,3*b,17) for a,b in d['ul']]))))
rng=np.random.default_rng(5104)
vals=[]
for trial in range(250):
 L=x[:4]*(1+rng.uniform(-.01,.01,4))
 kk=x[4:10]+rng.uniform(-.01,.01,6)
 il=0.;h2=1e5;h3=1e5
 for i in range(6):
  C=x[10+4*i:14+4*i]*(1+rng.uniform(-.01,.01,4))
  z=np.r_[L,C,kk]
  fp,f2,f3=grid[i]
  ii=transfer(z,fp,B,ser,ed,Q)
  jj=transfer(z,f2,B,ser,ed,Q)
  ll=transfer(z,f3,B,ser,ed,Q)
  il=max(il,float(np.max(ii)));h2=min(h2,float(np.min(jj)));h3=min(h3,float(np.min(ll)))
 vals.append((il,h2,h3))
a=np.array(vals)
print('MONTE CARLO 250 independent random uniform L and C +/-1% and all 6 k +/-0.01',flush=True)
print('IL max',a[:,0].max(),'H2 min',a[:,1].min(),'H3 min',a[:,2].min(),'failing 30dB',np.sum((a[:,1]<30)|(a[:,2]<30)),flush=True)
print('QTL',np.quantile(a,[0,.05,.5,.95,1],axis=0),flush=True)
json.dump(dict(count=250,IL_max=float(a[:,0].max()),H2_min=float(a[:,1].min()),H3_min=float(a[:,2].min()),failing=int(np.sum((a[:,1]<30)|(a[:,2]<30)))),open('/mnt/data/lpf_goal/monte_carlo_summary.json','w'),indent=2)
