"""Reproducible, budgeted graph-to-MNA minimax screening (not exhaustive)."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from instantiate_graph import build_settings,check_graph
from lpf.circuit import solve
from lpf.evaluate import CASES,load_bands
from enumerate_graphs import enumerate_graphs
def frequency_sets(step):
    rows=load_bands()
    return {c:np.unique(np.concatenate([np.linspace(float(r['low_mhz']),float(r['high_mhz']),
        max(2,int(np.ceil((float(r['high_mhz'])-float(r['low_mhz']))/step))+1))
        for r in rows if r['case']==c and r['type']=='pass'])) for c in CASES}
def objective(x,graph,frequencies):
    n,edges=graph
    vals=[x[i]*(1e-12 if t=='GJM01' else 1e-9) for i,(_,_,t) in enumerate(edges)]
    try:
        settings=build_settings(graph,vals,x[len(edges):].reshape(6,2))
        worst=-1e9
        for case in CASES:
            kw=settings[case]
            for f in frequencies[case]:
                worst=max(worst,solve(f*1e6,**kw)['il_db'])
        return float(worst) if np.isfinite(worst) else 1e6
    except (ValueError,np.linalg.LinAlgError,FloatingPointError):
        return 1e6
def select_stratified(graphs,max_candidates):
    bins={'P2':[],'P3':[],'P4':[]}
    for edges in graphs:
        graph=(1+max(max(a,b) for a,b,_ in edges),edges)
        area=check_graph(graph)
        key='P2' if area<=2 else 'P3' if area<=4 else 'P4'
        bins[key].append(graph)
    for key in bins:
        bins[key].sort(key=lambda g:(-len(set(t for _,_,t in g[1])), -g[0],str(g)))
    chosen=[]
    while len(chosen)<max_candidates and any(bins.values()):
        for key in ('P2','P3','P4'):
            if bins[key] and len(chosen)<max_candidates:
                chosen.append(bins[key].pop(0))
    return chosen

def run(max_candidates=6,max_raw=300,seed=20261010):
    counts,graphs=enumerate_graphs(4,4,max_raw=max_raw)
    freq=frequency_sets(15)
    rng=np.random.default_rng(seed)
    output=[]
    for graph in select_stratified(graphs,max_candidates):
        area=check_graph(graph)
        _,edges=graph
        x0=np.array([2.0 if t!='GJM01' else 2.0 for _,_,t in edges]+[.1]*12)
        bounds=[(.4,8) if t!='GJM01' else (.05,100) for _,_,t in edges]+[(0,4)]*12
        candidates=[]
        for x in (x0,np.clip(x0*(1+rng.uniform(-.25,.25,len(x0))),[b[0] for b in bounds],[b[1] for b in bounds])):
            result=minimize(objective,x,args=(graph,freq),method='SLSQP',bounds=bounds,
                options={'maxiter':35,'ftol':1e-7})
            candidates.append(result)
        best=min(candidates,key=lambda r:objective(r.x,graph,freq))
        output.append(dict(area=area,graph=str(graph),il_coarse_db=objective(best.x,graph,freq),
            optimizer_success=bool(best.success),settings_caps_pf=best.x[len(edges):].reshape(6,2).tolist(),
            values=best.x[:len(edges)].tolist()))
    counts['screened']=len(output)
    counts['screened_P2']=sum(r['area']<=2 for r in output)
    counts['screened_P3']=sum(2<r['area']<=4 for r in output)
    counts['screened_P4']=sum(4<r['area']<=6 for r in output)
    return counts,output
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--max-candidates',type=int,default=6)
    p.add_argument('--max-raw',type=int,default=300)
    p.add_argument('--out')
    a=p.parse_args()
    counts,results=run(a.max_candidates,a.max_raw)
    print('GRAPH_ENUMERATION_TRUNCATED=',counts['truncated'])
    print('OPTIMIZED_CANDIDATES=',len(results),'out of',counts['unique'])
    for row in results:print('SCREEN',row['area'],round(row['il_coarse_db'],8),row['optimizer_success'],row['graph'])
    if a.out:Path(a.out).write_text(json.dumps({'counts':dict(counts),'results':results},indent=2))
if __name__=='__main__':main()
