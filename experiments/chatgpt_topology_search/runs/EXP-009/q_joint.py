#!/usr/bin/env python3
"""EXP009 illustrative L1-Q continuation with joint L/C/k and 6x3 C retuning.
This is a constant-Q-only hypothetical; no SRF/Q(f) or real component validation.
SLSQP nonconvex starts are NOT a proof of any theoretical IL or rejection bound.
"""
import argparse,csv,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from sweep import Model,jobs,CASES,BANDS

HERE=Path(__file__).resolve().parent
class QStressModel(Model):
 def __init__(self,job,bands,qL):
  super().__init__(job,bands)
  self.qL=np.array([25,float(qL),25,25])
 def metrics(self,x,n):
  L=np.exp(x[:4])*1e-9;C=np.exp(x[4:7])*1e-12;k=x[7:10]
  var=x[10:-1].reshape(6,self.nvar)*1e-12
  K=np.eye(4);M=np.diag(L.astype(complex))
  for i,z in enumerate(k):
   a,b=(1,2,3,0)[i:i+2];K[a,b]=K[b,a]=z;M[a,b]=M[b,a]=z*np.sqrt(L[a]*L[b])
  if np.linalg.eigvalsh(K).min()<=1e-5:return np.full((6,3),1000.)
  coil=self.B@np.linalg.solve(np.diag(L/self.qL)+1j*M,self.B.T)
  fixed=np.einsum('i,ijk->jk',C/(1/80-1j),self.Dfix)
  variable=np.einsum('si,ijk->sjk',var/(1/80-1j),self.Dvar)
  values=np.zeros((6,3))
  for ci,groups in enumerate(self.grids_for(n)):
   cy=fixed+variable[ci]
   for j,w in enumerate(groups):
    Y=self.ports[None,:,:]+coil[None,:,:]/w[:,None,None]+w[:,None,None]*cy[None,:,:]
    voltage=np.linalg.solve(Y,np.broadcast_to(self.src,(len(w),5))[...,None])[...,0]
    att=-10*np.log10(np.maximum(200*60/5200*np.abs(voltage[:,2])**2,1e-300))
    values[ci,j]=att.max() if j==0 else att.min()
  return values

def start_vector(ref):
 t=ref['topology']
 L=[v['L_nH'] for v in t['inductors']]
 C=[v['C_pF'] for v in t['fixed_capacitors']]
 k=t['signed_adjacent_k']
 tun=[ref['variable_C_pf_by_setting'][case] for case in CASES]
 return np.r_[np.log(L),np.log(C),k,np.array(tun).ravel(),.5]

def run(model,x0,target,maxiter=450,points=31,verification=7001):
 last=[None,None];evals=[0];t0=time.monotonic()
 def met(x):
  if last[0] is None or not np.array_equal(x,last[0]):
   last[0]=x.copy();last[1]=model.metrics(x,points);evals[0]+=1
  return last[1]
 def con(x):
  a=met(x);return np.r_[x[-1]-a[:,0],a[:,1]-target,a[:,2]-target]
 z=minimize(lambda v:v[-1],x0,method='SLSQP',bounds=model.bounds(),
   constraints=[{'type':'ineq','fun':con}],options={'maxiter':maxiter,'ftol':1e-9})
 a=model.metrics(z.x,verification)
 return {'x':z.x.tolist(),'solver_success':bool(z.success),'solver_message':str(z.message),
   'iterations':int(z.nit),'nfev':int(z.nfev),'model_evals':evals[0],
   'runtime_s':round(time.monotonic()-t0,3),'worst_IL_db':float(a[:,0].max()),
   'min_H2_db':float(a[:,1].min()),'min_H3_db':float(a[:,2].min()),
   'all_six_setting_metrics':a.tolist(),'finite_grid_points_per_interval':verification,
   'meets_minimum_30db':bool(a[:,1:].min()>=30.0),'global_optimum_proven':False,
   'independent_MNA_checked_here':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--iterations',type=int,default=450)
 p.add_argument('--points',type=int,default=31);p.add_argument('--target',type=float,default=30.022)
 p.add_argument('--output',type=Path,default=HERE/'q_joint_reproduction.json')
 args=p.parse_args()
 ref=json.loads((HERE/'EXP009-01.json').read_text())
 bands=list(csv.DictReader(BANDS.open(newline='')))
 job=next(z for z in jobs() if z['name']=='fixed_C2_to_2_3')
 x=start_vector(ref);results={}
 for q in [24,22,20,19]:
  m=QStressModel(job,bands,q);row=run(m,x,args.target,args.iterations,args.points)
  results[str(q)]={'L1_Q_hypothetical':q,**row}
  args.output.write_text(json.dumps(results,indent=2)+'\n')
  print('L1_Q',q,'IL',row['worst_IL_db'],'H2',row['min_H2_db'],'H3',row['min_H3_db'],
        'solver_success',row['solver_success'],flush=True)
  if min(row['min_H2_db'],row['min_H3_db'])>=29.99:x=np.array(row['x'])
if __name__=='__main__':main()