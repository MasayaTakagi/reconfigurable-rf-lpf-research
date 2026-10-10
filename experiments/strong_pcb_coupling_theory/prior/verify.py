import os,json,csv,sys,numpy as np
from scipy.optimize import minimize_scalar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from weak_search import tr, getB, getpsd, SER, CE, COUPLES, NAMES
from explore import BANDS, three_series, transfer
root=os.path.dirname(os.path.abspath(__file__))
records=json.load(open(root+'/results.json'))
best=min((r for r in records if r['good']),key=lambda d:d['IL']); base=json.load(open(root+'/first.json'))
print('BEST',best['IL'],best['H2'],best['H3'],best['edges'],best['cp'],flush=True)
B4,ser4,ce4=three_series(2)

def frequencies(intervals,interval=.02,factor=1):
 return np.unique(np.concatenate([np.linspace(a*factor,b*factor, int(round((b-a)*factor/interval))+1) for a,b in intervals]))

def resp(r,j,f):
 x=np.array(r['x']);n=len(r['edges']);N=len(r['extraC']);d=4+n+N
 C=x[10+2*n+j*d:10+2*n+(j+1)*d]
 return tr(x[:4],x[4:10],x[10:10+n],x[10+n:10+2*n],C,np.asarray(f,dtype=np.float64),getB(r['edges']),np.asarray(r['extraC'],dtype=np.int64).reshape(-1,2),np.asarray(r['cp'],dtype=np.int64),n,N)

def respbase(j,f):
 x=np.array(base['x']);xx=np.r_[x[:4],x[10+4*j:10+4*j+4],x[4:10]]
 return transfer(xx,np.asarray(f,dtype=np.float64),B4,ser4,ce4,np.array([25.,25.,25.,25.,80.]))

rows=[]
for j,name in enumerate(NAMES):
 b=BANDS[name];p=frequencies(b['ul']+b['dl']);h2=frequencies(b['ul'],factor=2);h3=frequencies(b['ul'],factor=3)
 for mode,f,fn in [('PASS',p,max),('H2',h2,min),('H3',h3,min)]:
  y=resp(best,j,f);yb=respbase(j,f)
  ind=int(np.argmax(y) if mode=='PASS' else np.argmin(y));indb=int(np.argmax(yb) if mode=='PASS' else np.argmin(yb))
  rows.append(dict(case=name,band=mode,new_value_dB=float(y[ind]),new_extreme_MHz=float(f[ind]),baseline_value_dB=float(yb[indb]),baseline_extreme_MHz=float(f[indb])))
  print(name,mode,'new',round(y[ind],6),'old',round(yb[indb],6),flush=True)
with open(root+'/dense_verification.csv','w',newline='') as g:
 w=csv.DictWriter(g,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

# make compact performance
counts={0:[base['IL'],base['H2'],base['H3']]}
for n in (1,2,3,4):
 rs=[r for r in records if len(r['edges'])==n and r['good']]
 if rs:
  rr=min(rs,key=lambda r:r['IL']);counts[n]=[rr['IL'],rr['H2'],rr['H3']]
with open(root+'/topology_summary.csv','w',newline='') as g:
 w=csv.writer(g);w.writerow(['PCB_L_count','total_L','total_C','max_IL_dB','min_H2_dB','min_H3_dB'])
 for n,(il,h2,h3) in counts.items():w.writerow([n,4+n,4+n,il,h2,h3])

# cap values tables
n=len(best['edges']); d=4+n+len(best['extraC']);x=np.array(best['x']);
with open(root+'/best_components.csv','w',newline='') as g:
 w=csv.writer(g);w.writerow(['parameter','value','unit'])
 for i,v in enumerate(x[:4]):w.writerow([f'L{i+1}_CHIP',v,'nH'])
 for pair,v in zip(['k12','k13','k14','k23','k24','k34'],x[4:10]):w.writerow([pair,v,''])
 for i in range(n):w.writerow([f'PCB_L{i+5}_edge_{best["edges"][i]}',x[10+i],'nH'])
 for i in range(n):w.writerow([f'k_PCB_L{i+5}_to_chip_{best["cp"][i]+1}',x[10+n+i],''])
with open(root+'/best_band_caps.csv','w',newline='') as g:
 w=csv.writer(g);w.writerow(['case']+[f'C{i+1}_pF' for i in range(d)])
 for i,name in enumerate(NAMES):w.writerow([name]+list(x[10+2*n+i*d:10+2*n+(i+1)*d]))

# frequency chart B8
j=5
fig,axes=plt.subplots(3,1,figsize=(8.7,8),constrained_layout=True)
for ax,band,mode in zip(axes,[BANDS['B8']['ul']+BANDS['B8']['dl'],BANDS['B8']['ul'],BANDS['B8']['ul']],['pass','h2','h3']):
 mul={'pass':1,'h2':2,'h3':3}[mode]
 f=frequencies(band,interval=.1,factor=mul)
 ax.plot(f,respbase(j,f),label='4-chip-L reference',linewidth=1.8)
 ax.plot(f,resp(best,j,f),label='3-PCB-L weak coupling',linewidth=1.8)
 if mode!='pass':ax.axhline(35.,ls='--',color='grey',alpha=.7,label='35 dB target')
 ax.set_ylabel('IL / attenuation (dB)');ax.set_xlabel('Frequency (MHz)');ax.grid(True,alpha=.25)
 ax.set_title({'pass':'B8 UL + DL: insertion loss','h2':'B8 UL second harmonic','h3':'B8 UL third harmonic'}[mode])
 ax.legend(loc='best',fontsize=8)
fig.savefig(root+'/response_B8.png',dpi=160)
plt.close(fig)
fig,ax=plt.subplots(figsize=(7.6,4.8)); ns=list(counts.keys()); ils=[counts[k][0] for k in ns]
ax.plot(ns,ils,'-o');ax.set_xticks(ns);ax.set_xlabel('Number of additional buried PCB-L branches');ax.set_ylabel('6-case worst insertion loss (dB)');ax.grid(True,alpha=.3);fig.tight_layout();fig.savefig(root+'/pcb_count_tradeoff.png',dpi=160);plt.close(fig)

# component power loss with Vsrc=1V and P_avs=5mW

def power(r,b=5,f=960.0):
 x=np.array(r['x']);n=len(r['edges']);nc=len(r['extraC']);D=4+n+nc; C=x[10+2*n+b*D:10+2*n+(b+1)*D]
 B=getB(r['edges']);w=2*np.pi*f*1e6;Z=np.zeros((4+n,4+n),complex)
 for i in range(4):
  Z[i,i]=w*x[i]*1e-9*(1j+1/25.)
  if SER[i]:Z[i,i]+=(1/80-1j)/(w*C[i]*1e-12)
 for z,(a,bb) in zip(x[4:10],COUPLES):
  zz=1j*w*z*np.sqrt(x[a]*x[bb])*1e-9;Z[a,bb]=Z[bb,a]=zz
 for i in range(n):
  ii=4+i;lp=x[10+i];Z[ii,ii]=w*lp*1e-9*(1j+1/12.)+(1/80-1j)/(w*C[ii]*1e-12)
  ci=r['cp'][i];zz=1j*w*x[10+n+i]*np.sqrt(x[ci]*lp)*1e-9;Z[ii,ci]=Z[ci,ii]=zz
 Y=B.T@np.linalg.solve(Z,B)
 lossC=[]
 for jj in range(len(CE)):
  ci,a,bb=CE[jj];yy=w*C[ci]*1e-12/(1/80-1j)
  Y[a,a]+=yy;Y[bb,bb]+=yy;Y[a,bb]-=yy;Y[bb,a]-=yy
 for jj,edge in enumerate(r['extraC']):
  a,bb=edge; yy=w*C[4+n+jj]*1e-12/(1/80-1j)
  if a>=0:Y[a,a]+=yy
  if bb>=0:Y[bb,bb]+=yy
  if a>=0 and bb>=0:Y[a,bb]-=yy;Y[bb,a]-=yy
 Y[0,0]+=1/50.;Y[3,3]+=1/(60-40j);rhs=np.zeros(4,complex);rhs[0]=1/50.
 v=np.linalg.solve(Y,rhs);I=np.linalg.solve(Z,B@v)
 lps=np.array([200*1000*(w*x[i]*1e-9/25.)*abs(I[i])**2 for i in range(4)]+[200*1000*(w*x[10+i]*1e-9/12.)*abs(I[4+i])**2 for i in range(n)])
 cpower=[]
 for i in range(4):
  if SER[i]:cpow=200*1000*abs(I[i])**2/(80*w*C[i]*1e-12)
  else:
   a,bb=[(0,1),(2,-1),(2,3),(1,2)][i] if False else (0,0)
   # use capacitor edges from original CE
   _,a,bb=next(vv for vv in CE if vv[0]==i)
   VV=(v[a] if a>=0 else 0)-(v[bb] if bb>=0 else 0)
   cpow=200*1000*abs(VV)**2*np.real(w*C[i]*1e-12/(1/80-1j))
  cpower.append(cpow)
 for i in range(n):cpower.append(200*1000*abs(I[4+i])**2/(80*w*C[4+i]*1e-12))
 for jj,(a,bb) in enumerate(r['extraC']):
  VV=(v[a] if a>=0 else 0)-(v[bb] if bb>=0 else 0)
  cpower.append(200*1000*abs(VV)**2*np.real(w*C[4+n+jj]*1e-12/(1/80-1j)))
 return dict(lps=lps.tolist(),caps=cpower,reflection_mW=float(abs(2*v[0]-1)**2*1000),load_mW=float(200*1000*abs(v[3])**2*(60/5200)),total_diss_mW=float(sum(lps)+sum(cpower)))

# calculate baseline as no PCB branches, with matching stored vector
b0=dict(x=base['x'],edges=[],cp=[],extraC=[])
p0=power(b0);pn=power(best)
with open(root+'/B8_960_power.csv','w',newline='') as g:
 w=csv.writer(g);w.writerow(['term','4_chip_baseline_mW','3_PCB_weak_mW'])
 for i in range(4):w.writerow([f'Chip_L{i+1}',p0['lps'][i],pn['lps'][i]])
 for i in range(n):w.writerow([f'PCB_L{i+5}',0,pn['lps'][4+i]])
 w.writerow(['all_C',sum(p0['caps']),sum(pn['caps'])]);w.writerow(['dissipation_total',p0['total_diss_mW'],pn['total_diss_mW']]);w.writerow(['reflection',p0['reflection_mW'],pn['reflection_mW']]);w.writerow(['load_power',p0['load_mW'],pn['load_mW']]);
print('POWER',p0,pn,flush=True)
# C+/- 0.01 pF and kchipPCB to 0 safety / sensitivity
sens=[]
for tag,p in [('nominal',x.copy()),('all_C_+0.01pF',x.copy()),('all_C_-0.01pF',x.copy()),('chip_PCB_k_zero',x.copy())]:
 if tag=='all_C_+0.01pF':p[10+2*n:]+=0.01
 if tag=='all_C_-0.01pF':p[10+2*n:]=np.maximum(.01,p[10+2*n:]-0.01)
 if tag=='chip_PCB_k_zero':p[10+n:10+2*n]=0
 r={**best,'x':p.tolist()};out=[]
 for j,nam in enumerate(NAMES):
  bb=BANDS[nam];f1=frequencies(bb['ul']+bb['dl'],interval=.25);f2=frequencies(bb['ul'],interval=.25,factor=2);f3=frequencies(bb['ul'],interval=.25,factor=3)
  out.append((max(resp(r,j,f1)),min(resp(r,j,f2)),min(resp(r,j,f3))))
 sens.append([tag,max(k[0] for k in out),min(k[1] for k in out),min(k[2] for k in out)])
with open(root+'/fixed_value_sensitivity.csv','w',newline='') as g:
 w=csv.writer(g);w.writerow(['change','max_IL_dB','min_H2_dB','min_H3_dB']);w.writerows(sens)
print('SENS',sens,flush=True)
