"""Bounded P2-P4 numerical search with coupled chip L and independent validation.

Searches a seeded subset only. Never report this as exhaustive or global.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from coverage_sampler import sample_graphs
from selection_patch import select_node_balanced
from instantiate_graph import build_grounded_settings
from coupling_layout import admissible_matrix,adjacent_patterns
from p4_sharding import (CHECKPOINT_SCHEMA_VERSION, atomic_write_json,
                         canonical_config_hash, canonical_graph_id,
                         load_checkpoint, shard_for_graph)
from lpf.evaluate import CASES,load_bands,evaluate_settings
from lpf.circuit import solve
from lpf.independent import solve_gain

AREA={'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2}

def frequency_grid(rows,points):
    return {c:sorted(set(float(f) for r in rows if r['case']==c and r['region'] in ('UL','DL')
                 for f in np.linspace(float(r['low_mhz']),float(r['high_mhz']),points))) for c in CASES}

def layout_candidates(graph,max_layouts):
    """Deterministic nominal + spread chip and PCB coupling patterns.

    Chip-to-PCB remains nominal zero in this stage. Every candidate must be SPD.
    """
    import itertools
    types=[t for _,_,t in graph[1] if t!='GJM01']
    chips=[i for i,t in enumerate(types) if t in ('LQP01','LQP02')]
    pcbs=[i for i,t in enumerate(types) if t=='PCB_L']
    chip_pairs=list(zip(chips,chips[1:]))
    pcb_pairs=list(itertools.combinations(pcbs,2))
    candidates=[({}, {})]
    for a,b in chip_pairs:
        for k in (-.4,.4):candidates.append(({frozenset((a,b)):k},{}))
    for a,b in pcb_pairs:
        for k in (-.6,.6):candidates.append(({}, {frozenset((a,b)):k}))
    if chip_pairs:candidates.append(({frozenset(pair):.4 for pair in chip_pairs},{}))
    if pcb_pairs:candidates.append(({}, {frozenset(pair):.6 for pair in pcb_pairs}))
    unique=[];seen=set()
    for ce,pe in candidates:
        signature=(tuple(sorted((tuple(sorted(pair)),k) for pair,k in ce.items())),
                   tuple(sorted((tuple(sorted(pair)),k) for pair,k in pe.items())))
        if signature in seen:continue
        seen.add(signature)
        try:K=admissible_matrix(types,[1.]*len(types),chip_edges=ce,pcb_pairs=pe)
        except ValueError:continue
        unique.append(K)
        if len(unique)>=max_layouts:break
    return unique

def bounds_for(graph):
    b=[]
    for _,_,t in graph[1]:
        b.append((.05,100.) if t=='GJM01' else (.3,5.) if t=='PCB_L' else (.3,12.))
    return b+[(0.,4.)]*12

def settings_for(graph,x,K):
    values=[float(v)*(1e-12 if t=='GJM01' else 1e-9) for v,(_,_,t) in zip(x,graph[1])]
    return build_grounded_settings(graph,values,np.asarray(x[len(values):]).reshape(6,2),coupling=K)

def objective(x,graph,K,grid):
    try:
        settings=settings_for(graph,x,K)
        worst=-np.inf
        for c in CASES:
            for f in grid[c]:
                val=solve(f*1e6,**settings[c])['il_db']
                if not np.isfinite(val):return 1e5
                worst=max(worst,val)
        return float(worst)
    except (ValueError,np.linalg.LinAlgError,OverflowError,FloatingPointError):
        return 1e5

def validate(graph,x,K,rows,points):
    settings=settings_for(graph,x,K)
    report=evaluate_settings(lambda c:settings[c],samples_per_segment=points,bands=rows)
    mismatch=0.;residual=0.
    for c in CASES:
        for r in rows:
            if r['case']!=c or r['region'] not in ('UL','DL'):continue
            for f in np.linspace(float(r['low_mhz']),float(r['high_mhz']),points):
                params=settings[c];mna=solve(float(f)*1e6,**params)
                nodal=solve_gain(float(f)*1e6,**params)
                mismatch=max(mismatch,abs(mna['gain']-nodal))
                residual=max(residual,abs(mna['power_residual']))
    return dict(worst_il_db=report['worst_il_db'][0],
                worst_il_case=report['worst_il_db'][1],
                worst_il_region=report['worst_il_db'][2],
                min_h2_db=report['min_h2_db'][0],
                min_h3_db=report['min_h3_db'][0],
                max_gain_mismatch=mismatch,max_power_residual=residual,
                samples_per_segment=points)

def handle_termination(signum,frame):
    raise KeyboardInterrupt

def run(args):
    graphs,counts=sample_graphs(max_internal=4,attempts_per_cell=args.attempts,
                               seed=args.seed,max_branches=8)
    graphs=[g for g in graphs if any(t!='GJM01' for _,_,t in g[1])]
    selected,eligible=select_node_balanced(graphs,args.per_bin)
    rows=load_bands();grid=frequency_grid(rows,args.coarse_points)
    entries=[]
    for (internal_nodes,bin_idx),graph in selected:
        entries.append((canonical_graph_id(graph),internal_nodes,bin_idx,graph))
    entries.sort(key=lambda item:item[0])
    all_graph_ids=[item[0] for item in entries]
    if len(all_graph_ids)!=len(set(all_graph_ids)):
        raise ValueError('Selected graph set contains duplicate canonical graph IDs')
    shard_entries=[item for item in entries
                   if shard_for_graph(item[0],args.shard_count)==args.shard_index]
    expected_graph_ids=[item[0] for item in shard_entries]

    source_files=(
        Path(__file__), Path(__file__).with_name('p4_sharding.py'),
        ROOT/'experiments/matching_limit/coverage_sampler.py',
        ROOT/'experiments/matching_limit/selection_patch.py',
        ROOT/'experiments/matching_limit/enumerate_grounded.py',
        ROOT/'experiments/matching_limit/instantiate_graph.py',
        ROOT/'experiments/matching_limit/coupling_layout.py',
        *sorted((ROOT/'src/lpf').glob('*.py')),
        ROOT/'data/design_constraints.json', ROOT/'data/bands.csv',
        ROOT/'docs/specification.md', ROOT/'requirements.txt',
    )
    source_fingerprints={str(path.relative_to(ROOT)):
                         hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in source_files}
    def package_version(name):
        try:return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:return 'missing'
    source_commit=os.environ.get('GITHUB_SHA')
    if not source_commit:
        try:source_commit=subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
        except (OSError,subprocess.CalledProcessError):source_commit='unknown'
    parameters={name:getattr(args,name) for name in (
        'attempts','per_bin','starts','layouts','iterations','coarse_points',
        'validation_points','seed')}
    run_config=dict(
        algorithm='p4-a-bounded-sharded-v1',
        p4_a_limits=dict(max_internal_nodes=4,max_branches=8,max_chip_area=6,
                         max_pcb_inductors=3),
        parameters=parameters,
        shard_count=args.shard_count,
        shard_assignment='sha256-canonical-graph-id-mod-v1',
        per_graph_seed='sha256-base-seed-and-graph-id-v1',
        selected_graph_ids=all_graph_ids,
        source_commit=source_commit,
        source_fingerprints=source_fingerprints,
        runtime=dict(python=sys.version.split()[0],platform=platform.platform(),
                     numpy=package_version('numpy'),scipy=package_version('scipy')))
    config_hash=canonical_config_hash(run_config)
    checkpoint=Path(args.checkpoint or (Path(args.output).with_suffix('.checkpoint.json')))
    if args.resume:
        payload=load_checkpoint(checkpoint,config_hash=config_hash,
                                shard_index=args.shard_index,shard_count=args.shard_count,
                                expected_graph_ids=expected_graph_ids)
    else:
        payload=dict(schema_version=CHECKPOINT_SCHEMA_VERSION,
                     method='bounded_sampled_search_not_global_optimum',
                     status='running',source_commit=source_commit,
                     config_hash=config_hash,run_config=run_config,
                     shard_index=args.shard_index,shard_count=args.shard_count,
                     expected_graph_ids=expected_graph_ids,completed_graph_ids=[],
                     sampled_graphs=len(graphs),eligible=eligible,results=[],
                     started_at_utc=datetime.now(timezone.utc).isoformat(),
                     elapsed_seconds=0.0,resume_count=0,
                     run_segments=[dict(started_at_utc=datetime.now(timezone.utc).isoformat(),
                                        elapsed_seconds=0.0,status='running')])
        atomic_write_json(checkpoint,payload)

    if args.resume:
        payload['resume_count']=int(payload.get('resume_count',0))+1
        payload.setdefault('run_segments',[]).append(
            dict(started_at_utc=datetime.now(timezone.utc).isoformat(),
                 elapsed_seconds=0.0,status='running'))
    results=list(payload['results'])
    completed=set(payload['completed_graph_ids'])
    elapsed_before=float(payload.get('elapsed_seconds',0.0))
    invocation_started=time.monotonic()
    current_graph_id=None
    interrupted=False

    def save_checkpoint(status):
        payload['status']=status
        payload['results']=results
        payload['completed_graph_ids']=sorted(completed)
        payload['optimized_graphs']=len(results)
        payload['elapsed_seconds']=round(elapsed_before+time.monotonic()-invocation_started,3)
        payload['updated_at_utc']=datetime.now(timezone.utc).isoformat()
        if payload.get('run_segments'):
            payload['run_segments'][-1].update(
                elapsed_seconds=round(time.monotonic()-invocation_started,3),
                status=status,updated_at_utc=payload['updated_at_utc'])
        if current_graph_id is not None:
            payload['current_graph_id']=current_graph_id
        else:
            payload.pop('current_graph_id',None)
        atomic_write_json(checkpoint,payload)

    for graph_id,internal_nodes,bin_idx,graph in shard_entries:
        if graph_id in completed:
            continue
        current_graph_id=graph_id
        save_checkpoint('running')
        try:
            best=None;bounds=bounds_for(graph)
            seed_material=f'{args.seed}:{graph_id}'.encode('ascii')
            optimization_seed=int.from_bytes(hashlib.sha256(seed_material).digest()[:8],'big')
            rng=np.random.default_rng(optimization_seed)
            for K in layout_candidates(graph,args.layouts):
                for start in range(args.starts):
                    x=np.array([rng.uniform(lo,hi) for lo,hi in bounds])
                    if start==0:
                        x[:len(graph[1])]=[2.0 for _ in graph[1]]
                        x[len(graph[1]):]=1.0
                    result=minimize(objective,x,args=(graph,K,grid),method='SLSQP',bounds=bounds,
                                    options={'maxiter':args.iterations,'ftol':1e-6})
                    score=objective(result.x,graph,K,grid)
                    if best is None or score<best['coarse_il_db']:
                        best=dict(coarse_il_db=score,converged=bool(result.success),
                                  values=result.x.tolist(),coupling=K.tolist())
            if best is None:
                continue
            K=np.array(best['coupling']);x=np.array(best['values'])
            try:validation=validate(graph,x,K,rows,args.validation_points)
            except (ValueError,np.linalg.LinAlgError,OverflowError) as exc:
                validation={'error':str(exc)}
            results.append(dict(graph_id=graph_id,optimization_seed=optimization_seed,
                                internal_nodes=internal_nodes,
                                area=sum(AREA[t] for _,_,t in graph[1])/3,
                                bin=f'P{bin_idx+2}',graph=[graph[0],list(map(list,graph[1]))],
                                **best,validation=validation))
            completed.add(graph_id)
            save_checkpoint('running')
        except KeyboardInterrupt:
            interrupted=True
            save_checkpoint('interrupted')
            break
    status=('interrupted' if interrupted else
            'completed' if completed==set(expected_graph_ids) else 'partial')
    save_checkpoint(status)
    payload['finished_at_utc']=datetime.now(timezone.utc).isoformat() if status=='completed' else None
    atomic_write_json(checkpoint,payload)
    output=Path(args.output)
    if output.resolve()!=checkpoint.resolve():
        atomic_write_json(output,payload)
    return payload

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--attempts',type=int,default=200)
    p.add_argument('--per-bin',type=int,default=2,help='Candidates per node-count and area bin')
    p.add_argument('--starts',type=int,default=2)
    p.add_argument('--layouts',type=int,default=3)
    p.add_argument('--iterations',type=int,default=25)
    p.add_argument('--coarse-points',type=int,default=2)
    p.add_argument('--validation-points',type=int,default=21)
    p.add_argument('--seed',type=int,default=20261011)
    p.add_argument('--output',default='p4_batch_result.json')
    p.add_argument('--checkpoint',default=None,help='Atomic per-shard checkpoint JSON path')
    p.add_argument('--shard-count',type=int,default=1)
    p.add_argument('--shard-index',type=int,default=0)
    p.add_argument('--resume',action='store_true',help='Resume a compatible checkpoint')
    args=p.parse_args()
    if min(args.attempts,args.per_bin,args.starts,args.layouts,args.iterations,args.coarse_points,args.validation_points)<1:
        p.error('All budget arguments must be positive')
    if not 1<=args.shard_count<=64:
        p.error('--shard-count must be between 1 and 64')
    if not 0<=args.shard_index<args.shard_count:
        p.error('--shard-index must be in [0, shard-count)')
    if args.resume and not args.checkpoint:
        p.error('--resume requires --checkpoint')
    previous_sigterm=signal.signal(signal.SIGTERM,handle_termination)
    try:
        report=run(args)
    finally:
        signal.signal(signal.SIGTERM,previous_sigterm)
    print(json.dumps({'status':report['status'],'shard_index':report['shard_index'],
                      'shard_count':report['shard_count'],
                      'optimized_graphs':report.get('optimized_graphs',len(report['results'])),
                      'results':[(r['internal_nodes'],r['bin'],r['area'],r['coarse_il_db'],r['validation'])
                                 for r in report['results']]},indent=2))
    return 0 if report['status']=='completed' else 130
if __name__=='__main__':raise SystemExit(main())
