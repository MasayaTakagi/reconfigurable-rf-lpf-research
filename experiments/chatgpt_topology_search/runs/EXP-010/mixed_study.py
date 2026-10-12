#!/usr/bin/env python3
"""EXP-010 Q25/80/40 nominal Phase 2 local topology search, no global guarantee.
Source+load fixed 50ohm / 60-j40ohm; 6 band UL/DL worst IL and H2/H3
minimum attenuation. Includes fixed PCB-pattern capacitors (0.02..0.2pF).
Fixed L, fixed C, coupling shared among six settings; three IC C values per case.
Chip area 4*LQP02HQ + 3*GJM01 = 6. All couplings only adjacent in chip row.
"""
import argparse,csv,hashlib,json,os,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SOURCE=HERE/'EXP010-02.json'
BANDS=ROOT/'data/bands.csv'
POLICY=ROOT/'data/design_constraints.json'
CASES=('B71','B12','B28','B13+B14','B26','B8')
CHIP_EDGES=((0,1),(2,3),(1,4),(1,2))
CHIP_ROW=(1,2,3,0)
GJM_EDGES=((0,2),(4,-1),(0,1))
PCB_EDGES=((2,3),)
VAR_EDGES=((3,-1),(4,-1),(1,2))
ALL_EDGES=tuple((a,b) for a in range(5) for b in range(a+1,5))+tuple((a,-1) for a in range(5))

def outer(edge):
    v=np.zeros(5)
    for n,s in zip(edge,(1,-1)):
        if n>=0:v[n]+=s
    return np.outer(v,v)

def jobs(family):
    original={'id':0,'name':'saved_EXP010_02','family':'baseline',
              'gjm_edges':GJM_EDGES,'pcb_edges':PCB_EDGES,'variable_edges':VAR_EDGES}
    if family=='baseline':return [original]
    out=[]
    if family=='pcb_move':
        for e in ALL_EDGES:
            if e==PCB_EDGES[0]:continue
            out.append({'name':f'PCB_{e[0]}_{e[1]}','family':family,'gjm_edges':GJM_EDGES,
                        'pcb_edges':(e,),'variable_edges':VAR_EDGES})
    elif family=='gjm_move':
        for e in ALL_EDGES:
            if e in GJM_EDGES:continue
            out.append({'name':f'GJM_Cf3_{e[0]}_{e[1]}','family':family,
                        'gjm_edges':GJM_EDGES[:2]+(e,),'pcb_edges':PCB_EDGES,'variable_edges':VAR_EDGES})
    elif family=='second_pcb':
        for e in ALL_EDGES:
            if e in PCB_EDGES:continue
            out.append({'name':f'PCB2_{e[0]}_{e[1]}','family':family,
                        'gjm_edges':GJM_EDGES,'pcb_edges':PCB_EDGES+(e,),'variable_edges':VAR_EDGES})
    else:raise ValueError(family)
    for i,j in enumerate(out):j['id']=i
    return out

class Model:
    def __init__(self,job,bands):
        self.job=job;self.npcb=len(job['pcb_edges'])
        self.B=np.zeros((5,4))
        for i,(a,b) in enumerate(CHIP_EDGES):self.B[a,i]+=1;self.B[b,i]-=1
        self.Dgjm=np.array([outer(e) for e in job['gjm_edges']])
        self.Dpcb=np.array([outer(e) for e in job['pcb_edges']])
        self.Dvar=np.array([outer(e) for e in job['variable_edges']])
        self.ports=np.zeros((5,5),complex)
        self.ports[0,0]=1/50;self.ports[2,2]=1/(60-40j)
        self.source=np.array([1/50,0,0,0,0],complex)
        self.bands=bands;self.grids_cache={}
    def bounds(self):
        return ([(np.log(.4),np.log(56))]*4+[(np.log(.1),np.log(100))]*3+
                [(np.log(.02),np.log(.2))]*self.npcb+[(-.4,.4)]*3+[(0,4)]*18+[(0,1.5)])
    def grids(self,N):
        if N not in self.grids_cache:
            self.grids_cache[N]=[[np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),N)*2*np.pi*1e6
                for r in self.bands if r['case']==case and r['region'] in region])
                for region in (('UL','DL'),('H2',),('H3',))] for case in CASES]
        return self.grids_cache[N]
    def metrics(self,x,N):
        l=np.exp(x[:4])*1e-9;cg=np.exp(x[4:7])*1e-12
        cp=np.exp(x[7:7+self.npcb])*1e-12
        k=x[7+self.npcb:10+self.npcb]
        var=x[10+self.npcb:-1].reshape(6,3)*1e-12
        M=np.diag(l.astype(complex));K=np.eye(4)
        for j,ki in enumerate(k):
            a,b=CHIP_ROW[j:j+2]
            K[a,b]=K[b,a]=ki;M[a,b]=M[b,a]=ki*np.sqrt(l[a]*l[b])
        if np.linalg.eigvalsh(K).min()<=1e-6:return np.full((6,3),1000.)
        coil=self.B@np.linalg.solve(np.diag(l/25)+1j*M,self.B.T)
        Yfixed=(np.einsum('i,ijk->jk',cg/(1/80-1j),self.Dgjm)+
                np.einsum('i,ijk->jk',cp/(1/40-1j),self.Dpcb))
        Yvar=np.einsum('si,ijk->sjk',var/(1/80-1j),self.Dvar)
        result=np.empty((6,3))
        for ci,regions in enumerate(self.grids(N)):
            Ycap=Yfixed+Yvar[ci]
            for typ,omega in enumerate(regions):
                Y=self.ports[None,:,:]+coil[None,:,:]/omega[:,None,None]+omega[:,None,None]*Ycap[None,:,:]
                v=np.linalg.solve(Y,np.broadcast_to(self.source,(len(omega),5))[...,None])[...,0]
                att=-10*np.log10(np.maximum(200*60/5200*np.abs(v[:,2])**2,1e-300))
                result[ci,typ]=att.max() if typ==0 else att.min()
        return result

def reference_vector(d,npcb=1):
    top=d['topology']
    l=np.log([z['L_nH'] for z in top['inductors']])
    cg=np.log([z['C_pF'] for z in top['fixed_capacitors']])
    cp=np.log([z['C_pF'] for z in top['pcb_pattern_capacitors']])
    if npcb>1:cp=np.r_[cp,np.log([.02001]*(npcb-1))]
    k=np.array(top['signed_adjacent_k'])
    var=np.array([d['variable_C_pf_by_setting'][c] for c in CASES]).ravel()
    return np.r_[l,cg,cp,k,var,.30]

def local_optimize(model,x0,N,target,iterations):
    bounds=model.bounds();cache=[None,None];calls=0;ts=time.monotonic()
    def metric(x):
        nonlocal calls
        if cache[0] is None or not np.array_equal(cache[0],x):
            cache[:]=[x.copy(),model.metrics(x,N)];calls+=1
        return cache[1]
    def constraints(x):
        a=metric(x)
        return np.r_[x[-1]-a[:,0],a[:,1]-target,a[:,2]-target]
    o=minimize(lambda x:x[-1],x0,method='SLSQP',bounds=bounds,
               constraints=[{'type':'ineq','fun':constraints}],
               options={'maxiter':iterations,'ftol':1e-9})
    a=model.metrics(o.x,201)
    return dict(x=o.x.tolist(),converged=bool(o.success),message=str(o.message),
                nit=int(o.nit),nfev=int(o.nfev),model_evaluations=calls,
                seconds=round(time.monotonic()-ts,3),
                worstIL201_db=float(a[:,0].max()),H2min201_db=float(a[:,1].min()),
                H3min201_db=float(a[:,2].min()),setting_metrics201=a.tolist(),
                independent_MNA_verified=False,global_optimum_proven=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--family',choices=['baseline','pcb_move','gjm_move','second_pcb'],default='baseline')
    p.add_argument('--reference-only',action='store_true')
    p.add_argument('--shard-count',type=int,default=1);p.add_argument('--shard-index',type=int,default=0)
    p.add_argument('--max-new-jobs',type=int,default=2);p.add_argument('--starts',type=int,default=1)
    p.add_argument('--iterations',type=int,default=300)
    p.add_argument('--points',type=int,default=13)
    p.add_argument('--atten',type=float,default=30.015)
    p.add_argument('--seed',type=int,default=20261012)
    p.add_argument('--checkpoint',type=Path)
    args=p.parse_args()
    assert args.shard_count>=1 and 0<=args.shard_index<args.shard_count
    assert args.starts>=1 and args.iterations>=1 and args.points>=3
    assert 30<=args.atten<=35 and args.max_new_jobs>=1
    original=json.loads(SOURCE.read_text())
    bands=list(csv.DictReader(BANDS.open(newline='')))
    ref_model=Model(jobs('baseline')[0],bands)
    result=ref_model.metrics(reference_vector(original),201)
    metrics=original['verified_dense_metrics']
    assert abs(result[:,0].max()-metrics['worst_IL_db'])<1e-6
    assert abs(result[:,1].min()-metrics['min_H2_db'])<1e-6
    assert abs(result[:,2].min()-metrics['min_H3_db'])<1e-6
    print('EXP010-02 reference reproduced, IL=',result[:,0].max(),flush=True)
    if args.reference_only:return
    candidates=jobs(args.family)
    data=SOURCE.read_bytes()+BANDS.read_bytes()+POLICY.read_bytes()+Path(__file__).read_bytes()
    settings={k:v for k,v in vars(args).items() if k not in ('checkpoint','max_new_jobs')}
    fingerprint=hashlib.sha256(data+json.dumps(settings,sort_keys=True).encode()).hexdigest()
    assigned=[job for job in candidates if job['id']%args.shard_count==args.shard_index]
    state={'fingerprint':fingerprint,'commit_sha':os.getenv('GITHUB_SHA','local'),
           'settings':settings,'assigned_count':len(assigned),'completed_ids':[],
           'results':[],'failures':[],'unfinished':True,'global_optimization_proven':False}
    if args.checkpoint and args.checkpoint.exists():
        prior=json.loads(args.checkpoint.read_text())
        if prior['fingerprint']!=fingerprint:raise RuntimeError('Checkpoint mismatch')
        state=prior
    clock=time.monotonic();done=0
    for job in assigned:
        if job['id'] in state['completed_ids']:continue
        if done>=args.max_new_jobs:break
        mod=Model(job,bands)
        for si in range(args.starts):
            seed=args.seed+10000*job['id']+si;rng=np.random.default_rng(seed)
            x=reference_vector(original,mod.npcb)
            if si:
                x[:4]+=rng.normal(0,.05,4)
                x[4:7+mod.npcb]+=rng.normal(0,.065,3+mod.npcb)
                x[7+mod.npcb:10+mod.npcb]+=rng.normal(0,.025,3)
                x[10+mod.npcb:-1]+=rng.normal(0,.05,18)
            bounds=np.array(mod.bounds());x=np.clip(x,bounds[:,0],bounds[:,1])
            try:state['results'].append({'job':job,'seed':seed,'result':local_optimize(mod,x,args.points,args.atten,args.iterations)})
            except Exception as e:state['failures'].append({'job_id':job['id'],'seed':seed,'error':repr(e)})
        state['completed_ids'].append(job['id']);done+=1
        state['unfinished']=len(state['completed_ids'])<len(assigned)
        state['run_seconds']=round(time.monotonic()-clock,2)
        if args.checkpoint:
            args.checkpoint.parent.mkdir(parents=True,exist_ok=True)
            path=args.checkpoint.with_suffix('.tmp');path.write_text(json.dumps(state,indent=2)+'\n');path.replace(args.checkpoint)
        valid=[r['result'] for r in state['results'] if min(r['result']['H2min201_db'],r['result']['H3min201_db'])>=30]
        print('completed',job['id'],job['name'],'of',len(assigned),'best_screening_IL',
              min([r['worstIL201_db'] for r in valid],default=None),flush=True)
    print('work complete',len(state['completed_ids']),'/',len(assigned),'failed',len(state['failures']),
          'unfinished',state['unfinished'],flush=True)
if __name__=='__main__':main()