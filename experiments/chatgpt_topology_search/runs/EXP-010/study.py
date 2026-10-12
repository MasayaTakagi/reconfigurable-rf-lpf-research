#!/usr/bin/env python3
"""Phase 2 EXP-010: Q=25 ideal LQP02HQ (0.4..56 nH) topology continuation.
Independent candidate regression in verify.py. This optimizer is local and nonconvex.
Only the permitted 3 IC C values vary across 6 settings; other components fixed.
"""
import argparse,csv,hashlib,importlib.util,json,os,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=HERE.parent/'EXP-009'
BANDS=ROOT/'data/bands.csv'
POLICY=ROOT/'data/design_constraints.json'
BASE=OLD/'EXP009-02.json'
CASES=('B71','B12','B28','B13+B14','B26','B8')

def load_engine():
    spec=importlib.util.spec_from_file_location('lpf_exp009_engine',OLD/'sweep.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Model

class ExtendModel:
    def __init__(self,lmax,bands):
        model_cls=load_engine()
        j={'fixed_edges':((0,2),(4,-1),(2,3)),
           'variable_edges':((3,-1),(4,-1),(1,2))}
        self.model=model_cls(j,bands)
        self.lmax=lmax
    def bounds(self):
        b=self.model.bounds()
        for i in range(4):b[i]=(np.log(.4),np.log(self.lmax))
        return b
    def metrics(self,x,points):return self.model.metrics(x,points)

def from_checkpoint(d):
    topo=d['topology']
    return np.r_[np.log([z['L_nH'] for z in topo['inductors']]),
                 np.log([z['C_pF'] for z in topo['fixed_capacitors']]),
                 topo['signed_adjacent_k'],
                 np.array([d['variable_C_pf_by_setting'][k] for k in CASES]).ravel(),.32]

def optimize(m,x0,points,atten,iterations):
    cached=[None,None];evaluations=0
    def metrics(x):
        nonlocal evaluations
        if cached[0] is not None and np.array_equal(cached[0],x):return cached[1]
        cached[0]=x.copy();cached[1]=m.metrics(x,points);evaluations+=1
        return cached[1]
    def constr(x):
        met=metrics(x)
        return np.r_[x[-1]-met[:,0],met[:,1]-atten,met[:,2]-atten]
    tick=time.monotonic()
    result=minimize(lambda x:x[-1],x0,method='SLSQP',bounds=m.bounds(),
              constraints=[{'type':'ineq','fun':constr}],
              options={'maxiter':iterations,'ftol':1e-9})
    valid=m.metrics(result.x,201)
    return {'x':result.x.tolist(),'solver_success':bool(result.success),'message':str(result.message),
            'iterations':int(result.nit),'nfev':int(result.nfev),'model_evaluations':evaluations,
            'seconds':round(time.monotonic()-tick,3),'verified_201_worst_IL_db':float(valid[:,0].max()),
            'verified_201_min_H2_db':float(valid[:,1].min()),'verified_201_min_H3_db':float(valid[:,2].min()),
            'full_grid_independent_validation':False,'global_optimum_proven':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--reference-only',action='store_true')
    p.add_argument('--max-l',type=float,default=56)
    p.add_argument('--starts',type=int,default=2)
    p.add_argument('--iterations',type=int,default=400)
    p.add_argument('--points',type=int,default=31)
    p.add_argument('--atten',type=float,default=30.02)
    p.add_argument('--seed',type=int,default=20261012)
    p.add_argument('--checkpoint',type=Path)
    args=p.parse_args()
    if not (.4<=args.max_l<=56 and 1<=args.starts<=64 and args.iterations>=1 and args.points>=3 and 30<=args.atten<=35):
        p.error('Invalid Phase 2 study settings')
    d=json.loads(BASE.read_text());bands=list(csv.DictReader(BANDS.open(newline='')))
    base_model=ExtendModel(56,bands)
    x=from_checkpoint(d)
    m=base_model.metrics(x,201)
    assert abs(m[:,0].max()-d['verified_dense_metrics']['worst_IL_db'])<1e-5
    assert abs(m[:,1].min()-d['verified_dense_metrics']['min_H2_db'])<1e-5
    assert abs(m[:,2].min()-d['verified_dense_metrics']['min_H3_db'])<1e-5
    print('EXP009-02 regression passed',float(m[:,0].max()),flush=True)
    if args.reference_only:return
    ck_hash=hashlib.sha256(BANDS.read_bytes()+POLICY.read_bytes()+BASE.read_bytes()+
      (HERE/'study.py').read_bytes()+json.dumps(vars(args)|{'checkpoint':None},sort_keys=True,default=str).encode()).hexdigest()
    state={'fingerprint':ck_hash,'commit_sha':os.environ.get('GITHUB_SHA','local'),
       'parameterization':'LQP02HQ Q25, <=56nH, 4 chip L+3 GJM+3 variable C, 6 settings',
       'start_count':args.starts,'completed_starts':[],'records':[],'failures':[],'unfinished':True}
    if args.checkpoint and args.checkpoint.exists():
        previous=json.loads(args.checkpoint.read_text())
        if previous['fingerprint']!=ck_hash:raise RuntimeError('Checkpoint source or settings changed')
        state=previous
    for s in range(args.starts):
        if s in state['completed_starts']:continue
        seed=args.seed+s;rng=np.random.default_rng(seed)
        x0=x.copy()
        if s:
            x0[:4]+=rng.normal(0,.06,4)
            x0[4:7]+=rng.normal(0,.07,3)
            x0[7:10]+=rng.normal(0,.03,3)
            x0[10:-1]+=rng.normal(0,.06,18)
        model=ExtendModel(args.max_l,bands)
        limits=np.array(model.bounds());x0=np.clip(x0,limits[:,0],limits[:,1])
        try:state['records'].append({'start':s,'seed':seed,'result':optimize(model,x0,args.points,args.atten,args.iterations)})
        except Exception as e:state['failures'].append({'start':s,'seed':seed,'error':repr(e)})
        state['completed_starts'].append(s);state['unfinished']=len(state['completed_starts'])<args.starts
        if args.checkpoint:
            args.checkpoint.parent.mkdir(parents=True,exist_ok=True)
            temp=args.checkpoint.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(args.checkpoint)
        print('completed start',s,'of',args.starts,flush=True)
if __name__=='__main__':main()