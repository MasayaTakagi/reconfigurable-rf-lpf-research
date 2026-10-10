import os,sys,json,csv,zipfile
import numpy as np
from scipy.optimize import minimize_scalar
sys.path.insert(0,'/mnt/data/lpf_next')
from explore import *
OUT='/mnt/data/lpf_phase2_extension'
q=np.array([25.,25.,25.,25.,80.]);top=three_series(2)
baseline=json.load(open(OUT+'/first.json'));x=np.array(baseline['x'])

def calc(one,xx):
 C=np.array(xx[10:]).reshape(6,4)[one];y=np.r_[xx[:4],C,xx[4:10]]
 return lambda f:transfer(y,np.asarray(f,dtype=float),*top,q)

def find_extreme(calc_f,ranges,want='max',dx=.05):
 v_best=(-1e99 if want=='max' else 1e99,None)
 for lo,hi in ranges:
  ff=np.linspace(lo,hi,int(np.ceil((hi-lo)/dx))+1)
  rr=calc_f(ff)
  f_exts=[(float(ff[0]),float(rr[0])),(float(ff[-1]),float(rr[-1]))]
  for i in range(1,len(ff)-1):
   if (want=='max' and rr[i]>=rr[i-1] and rr[i]>=rr[i+1]) or (want=='min' and rr[i]<=rr[i-1] and rr[i]<=rr[i+1]):
    res=minimize_scalar(lambda z: float(calc_f(np.array([z]))[0])*(-1 if want=='max' else 1),bounds=(ff[i-1],ff[i+1]),method='bounded',options={'xatol':1e-9})
    f_exts.append((res.x,-res.fun if want=='max' else res.fun))
  mode=max if want=='max' else min
  best=mode(f_exts,key=lambda z:z[1])
  if (want=='max' and best[1]>v_best[0]) or (want=='min' and best[1]<v_best[0]):v_best=(best[1],best[0])
 return v_best

rows=[]
for i,name in enumerate(NAMES):
 b=BANDS[name]; fun=calc(i,x)
 p,fp=find_extreme(fun,b['ul']+b['dl'],'max')
 h2,f2=find_extreme(fun,[(2*a,2*z) for a,z in b['ul']],'min')
 h3,f3=find_extreme(fun,[(3*a,3*z) for a,z in b['ul']],'min')
 row=dict(band=name,MaxIL_dB=p,IL_peak_MHz=fp,H2min_dB=h2,H2worst_MHz=f2,H3min_dB=h3,H3worst_MHz=f3,**{f'C{n+1}_pF':x[10+4*i+n] for n in range(4)})
 rows.append(row)
 print(name,{k:round(v,6) if isinstance(v,(int,float)) else v for k,v in row.items() if k not in ('band','C1_pF','C2_pF','C3_pF','C4_pF')},flush=True)
with open(OUT+'/dense_verification.csv','w',newline='') as fo:
 wr=csv.DictWriter(fo,fieldnames=rows[0].keys());wr.writeheader();wr.writerows(rows)
print('K',x[4:10],'PSD minimum',psd(x[4:10]))
print('extrema maximum IL',max(r['MaxIL_dB'] for r in rows),'H2',min(r['H2min_dB'] for r in rows),'H3',min(r['H3min_dB'] for r in rows))
