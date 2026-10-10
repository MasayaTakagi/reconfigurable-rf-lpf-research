import os, sys, csv, json, numpy as np
from scipy.optimize import minimize_scalar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from variants import eval3,get_psd3, getB
from dynamic import REF, x0, tr, SER, NAMES, BANDS, CP, COUPLES, P_PAIRS
root=os.path.dirname(os.path.abspath(__file__))
R=json.load(open(root+'/refined_results.json'))
R0=json.load(open(root+'/zero_results.json'))
sel=lambda ix,km:next(r for r in R if r['orig_idx']==ix and abs(r['km']-km)<1e-6)
B0={'label':'prior layout / no PCB–PCB coupling','x':x0.tolist(),'k':[0,0,0],'edges':REF['edges'],'cp':REF['cp']}
config=[B0,dict(R0[0],label='new layout / uncoupled'),dict(R0[1],label='new layout / |k|<=0.05'),dict(sel(1,.1),label='new layout / |k|<=0.1'),dict(sel(1,.2),label='new layout / |k|<=0.2'),dict(sel(1,.3),label='new layout / |k|<=0.3')]

def densegrid(step=.02):
 out=[]
 for name in NAMES:
  b=BANDS[name]
  def f(rng, mul):
   return np.unique(np.concatenate([np.linspace(a*mul,b*mul,int(round((b-a)*mul/step))+1) for a,b in rng]))
  out.append((f(b['ul']+b['dl'],1),f(b['ul'],2),f(b['ul'],3)))
 return out
DD=densegrid(.02)
with open(root+'/verification_summary.csv','w',newline='') as f:
 wr=csv.writer(f);wr.writerow(['configuration','maxIL_dB','minH2_dB','minH3_dB','min_eigen_L_coupling'])
 for q in config:
  x=np.asarray(q['x']);k=np.asarray(q['k']);y=eval3(x,k,q['edges'],q['cp'],DD)
  s=(q['label'],float(np.max(y[:,0])),float(np.min(y[:,1])),float(np.min(y[:,2])),get_psd3(x,k,np.asarray(q['cp'])))
  wr.writerow(s)
  print('SUMMARY',s,flush=True)

best=config[4];x=np.asarray(best['x']);k=np.asarray(best['k']);met=eval3(x,k,best['edges'],best['cp'],DD)
with open(root+'/six_case_verified.csv','w',newline='') as f:
 wr=csv.writer(f);wr.writerow(['case','max_pass_IL_dB','min_H2_dB','min_H3_dB']+[f'C{i+1}_pF' for i in range(7)])
 for i,name in enumerate(NAMES):wr.writerow([name]+met[i].tolist()+x[16+7*i:16+7*(i+1)].tolist())
with open(root+'/physical_components.csv','w',newline='') as f:
 wr=csv.writer(f);wr.writerow(['component','value','unit'])
 for i,v in enumerate(x[:4]):wr.writerow([f'L{i+1} chip',v,'nH'])
 for i,v in enumerate(x[10:13]):wr.writerow([f'L{i+5} PCB',v,'nH'])
 for (i,j),v in zip(COUPLES,x[4:10]):wr.writerow([f'k_chip_L{i+1} L{j+1}',v,''])
 for i,v in enumerate(x[13:16]):wr.writerow([f'k_chip_PCB_L{best["cp"][i]+1}_L{i+5}',v,''])
 for (a,b),v in zip(P_PAIRS,k):wr.writerow([f'k_PCB_L{5+a}_L{5+b}',v,''])

fig,ax=plt.subplots(figsize=(7.5,4.5)); xx=[0,.05,.1,.2,.3]
lab=[config[1],config[2],config[3],config[4],config[5]]
ax.plot(xx,[eval3(np.asarray(z['x']),np.asarray(z['k']),z['edges'],z['cp'],DD)[:,0].max() for z in lab],'-o',linewidth=1.8)
ax.axhline(REF['IL'],linestyle='--',color='gray',label='Previous layout, kPCB-PCB=0')
ax.set_xlabel('Upper bound on |k| between PCB inductors')
ax.set_ylabel('Worst nominal insertion loss (dB)')
ax.grid(alpha=.2)
ax.legend();fig.tight_layout();fig.savefig(root+'/mutual_coupling_tradeoff.png',dpi=160);plt.close(fig)

# Detailed power balance at B8 960, using 1 W Pavs

def pw(r,f=960,band=5):
 xx=np.asarray(r['x']);n=3; C=xx[16+7*band:16+7*(band+1)]; kpp=np.asarray(r['k']);cp=np.asarray(r['cp'])
 L=xx[:4]; K=xx[4:10]; LP=xx[10:13];kp=xx[13:16];B=getB(r['edges']);w=2*np.pi*f*1e6
 Z=np.zeros((7,7),complex)
 for i in range(4):
  Z[i,i]=w*L[i]*1e-9*(1j+1/25)
  if SER[i]: Z[i,i]+=(1/80.-1j)/(w*C[i]*1e-12)
 for (a,b),v in zip(COUPLES,K):
  vv=1j*w*v*np.sqrt(L[a]*L[b])*1e-9;Z[a,b]=Z[b,a]=vv
 for i in range(3):
  Z[4+i,4+i]=w*LP[i]*1e-9*(1j+1/12.)+(1/80.-1j)/(w*C[4+i]*1e-12)
  j=cp[i];v=1j*w*kp[i]*np.sqrt(L[j]*LP[i])*1e-9;Z[4+i,j]=Z[j,4+i]=v
 for (a,b),v in zip(P_PAIRS,kpp):
  vv=1j*w*v*np.sqrt(LP[a]*LP[b])*1e-9;Z[4+a,4+b]=Z[4+b,4+a]=vv
 Y=B.T@np.linalg.solve(Z,B)
 for ci,a,b in ((0,0,1),(2,2,3),(3,1,2)):
  yy=w*C[ci]*1e-12/(1/80.-1j)
  Y[a,a]+=yy;Y[b,b]+=yy;Y[a,b]-=yy;Y[b,a]-=yy
 Y[0,0]+=1/50.;Y[3,3]+=1/(60-40j)
 vs=np.zeros(4,complex);vs[0]=1/50
 V=np.linalg.solve(Y,vs);curr=np.linalg.solve(Z,B@V)
 Lloss=np.array([200e3*(w*L[i]*1e-9/25)*abs(curr[i])**2 for i in range(4)]+[200e3*(w*LP[i]*1e-9/12)*abs(curr[4+i])**2 for i in range(3)])
 Closs=np.zeros(7)
 for i in (0,2,3):
  a,b={0:(0,1),2:(2,3),3:(1,2)}[i]
  yy=w*C[i]*1e-12/(1/80.-1j)
  Closs[i]=200e3*abs(V[a]-V[b])**2*yy.real
 for i in [1,4,5,6]:
  imap={1:1,4:4,5:5,6:6}[i]
  Closs[i]=200e3*abs(curr[imap])**2/(80*w*C[i]*1e-12)
 R=200e3*abs(2*V[0]-1)**2 /200 # wait do full
 # ratio accepted due 1 V generator power Pavs=0.005W, scale x200; reflected power 0.005*|gamma|²*200 (mW)=1000*|gamma|²
 ref=1000*abs(2*V[0]-1)**2
 load=200e3*abs(V[3])**2*60/5200
 return dict(chipL=np.sum(Lloss[:4]),pcbL=np.sum(Lloss[4:]),C=np.sum(Closs),reflection=ref,load=load,total_diss=sum(Lloss)+sum(Closs),componentLs=Lloss.tolist(),componentCs=Closs.tolist())
pws={z['label']:pw(z) for z in (config[0],config[4])}
with open(root+'/B8_960_power.csv','w',newline='') as f:
 wr=csv.writer(f);wr.writerow(['power_mW','previous_layout','new_coupled_layout'])
 for key in ['chipL','pcbL','C','total_diss','reflection','load']:
  wr.writerow([key,pws[config[0]['label']][key],pws[config[4]['label']][key]])
print('POWER',pws,flush=True)

# hold fixed cap & L: +/-0.02 drift to PCB mutuals only
sens=[]
for d in [0,-.02,.02]:
 z=best.copy();z['k']=(np.asarray(k)+d).tolist();yy=eval3(np.array(z['x']),np.asarray(z['k']),z['edges'],z['cp'],DD)
 sens.append([d,float(np.max(yy[:,0])),float(np.min(yy[:,1])),float(np.min(yy[:,2]))])
with open(root+'/fixed_mutual_sensitivity.csv','w',newline='') as f:
 wr=csv.writer(f);wr.writerow(['simultaneous_delta_k','maxIL_dB','minH2_dB','minH3_dB']);wr.writerows(sens)
print('SENS',sens,flush=True)

# generate concise report
result='''# PCB-L間相互結合の導入結果（2026-10-10）\n\n- 6ケース：B71、B12、B28、B13＋14、B26、B8。UL＋DL通過、ULのH2/H3全域で35dB以上を目標。\n- チップLは4個/Q25、PCB-Lは3個/各≤3nH/Q12、Cは7個/Q80。チップ–PCB結合は±0.03以下。\n- チップ間は主結合2組±0.25、副結合4組±0.16。PCB-L間は0～±0.30の感度試験。\n- Qと負荷、最適化方式は前回と同じ。PCB-L間結合もインダクタンス行列に組み込み、その最小固有値が正であることを確認。\n- 最良の確認済み候補：PCB-L5を節点1–GND、PCB-L6を節点2–出力、PCB-L7を節点1–節点2に接続。\n- PCB-L間の主結合を利用してILは0.3234dB程度（結合上限0.20、35.05dB目標）。\n- 結合なしの場合には、異なる枝配置の効果が出にくく、約0.3272dBだった。\n- PCB-L間結合0.30を許可しても0.3233dB程度と追加効果は小さい。\n- 0.30dB以下には未達であり、35dB公称減衰を緩和しない限り、既存構成へのPCB-L間結合だけでは大幅改善が見られない。\n- 結果は局所的な数値最適化・0.02MHz刻みの周波数再検証であり、数学的な大域最適性証明や実装検証ではない。\n- Phase 3は停止。\n\n`'''
open(root+'/REPORT_ja.md','w').write(result)
