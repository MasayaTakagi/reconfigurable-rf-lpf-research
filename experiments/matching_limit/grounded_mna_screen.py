"""Small, reproducible grounded graph P2/P3/P4 MNA screen.

Only a cost-stratified *pilot*, not complete P2-P4. No coupling yet.
"""
import argparse,sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from coverage_sampler import sample_graphs
from topology_selection import select_balanced
from instantiate_graph import build_grounded_settings
from lpf.evaluate import CASES,load_bands
from lpf.circuit import solve
def frequencies():
    rows=load_bands()
    return {c:sorted({f for r in rows if r['case']==c and r['type']=='pass'
        for f in np.linspace(float(r['low_mhz']),float(r['high_mhz']),3)}) for c in CASES}
def score(x,graph,freq):
    edges=graph[1]
    values=[float(v)*(1e-12 if t=='GJM01' else 1e-9) for v,(_,_,t) in zip(x,edges)]
    try:
        settings=build_grounded_settings(graph,values,np.asarray(x[len(edges):]).reshape(6,2))
        return max(solve(f*1e6,**settings[c])['il_db'] for c in CASES for f in freq[c])
    except (ValueError,np.linalg.LinAlgError,OverflowError):return 1e6
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--max-raw',type=int,default=200,help='Legacy flag: random attempts per internal-node/area cell')
    p.add_argument('--per-bin',type=int,default=1)
    a=p.parse_args()
    graphs,counts=sample_graphs(max_internal=4,attempts_per_cell=a.max_raw,seed=20261011)
    print('sampled_graphs_nonexhaustive',len(graphs),'coverage_by_node_and_area',dict(counts))
    freq=frequencies()
    # Prefer graphs with at least one inductor and one fixed C where possible.
    filtered=[g for g in graphs if any(t=='GJM01' for _,_,t in g[1])
              and any(t!='GJM01' for _,_,t in g[1])]
    selected,eligible_counts=select_balanced(filtered,a.per_bin)
    print('eligible_after_structural_pruning',eligible_counts)
    print('selected_bins', {name:sum(i==idx for i,_ in selected) for idx,name in enumerate(('P2','P3','P4'))})
    for idx,g in selected:
        edges=g[1];n=len(edges)
        x=np.array([2.]*n+[.1]*12)
        bounds=[(.4,3) if t=='PCB_L' else (.4,8) if t!='GJM01' else (.05,100)
                for _,_,t in edges]+[(0,4)]*12
        result=minimize(score,x,args=(g,freq),method='SLSQP',bounds=bounds,
            options={'maxiter':15,'ftol':1e-6})
        print('P%d'% (idx+2),'area',sum({'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2}[t] for _,_,t in edges)/3,
            'coarse_il',score(result.x,g,freq),'success',result.success,'graph',g)
if __name__=='__main__':main()
