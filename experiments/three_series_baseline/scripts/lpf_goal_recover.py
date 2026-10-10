import sys,json,numpy as np
sys.path.insert(0,'/mnt/data')
from lpf_goal_4coupling import optimize
D=json.load(open('/mnt/data/lpf_goal/margins.json'))
z=np.array(next(r['x'] for r in D if r['atten']==32))
Q=np.array([25.,25.,25.,25.,80.])
def model(sh=2):
 edge=[(0,1),(sh,-1),(2,3),(1,2)]
 B=np.zeros((4,4),complex)
 for j,(a,b) in enumerate(edge):
  B[j,a]+=1
  if b>=0:B[j,b]-=1
 return B,np.array([False,True,False,False],bool),np.array([(0,0,1),(2,2,3),(3,1,2)],int)
k=[(-.03,.03)]*6
for i in [2,3]:k[i]=(-.25,.25)
s=z.copy();s[:4]=[4.,9.,2.5,3.3];s[4:10]=[0.,0.12,0.,.12,0.,0.]
for i in range(6):s[10+4*i:14+4*i]=[3.,z[10+4*i+1],3.,3.]
a=optimize(s,model(),Q,k,atten=30.5,cmin=.1,cmax=8,iter=150)
print('RECOVER 30.5',a['IL'],a['H2'],a['H3'],a['valid'],flush=True)
b=optimize(a['x'],model(),Q,k,atten=35.05,cmin=.1,cmax=8,iter=180)
print('RECOVER 35',b['IL'],b['H2'],b['H3'],b['valid'],flush=True)
json.dump({'30.5':a,'35.05':b},open('/mnt/data/lpf_goal/3series_best_saved.json','w'),indent=1)
