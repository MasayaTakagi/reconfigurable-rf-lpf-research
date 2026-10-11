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
                         CheckpointCompatibilityError, CheckpointCorruptError,
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

ALGORITHM_VERSION='p4-a-bounded-sharded-v2'


def handle_termination(signum, frame):
    raise KeyboardInterrupt


def _source_fingerprints():
    source_files=(
        Path(__file__), Path(__file__).with_name('p4_sharding.py'),
        ROOT/'experiments/matching_limit/coverage_sampler.py',
        ROOT/'experiments/matching_limit/selection_patch.py',
        ROOT/'experiments/matching_limit/topology_selection.py',
        ROOT/'experiments/matching_limit/enumerate_grounded.py',
        ROOT/'experiments/matching_limit/instantiate_graph.py',
        ROOT/'experiments/matching_limit/coupling_layout.py',
        *sorted((ROOT/'src/lpf').glob('*.py')),
        ROOT/'data/design_constraints.json', ROOT/'data/bands.csv',
        ROOT/'docs/specification.md', ROOT/'requirements.txt',
    )
    missing=[str(path) for path in source_files if not path.is_file()]
    if missing:
        raise FileNotFoundError('Missing calculation source files: '+', '.join(missing))
    return {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_files}


def _source_commit():
    value=os.environ.get('GITHUB_SHA')
    if value:
        return value
    try:
        return subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):
        return 'unknown'


def _execution_metadata():
    try:
        cpu_model=next((line.split(':',1)[1].strip()
                        for line in Path('/proc/cpuinfo').read_text().splitlines()
                        if line.lower().startswith('model name')),None)
    except OSError:
        cpu_model=None
    return {
        'source_commit':_source_commit(),
        'github_run_id':os.environ.get('GITHUB_RUN_ID'),
        'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),
        'github_job_id':os.environ.get('GITHUB_JOB'),
        'runner_name':os.environ.get('RUNNER_NAME'),
        'runner_os':os.environ.get('RUNNER_OS'),
        'runner_arch':os.environ.get('RUNNER_ARCH'),
        'platform':platform.platform(),
        'cpu':{'model':cpu_model,'processor':platform.processor(),
               'machine':platform.machine(),'logical_count':os.cpu_count()},
    }


def build_run_config(args, grid, all_graph_ids):
    """Calculation compatibility only; commit and runner metadata live elsewhere.

    Cross-commit resume is allowed only when this full hash remains identical,
    including calculation-source contents and exact numerical package versions.
    """
    constraints_path=ROOT/'data/design_constraints.json'
    constraints=json.loads(constraints_path.read_text(encoding='utf-8'))
    compatibility={
        'algorithm_version':ALGORITHM_VERSION,
        'analysis_mode':'matching_only',
        'objective':'worst_passband_IL_over_six_settings_UL_DL',
        'full_lpf_harmonic_constraints_applied_during_optimization':False,
        'p4_a_limits':{
            'max_internal_nodes':4,'max_branches':8,'max_chip_area':6,
            'max_pcb_inductors':3,'max_independent_variable_c_branches':2,
        },
        'rf_design_constraints':constraints,
        'topology_search':{
            'attempts_per_cell':args.attempts,'per_node_area_bin':args.per_bin,
            'max_internal_nodes':4,'max_branches':8,'seed':args.seed,
            'selected_graph_ids':all_graph_ids,
        },
        'optimization':{
            'starts':args.starts,'layouts':args.layouts,'iterations':args.iterations,
            'coarse_points_per_band_segment':args.coarse_points,
            'validation_points_per_band_segment':args.validation_points,
            'method':'SLSQP','ftol':1e-6,
        },
        'frequency_grid_mhz':grid,
        'sharding':{
            'shard_count':args.shard_count,
            'assignment':'sha256-canonical-graph-id-mod-v1',
            'per_graph_rng':'sha256-base-seed-and-graph-id-v1',
            'per_candidate_rng':'sha256-graph-seed-layout-start-v1',
        },
        'source_fingerprints':_source_fingerprints(),
        'numeric_environment':{
            'python_implementation':platform.python_implementation(),
            'python_version':platform.python_version(),
            'numpy':importlib.metadata.version('numpy'),
            'scipy':importlib.metadata.version('scipy'),
            'numpy_rng':'PCG64',
            'thread_environment':{
                name:os.environ.get(name,'unset')
                for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')
            },
            'blas_lapack':{
                'numpy':_numeric_backend_signature(np),
                'scipy':_numeric_backend_signature(sys.modules['scipy']),
            },
        },
    }
    return compatibility


def _candidate_seed(graph_seed, layout_index, start_index):
    raw=f'{graph_seed}:{layout_index}:{start_index}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],'big')


def _numeric_backend_signature(module):
    """Capture BLAS/LAPACK identity while omitting host paths and CPU details."""
    config_module=getattr(module,'__config__',None)
    show=getattr(config_module,'show',None)
    try:
        config=show(mode='dicts') if callable(show) else None
    except TypeError:
        config=None
    if isinstance(config,dict):
        dependencies=config.get('Build Dependencies',{})
        signature={}
        for name in ('blas','lapack'):
            backend=dependencies.get(name,{}) if isinstance(dependencies,dict) else {}
            if isinstance(backend,dict):
                signature[name]={key:backend[key] for key in (
                    'name','version','has ilp64')
                    if key in backend}
        if signature:
            return signature
    get_info=getattr(config_module,'get_info',None)
    if callable(get_info):
        signature={}
        for name in ('blas_opt_info','lapack_opt_info','openblas64__info'):
            info=get_info(name)
            if isinstance(info,dict) and info:
                signature[name]={key:info[key] for key in (
                    'libraries','language','define_macros') if key in info}
        if signature:
            return signature
    return {'backend_identity':'not_exposed_by_this_numeric_package_version'}


def run(args, progress_callback=None, candidate_progress_callback=None):
    graphs,counts=sample_graphs(max_internal=4,attempts_per_cell=args.attempts,
                               seed=args.seed,max_branches=8)
    graphs=[g for g in graphs if any(t!='GJM01' for _,_,t in g[1])]
    selected,eligible=select_node_balanced(graphs,args.per_bin)
    rows=load_bands();grid=frequency_grid(rows,args.coarse_points)
    entries=sorted((canonical_graph_id(graph),internal_nodes,bin_idx,graph)
                  for (internal_nodes,bin_idx),graph in selected)
    all_graph_ids=[item[0] for item in entries]
    if len(all_graph_ids)!=len(set(all_graph_ids)):
        raise ValueError('Selected graph set contains duplicate canonical graph IDs')
    shard_entries=[item for item in entries
                   if shard_for_graph(item[0],args.shard_count)==args.shard_index]
    expected_graph_ids=[item[0] for item in shard_entries]
    run_config=build_run_config(args,grid,all_graph_ids)
    config_hash=canonical_config_hash(run_config)
    checkpoint=Path(args.checkpoint or Path(args.output).with_suffix('.checkpoint.json'))
    source_commit=_source_commit()
    execution_segment={
        **_execution_metadata(),
        'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'running','elapsed_seconds':0.0,
        'max_graphs_per_batch':args.max_graphs_per_batch,
        'max_batch_seconds':args.max_batch_seconds,
    }
    if args.resume:
        payload=load_checkpoint(checkpoint,config_hash=config_hash,
                                shard_index=args.shard_index,shard_count=args.shard_count,
                                expected_graph_ids=expected_graph_ids)
        payload['resume_count']=int(payload.get('resume_count',0))+1
        payload.setdefault('execution_history',[]).append(execution_segment)
        payload['source_commits']=sorted(set(payload.get('source_commits',[])+[source_commit]))
        payload['source_commit']=source_commit
        payload.setdefault('resume_history',[]).append({
            'resumed_at_utc':execution_segment['started_at_utc'],
            'artifact_run_id':args.resume_run_id,
            'checkpoint_source':'downloaded_github_artifact' if args.resume_run_id else 'local_file',
            'source_commit':source_commit,
            'compatibility_hash':config_hash,
        })
    else:
        recovery=[]
        if args.resume_artifact_missing:
            recovery.append({
                'requested_run_id':args.resume_run_id,
                'reason':'checkpoint_artifact_missing_or_expired; restarting_this_shard',
                'recorded_at_utc':execution_segment['started_at_utc'],
            })
        payload={
            'schema_version':CHECKPOINT_SCHEMA_VERSION,
            'method':'bounded_seeded_matching_only_search_not_global_optimum',
            'analysis_mode':'matching_only',
            'status':'running','source_commit':source_commit,
            'source_commits':[source_commit],
            'config_hash':config_hash,'run_config':run_config,
            'shard_index':args.shard_index,'shard_count':args.shard_count,
            'global_expected_graph_ids':all_graph_ids,
            'expected_graph_ids':expected_graph_ids,'completed_graph_ids':[],
            'sampled_graphs':len(graphs),'eligible':eligible,'results':[],
            'partial_optimization_runs':{},'candidate_execution_log':[],
            'interrupted_candidate_attempts':[],
            'completed_optimizer_candidates':0,
            'started_at_utc':execution_segment['started_at_utc'],
            'elapsed_seconds':0.0,'resume_count':0,
            'execution_history':[execution_segment],'resume_history':[],
            'resume_recovery':recovery,'unit_execution_log':[],'failures':[],
        }

    if args.resume_artifact_missing and args.resume:
        raise ValueError('--resume-artifact-missing cannot be combined with --resume')
    if args.resume_run_id and not args.resume and not args.resume_artifact_missing:
        raise ValueError('A resume run ID requires a restored checkpoint or explicit missing-artifact state')
    if args.resume_artifact_missing and not args.resume_run_id:
        raise ValueError('--resume-artifact-missing requires --resume-run-id')

    results=list(payload['results'])
    completed=set(payload['completed_graph_ids'])
    elapsed_before=float(payload.get('elapsed_seconds',0.0))
    invocation_started=time.monotonic()
    current_graph_id=None
    current_candidate_attempt=None
    partial_runs=payload.setdefault('partial_optimization_runs',{})
    new_completed=0
    interrupted=False
    failed=False
    batch_stop_reason=None

    def save_checkpoint(status):
        payload['status']=status
        payload['results']=results
        payload['completed_graph_ids']=sorted(completed)
        payload['optimized_graphs']=len(results)
        payload['completed_optimizer_candidates']=sum(
            len(row.get('optimization_runs',[])) for row in results
        )+sum(len(records) for records in partial_runs.values())
        payload['elapsed_seconds']=round(elapsed_before+time.monotonic()-invocation_started,3)
        payload['updated_at_utc']=datetime.now(timezone.utc).isoformat()
        if current_graph_id is None:
            payload.pop('current_graph_id',None)
        else:
            payload['current_graph_id']=current_graph_id
        if current_candidate_attempt is None:
            payload.pop('in_flight_candidate_attempt',None)
        else:
            payload['in_flight_candidate_attempt']=dict(current_candidate_attempt)
        segment=payload['execution_history'][-1]
        segment.update(elapsed_seconds=round(time.monotonic()-invocation_started,3),
                       status=status,updated_at_utc=payload['updated_at_utc'])
        atomic_write_json(checkpoint,payload)

    save_checkpoint('running')
    for graph_id,internal_nodes,bin_idx,graph in shard_entries:
        if graph_id in completed:
            continue
        if args.max_graphs_per_batch and new_completed>=args.max_graphs_per_batch:
            batch_stop_reason='max_graphs_per_batch'
            break
        if (args.max_batch_seconds is not None
                and time.monotonic()-invocation_started>=args.max_batch_seconds):
            batch_stop_reason='max_batch_seconds'
            break
        current_graph_id=graph_id
        unit_started=datetime.now(timezone.utc).isoformat()
        try:
            save_checkpoint('running')
            bounds=bounds_for(graph)
            graph_seed_material=f'{args.seed}:{graph_id}'.encode('ascii')
            graph_seed=int.from_bytes(hashlib.sha256(graph_seed_material).digest()[:8],'big')
            candidate_records=list(partial_runs.get(graph_id,[]))
            saved_candidate_keys={record['candidate_key'] for record in candidate_records}
            candidate_layouts=layout_candidates(graph,args.layouts)
            for layout_index,K in enumerate(candidate_layouts):
                for start_index in range(args.starts):
                    candidate_key=f'{graph_id}:{layout_index}:{start_index}'
                    if candidate_key in saved_candidate_keys:
                        continue
                    rng_seed=_candidate_seed(graph_seed,layout_index,start_index)
                    rng=np.random.default_rng(rng_seed)
                    initial=np.array([rng.uniform(lo,hi) for lo,hi in bounds])
                    if start_index==0:
                        initial[:len(graph[1])]=[2.0 for _ in graph[1]]
                        initial[len(graph[1]):]=1.0
                    evaluation_count=0
                    current_candidate_attempt={
                        'graph_id':graph_id,'candidate_key':candidate_key,
                        'layout_index':layout_index,'start_index':start_index,
                        'rng_seed':rng_seed,'initial_values':initial.tolist(),
                        'objective_evaluation_count':0,
                        'started_at_utc':datetime.now(timezone.utc).isoformat(),
                    }
                    save_checkpoint('running')

                    def counted_objective(values):
                        nonlocal evaluation_count
                        evaluation_count+=1
                        current_candidate_attempt['objective_evaluation_count']=evaluation_count
                        return objective(values,graph,K,grid)

                    optimized=minimize(
                        counted_objective,initial,method='SLSQP',bounds=bounds,
                        options={'maxiter':args.iterations,'ftol':1e-6})
                    final_values=np.asarray(optimized.x,float)
                    score=counted_objective(final_values)
                    candidate_record={
                        'graph_id':graph_id,
                        'candidate_key':candidate_key,
                        'layout_index':layout_index,'start_index':start_index,
                        'rng_seed':rng_seed,'initial_values':initial.tolist(),
                        'result_values':final_values.tolist(),
                        'coupling':np.asarray(K,float).tolist(),
                        'coarse_il_db':float(score),
                        'converged':bool(optimized.success),
                        'optimizer_message':str(optimized.message),
                        'scipy_nfev':int(getattr(optimized,'nfev',evaluation_count)),
                        'objective_evaluation_count':evaluation_count,
                        'completed_at_utc':datetime.now(timezone.utc).isoformat(),
                    }
                    candidate_records.append(candidate_record)
                    candidate_records.sort(key=lambda item:(item['layout_index'],item['start_index']))
                    partial_runs[graph_id]=candidate_records
                    payload.setdefault('candidate_execution_log',[]).append({
                        'graph_id':graph_id,'candidate_key':candidate_key,
                        'execution_segment_index':len(payload['execution_history'])-1,
                        'status':'completed',
                        'objective_evaluation_count':evaluation_count,
                        'completed_at_utc':candidate_record['completed_at_utc'],
                    })
                    current_candidate_attempt=None
                    save_checkpoint('running')
                    if candidate_progress_callback is not None:
                        candidate_progress_callback(payload,candidate_record)
            if not candidate_records:
                raise RuntimeError('No admissible coupling layouts were generated')
            best=min(candidate_records,key=lambda candidate:candidate['coarse_il_db'])
            K=np.asarray(best['coupling'],float)
            x=np.asarray(best['result_values'],float)
            # A validation exception is a job failure, never a normal result row.
            validation=validate(graph,x,K,rows,args.validation_points)
            row={
                'graph_id':graph_id,'optimization_seed':graph_seed,
                'internal_nodes':internal_nodes,
                'area':sum(AREA[t] for _,_,t in graph[1])/3,
                'bin':f'P{bin_idx+2}','graph':[graph[0],list(map(list,graph[1]))],
                'coarse_il_db':best['coarse_il_db'],'converged':best['converged'],
                'values':best['result_values'],'coupling':best['coupling'],
                'best_candidate_key':best['candidate_key'],
                'optimization_runs':candidate_records,'validation':validation,
            }
            results.append(row)
            completed.add(graph_id)
            partial_runs.pop(graph_id,None)
            payload.setdefault('unit_execution_log',[]).append({
                'graph_id':graph_id,'status':'completed',
                'execution_segment_index':len(payload['execution_history'])-1,
                'started_at_utc':unit_started,
                'completed_at_utc':datetime.now(timezone.utc).isoformat(),
                'optimizer_candidate_count':len(candidate_records),
                'objective_evaluation_count':sum(
                    candidate['objective_evaluation_count'] for candidate in candidate_records),
                'candidate_keys':[candidate['candidate_key'] for candidate in candidate_records],
            })
            new_completed+=1
            current_graph_id=None
            save_checkpoint('running')
            if progress_callback is not None:
                progress_callback(payload,row)
        except KeyboardInterrupt:
            interrupted=True
            if current_candidate_attempt is not None:
                payload.setdefault('interrupted_candidate_attempts',[]).append({
                    **current_candidate_attempt,
                    'status':'interrupted_will_replay',
                    'interrupted_at_utc':datetime.now(timezone.utc).isoformat(),
                })
                current_candidate_attempt=None
            save_checkpoint('interrupted')
            break
        except Exception as exc:
            failed=True
            failure={'graph_id':graph_id,'type':type(exc).__name__,'message':str(exc),
                     'failed_at_utc':datetime.now(timezone.utc).isoformat()}
            payload.setdefault('failures',[]).append(failure)
            if current_candidate_attempt is not None:
                payload.setdefault('interrupted_candidate_attempts',[]).append({
                    **current_candidate_attempt,
                    'status':'failed_will_replay',
                    'interrupted_at_utc':failure['failed_at_utc'],
                    'error':failure,
                })
                current_candidate_attempt=None
            payload.setdefault('unit_execution_log',[]).append({
                'graph_id':graph_id,'status':'failed','started_at_utc':unit_started,
                'execution_segment_index':len(payload['execution_history'])-1,
                'failed_at_utc':failure['failed_at_utc'],'error':failure,
            })
            save_checkpoint('failed')
            break

    all_completed=completed==set(expected_graph_ids)
    if interrupted:
        status='interrupted'
    elif failed:
        status='failed'
    elif all_completed:
        status='completed'
    else:
        status='partial'
    payload['batch_limit_reached']=status=='partial' and batch_stop_reason is not None
    payload['batch_stop_reason']=batch_stop_reason
    payload['remaining_graph_ids']=sorted(set(expected_graph_ids)-completed)
    payload['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    current_graph_id=None
    save_checkpoint(status)
    output=Path(args.output)
    if output.resolve()!=checkpoint.resolve():
        atomic_write_json(output,payload)
    return payload


def _parse_args():
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
    p.add_argument('--failure-report',default=None,
                   help='Structured error record for corruption or condition mismatch')
    p.add_argument('--shard-count',type=int,default=1)
    p.add_argument('--shard-index',type=int,default=0)
    p.add_argument('--resume',action='store_true',help='Resume a compatible checkpoint')
    p.add_argument('--resume-run-id',default=None,
                   help='GitHub Actions run ID that supplied the restored artifact')
    p.add_argument('--resume-artifact-missing',action='store_true',
                   help='Explicitly restart this shard when the source artifact was absent/expired')
    p.add_argument('--max-graphs-per-batch',type=int,default=None,
                   help='Stop after this many newly completed graph units for artifact persistence')
    p.add_argument('--max-batch-seconds',type=int,default=None,
                   help='Stop before starting another graph after this many seconds')
    args=p.parse_args()
    if min(args.attempts,args.per_bin,args.starts,args.layouts,args.iterations,args.coarse_points,args.validation_points)<1:
        p.error('All budget arguments must be positive')
    if not 1<=args.shard_count<=64:
        p.error('--shard-count must be between 1 and 64')
    if not 0<=args.shard_index<args.shard_count:
        p.error('--shard-index must be in [0, shard-count)')
    if args.resume and not args.checkpoint:
        p.error('--resume requires --checkpoint')
    if args.max_graphs_per_batch is not None and args.max_graphs_per_batch<1:
        p.error('--max-graphs-per-batch must be positive')
    if args.max_batch_seconds is not None and args.max_batch_seconds<1:
        p.error('--max-batch-seconds must be positive')
    if args.validation_points<2:
        p.error('--validation-points must be at least 2')
    if args.resume and args.resume_artifact_missing:
        p.error('--resume cannot be combined with --resume-artifact-missing')
    if args.resume_artifact_missing and not args.resume_run_id:
        p.error('--resume-artifact-missing requires --resume-run-id')
    return args


def main():
    args=_parse_args()
    checkpoint=Path(args.checkpoint or Path(args.output).with_suffix('.checkpoint.json'))
    failure_report=Path(args.failure_report or checkpoint.with_name('failure.json'))
    failure_report.unlink(missing_ok=True)
    output=Path(args.output)
    if output.resolve()!=checkpoint.resolve():
        output.unlink(missing_ok=True)
    previous_handlers={}
    for signum in (signal.SIGTERM,signal.SIGINT):
        previous_handlers[signum]=signal.signal(signum,handle_termination)
    process_started_wall=datetime.now(timezone.utc)
    process_started=time.monotonic()
    try:
        report=run(args)
    except KeyboardInterrupt:
        report={
            'state':'not_run','shard_index':args.shard_index,
            'message':'Interrupted before the next checkpointed graph unit began.',
            'source_commit':_source_commit(),
        }
        try:
            atomic_write_json(failure_report,report)
        except OSError as exc:
            print(f"::error::Unable to persist interruption report: {exc}",file=sys.stderr)
        print(json.dumps(report),file=sys.stderr)
        return 130
    except Exception as exc:
        if isinstance(exc,CheckpointCompatibilityError):
            state='incompatible'
        elif isinstance(exc,CheckpointCorruptError):
            state='corrupt'
        elif isinstance(exc,FileNotFoundError):
            state='not_run'
        else:
            state='failed'
        report={
            'state':state,'shard_index':args.shard_index,
            'message':f'{type(exc).__name__}: {exc}',
            'source_commit':_source_commit(),
            'resume_run_id':args.resume_run_id,
            'started_at_utc':process_started_wall.isoformat(),
            'finished_at_utc':datetime.now(timezone.utc).isoformat(),
            'elapsed_seconds':round(time.monotonic()-process_started,3),
            'execution_metadata':_execution_metadata(),
        }
        try:
            atomic_write_json(failure_report,report)
        except OSError as write_exc:
            print(f"::error::Unable to persist failure report: {write_exc}",file=sys.stderr)
        print(f"::error::{report['message']}",file=sys.stderr)
        return 1
    finally:
        for signum,handler in previous_handlers.items():
            signal.signal(signum,handler)
    print(json.dumps({'status':report['status'],'shard_index':report['shard_index'],
                      'shard_count':report['shard_count'],
                      'optimized_graphs':report.get('optimized_graphs',len(report['results'])),
                      'completed_optimizer_candidates':report['completed_optimizer_candidates'],
                      'remaining_graphs':len(report['remaining_graph_ids']),
                      'results':[(r['internal_nodes'],r['bin'],r['area'],r['coarse_il_db'],r['validation'])
                                 for r in report['results']]},indent=2))
    if report['status']=='interrupted':
        return 130
    if report['status']=='failed':
        return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
