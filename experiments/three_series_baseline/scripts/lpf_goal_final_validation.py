import json,sys,numpy as np,pandas as pd
sys.path.insert(0,'/mnt/data')
from lpf_goal_4coupling import transfer
from lpf_sixband import BANDS
import lpf_reexplore as e
j=json.load(open('/mnt/data/lpf_goal/3series_refined.json'))
S=sorted([z for z in j if z['valid'] and z['atten']==34 and z['weak']==.03 and z['cmax']==25],key=lambda z:z['IL'])[0]
x=np.array(S['x']);Q=np.array([25,25,25,25,80.]);
B=np.array([[1,-1,0,0],[0,0,1,0],[0,0,1,-1],[0,1,-1,0]],dtype=np.complex128)
ser=np.array([False,True,False,False]);eds=np.array([(0,0,1),(2,2,3),(3,1,2)],dtype=np.int64)
rows=[]
for i,nm in enumerate(e.NAMES):
 band=BANDS[nm];xx=np.r_[x[:4],x[10+4*i:14+4*i],x[4:10]]
 def grid(ranges,order=1,step=.02):
  a=np.concatenate([np.r_[np.arange(lo*order,hi*order,step),hi*order] for lo,hi in ranges]);return np.unique(np.round(a,7))
 pp=grid(band['ul']+band['dl']);f2=grid(band['ul'],2);f3=grid(band['ul'],3)
 yy=[transfer(xx,f,B,ser,eds,Q) for f in [pp,f2,f3]]
 vv=[float(np.max(yy[0])),float(np.min(yy[1])),float(np.min(yy[2]))]
 rows.append(dict(band=nm,max_IL_dB=vv[0],min_H2_dB=vv[1],min_H3_dB=vv[2],critical_pass_MHz=float(pp[np.argmax(yy[0])]),critical_H2_MHz=float(f2[np.argmin(yy[1])]),critical_H3_MHz=float(f3[np.argmin(yy[2])]),C1_pF=x[10+4*i],C2_pF=x[11+4*i],C3_pF=x[12+4*i],C4_pF=x[13+4*i]))
 print('VALIDATE',nm,*(round(z,5) for z in vv),flush=True)
pd.DataFrame(rows).to_csv('/mnt/data/lpf_goal/verified_3series_34.csv',index=False)
# Independent modified nodal analysis for sample frequencies.
def independent(xx,f):
 w=2*np.pi*f*1e6;L=xx[:4];C=xx[4:8];k=xx[8:]
 K=np.eye(4)
 pairs=[(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
 for l,(a,b) in enumerate(pairs):K[a,b]=K[b,a]=k[l]
 z=np.diag(w*L*1e-9/25)+1j*w*(np.sqrt(np.outer(L,L))*K)*1e-9
 z[1,1]+=(1/80-1j)/(w*C[1]*1e-12)
 Y=np.zeros((4,4),complex)
 for ci,a,b in [(0,0,1),(2,2,3),(3,1,2)]:
  yc=1/((1/80-1j)/(w*C[ci]*1e-12))
  Y[a,a]+=yc;Y[b,b]+=yc;Y[a,b]-=yc;Y[b,a]-=yc
 Y[0,0]+=1/50;Y[-1,-1]+=1/(60-40j)
 mat=np.block([[Y,B.T],[-B,z]])
 rhs=np.zeros(8,dtype=complex);rhs[0]=1/50
 v=np.linalg.solve(mat,rhs)
 eta=4*50*(60/5200)*abs(v[3])**2
 return -10*np.log10(eta)
for index,f in [(0,617.),(0,2094.),(2,803.),(5,960.),(5,2745.)]:
 xx=np.r_[x[:4],x[10+4*index:14+4*index],x[4:10]]
 a=transfer(xx,np.array([f]),B,ser,eds,Q)[0];b=independent(xx,f)
 print('INDEPENDENT',e.NAMES[index],f,a,b,'diff',a-b,flush=True)
# Coupling sensitivity on L2-L3 main pair (index k=3), and L1-L4 (index k=2)
checks=[]
for kt,loc,step in [('k14',2,.01),('k23',3,.01),('L_all',None,.01),('C_all',None,.01)]:
 for signed in [-1,1]:
  mm=[]
  for i,name in enumerate(e.NAMES):
   xx=np.r_[x[:4],x[10+4*i:14+4*i],x[4:10]].copy()
   if loc is not None:xx[8+loc]+=signed*step
   elif kt=='L_all':xx[:4]*=1+signed*step
   elif kt=='C_all':xx[4:8]*=1+signed*step
   band=BANDS[name]
   pp=np.unique(np.concatenate([np.linspace(a,b,17) for a,b in band['ul']+band['dl']]))
   h2=np.unique(np.concatenate([np.linspace(2*a,2*b,17) for a,b in band['ul']]))
   h3=np.unique(np.concatenate([np.linspace(3*a,3*b,17) for a,b in band['ul']]))
   mm.append((max(transfer(xx,pp,B,ser,eds,Q)),min(transfer(xx,h2,B,ser,eds,Q)),min(transfer(xx,h3,B,ser,eds,Q))))
  checks.append(dict(parameter=kt,variation=signed*step,max_IL=max(z[0] for z in mm),min_H2=min(z[1] for z in mm),min_H3=min(z[2] for z in mm)))
  print('SENS',checks[-1],flush=True)
pd.DataFrame(checks).to_csv('/mnt/data/lpf_goal/sensitivity_3series.csv',index=False)
json.dump({'design':S,'dense_bands':rows,'sensitivity':checks},open('/mnt/data/lpf_goal/confirmed_3series.json','w'),indent=2)
