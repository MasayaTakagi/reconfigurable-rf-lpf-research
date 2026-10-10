import os,json,numpy as np,csv
from independent_verify import response_full
from prior.explore import COUPLES
from prior.weak_search import SER,BCH
root=os.path.dirname(__file__)
base=json.load(open(root+'/base_search.json'))
old=min([r for r in base if r.get('feasible') and r.get('topology')=='3series_middle'],key=lambda r:r['IL'])

def oldpower(x,b,f):
 L=np.array(x[:4]);K=x[4:10]; C=x[10+4*b:14+4*b];w=2*np.pi*f*1e6
 Z=np.zeros((4,4),complex)
 for i in range(4):
  Z[i,i]=w*L[i]*1e-9*(1j+1/25)
  if SER[i]:Z[i,i]+=(1/80-1j)/(w*C[i]*1e-12)
 for k,(a,c) in zip(K,COUPLES): Z[a,c]=Z[c,a]=1j*w*k*np.sqrt(L[a]*L[c])*1e-9
 Y=BCH.T@np.linalg.solve(Z,BCH)
 zcaps=[]
 for cc,a,c in ((0,0,1),(2,2,3),(3,1,2)):
  z=(1/80-1j)/(w*C[cc]*1e-12)
  zcaps.append((cc,a,c,z));
  yy=1/z;Y[a,a]+=yy;Y[c,c]+=yy;Y[a,c]-=yy;Y[c,a]-=yy
 Y[0,0]+=1/50;Y[3,3]+=1/(60-40j)
 bvec=np.zeros(4,complex);bvec[0]=1/50
 v=np.linalg.solve(Y,bvec);i=np.linalg.solve(Z,BCH@v)
 pl=np.abs(i)**2*w*L*1e-9/25
 pc=np.zeros(4)
 pc[1]=abs(i[1])**2*(1/(w*C[1]*1e-12)/80)
 for ci,a,c,z in zcaps:pc[ci]=abs(v[a]-v[c])**2*np.real(1/z)
 load=abs(v[3])**2*60/5200;ref=abs(v[0]-.5)**2/50
 return dict(chip=pl*200, pcb=np.zeros(3),cap=pc*200,ref=ref*200,load=load*200)

if __name__=='__main__':
 new=json.load(open(root+'/stack_k_sensitivity.json'))
 rows=[]
 for b,f in [(0,698),(2,803),(5,960)]:
  oldr=oldpower(old['x'],b,f)
  def row(name,r):return dict(band=['B71','B12','B28','B13+14','B26','B8'][b],freq=f,name=name,**{q:(sum(r[q]) if hasattr(r[q],'__len__') else r[q]) for q in ('chip','pcb','cap','ref','load')},P_L1=r['chip'][0],P_L2=r['chip'][1],P_L3=r['chip'][2],P_L4=r['chip'][3])
  rows.append(row('4-chip base',oldr))
  for rec in new:
   if rec['k'] not in (.95,.98):continue
   pp=response_full(np.array(rec['x']),rec['k'],f,b,detail=True)
   r=dict(chip=np.array(pp['Pchip'])*200,pcb=np.array(pp['Ppcb'])*200,cap=np.array(pp['Pcap'])*200,ref=pp['Pref']*200,load=pp['Pload']*200)
   rows.append(row('3 PCB stack k='+str(rec['k']),r))
 for r in rows:print(r)
 with open(root+'/power_comparison_mW.csv','w') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
