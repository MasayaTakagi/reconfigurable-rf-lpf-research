import os,json,numpy as np,csv
from stack_refine import response,metrics
from prior.explore import NAMES,COUPLES,grids,BANDS
root=os.path.dirname(__file__)
run=json.load(open(root+'/stack_k_sensitivity.json'))
# Complete seven-winding modified nodal analysis; 3 PCB coils connected in SERIES with two internal nodes.
def response_full(x,kp,freq,band,detail=False):
 w=2*np.pi*freq*1e6
 L=np.array(x[:4]);K=x[4:10];lp=x[10];C=x[11+4*band:15+4*band]
 L7=np.r_[L,[lp]*3]
 Z=np.zeros((7,7),complex)
 for n,l in enumerate(L7):Z[n,n]=w*l*1e-9*(1j+1./(25 if n<4 else 12))
 Z[1,1]+=((1/80)-1j)/(w*C[1]*1e-12)
 for m,(a,b) in enumerate(COUPLES): Z[a,b]=Z[b,a]=1j*w*K[m]*np.sqrt(L[a]*L[b])*1e-9
 for a,b in ((4,5),(4,6),(5,6)): Z[a,b]=Z[b,a]=1j*w*kp*lp*1e-9
 B=np.zeros((7,6),complex)
 edges=((0,1),(2,-1),(2,3),(1,2),(2,4),(4,5),(5,3))
 for j,(a,b) in enumerate(edges):
  if a>=0:B[j,a]=1
  if b>=0:B[j,b]=-1
 Y=B.T@np.linalg.solve(Z,B)
 Zc1=(1/80-1j)/(w*C[0]*1e-12)
 Zc3=(1/80-1j)/(w*C[2]*1e-12)
 Zc4=(1/80-1j)/(w*C[3]*1e-12)
 for a,b,z in ((0,1,Zc1),(2,3,Zc3),(1,2,Zc4)):
  y=1/z;Y[a,a]+=y;Y[b,b]+=y;Y[a,b]-=y;Y[b,a]-=y
 Y[0,0]+=1/50.;Y[3,3]+=1/(60-40j)
 rhs=np.zeros(6,complex);rhs[0]=1/50.
 V=np.linalg.solve(Y,rhs)
 i=np.linalg.solve(Z,B@V)
 pc=np.abs(i[:4])**2*w*L*1e-9/25.
 pp=np.abs(i[4:])**2*w*lp*1e-9/12.
 caps=[]
 for a,b,z in ((0,1,Zc1),(2,3,Zc3),(1,2,Zc4)):
  caps.append(abs(V[a]-V[b])**2*np.real(1/z))
 # chip L2's C2 ESR
 caps.insert(1,abs(i[1])**2*np.real((1/80-1j)/(w*C[1]*1e-12)))
 P_load=abs(V[3])**2*(60/5200)
 P_ref=abs(V[0]-.5)**2/50
 P_source=1/200.
 eta=P_load/P_source
 il=-10*np.log10(eta)
 if detail:return dict(il=float(il),Pload=float(P_load),Pref=float(P_ref),Pchip=pc.tolist(),Ppcb=pp.tolist(),Pcap=[float(t) for t in caps],balance=float((P_load+P_ref+sum(pc)+sum(pp)+sum(caps))/P_source),Ipcb=np.abs(i[4:]).tolist(),Vsource=V[0],Vload=V[3])
 return float(il)

if __name__=='__main__':
 xs=[];bands=[]
 for r in run:
  # 0.98/0.95/0.9 and maybe k=1.0
  if r['k'] not in (.98,.95,.9,1.0):continue
  x=np.array(r['x']);k=r['k']
  points=grids(251)
  allmetrics=[]
  for b,(fpass,h2,h3) in enumerate(points):
   A=np.array([response_full(x,k,f,b) for f in fpass])
   B=np.array([response_full(x,k,f,b) for f in h2]);C=np.array([response_full(x,k,f,b) for f in h3]);allmetrics.append([max(A),min(B),min(C)])
   calcB8=response_full(x,k,max(fpass),b,detail=True)
   bands.append({'k':k,'band':NAMES[b],'maxIL':max(A),'H2':min(B),'H3':min(C)})
  a=np.array(allmetrics)
  print('INDEPENDENT',k,'maxIL',max(a[:,0]),'minH2',min(a[:,1]),'minH3',min(a[:,2]),'balance at B8',response_full(x,k,960,5,detail=True)['balance'],flush=True)
  xs.append({'k':k,'maxIL':float(max(a[:,0])),'H2':float(min(a[:,1])),'H3':float(min(a[:,2])),'leff':r['leff'],'qeff':r['qeff'],'physicalL':x[:11].tolist(),'chip_k':x[4:10].tolist()})
 json.dump(xs,open(root+'/independently_verified.json','w'),indent=2)
 with open(root+'/stack_band_verified.csv','w') as f:
  w=csv.DictWriter(f,fieldnames=['k','band','maxIL','H2','H3']);w.writeheader();w.writerows(bands)
