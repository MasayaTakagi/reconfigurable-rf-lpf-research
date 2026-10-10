"""Bounded P2-P4 numerical search with coupled chip L and independent validation.

Searches a seeded subset only. Never report this as exhaustive or global.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from coverage_sampler import sample_graphs
from selection_patch import select_node_balanced
from instantiate_graph import build_grounded_settings
from coupling_layout import admissible_matrix,adjacent_patterns
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

def run(args):
    graphs,counts=sample_graphs(max_internal=4,attempts_per_cell=args.attempts,
                               seed=args.seed,max_branches=8)
    graphs=[g for g in graphs if any(t!='GJM01' for _,_,t in g[1])]
    selected,eligible=select_node_balanced(graphs,args.per_bin)
    rows=load_bands();grid=frequency_grid(rows,args.coarse_points)
    rng=np.random.default_rng(args.seed);results=[]
    for (internal_nodes,bin_idx),graph in selected:
        best=None;bounds=bounds_for(graph)
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
        if best is None:continue
        K=np.array(best['coupling']);x=np.array(best['values'])
        try:validation=validate(graph,x,K,rows,args.validation_points)
        except (ValueError,np.linalg.LinAlgError,OverflowError) as exc:
            validation={'error':str(exc)}
        results.append(dict(internal_nodes=internal_nodes,
                            area=sum(AREA[t] for _,_,t in graph[1])/3,
                            bin=f'P{bin_idx+2}',graph=[graph[0],list(map(list,graph[1]))],
                            **best,validation=validation))
    return dict(method='bounded_sampled_search_not_global_optimum',
                parameters=vars(args),sampled_graphs=len(graphs),eligible=eligible,
                optimized_graphs=len(results),results=results)

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
    args=p.parse_args()
    if min(args.attempts,args.per_bin,args.starts,args.layouts,args.iterations,args.coarse_points,args.validation_points)<1:
        p.error('All budget arguments must be positive')
    report=run(args)
    Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'optimized_graphs':report['optimized_graphs'],
                      'results':[(r['internal_nodes'],r['bin'],r['area'],r['coarse_il_db'],r['validation'])
                                 for r in report['results']]},indent=2))
if __name__=='__main__':main()
