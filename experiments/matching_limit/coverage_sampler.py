"""Seeded non-exhaustive sampling across 0..4 internal nodes and P2/P3/P4."""
from collections import Counter
import random
from topology_selection import area_thirds,has_signal_path,has_unproductive_internal_leaf
TYPES=('LQP01','LQP02','PCB_L','GJM01')
def sample_graphs(max_internal=4,attempts_per_cell=2000,seed=20261011,max_branches=8):
    if not 0<=max_internal<=4 or attempts_per_cell<1 or max_branches<2:
        raise ValueError('Invalid sampling bounds')
    rng=random.Random(seed);out=[];counts=Counter();seen=set()
    for internal in range(max_internal+1):
        n=3+internal
        for target in range(3):
            for _ in range(attempts_per_cell):
                counts[(internal,target,'attempts')]+=1
                mid=list(range(3,n));rng.shuffle(mid)
                nodes=[1]+mid+[2]
                if len(nodes)-1>max_branches:continue
                edges=[(min(a,b),max(a,b),rng.choice(TYPES))
                       for a,b in zip(nodes,nodes[1:])]
                for _ in range(rng.randrange(max_branches-len(edges)+1)):
                    a,b=sorted(rng.sample(range(n),2))
                    edges.append((a,b,rng.choice(TYPES)))
                graph=(n,tuple(sorted(edges)));area=area_thirds(graph)
                actual=0 if area<=6 else 1 if area<=12 else 2
                if area>18 or actual!=target or sum(t=='PCB_L' for _,_,t in edges)>3:continue
                if not has_signal_path(graph) or has_unproductive_internal_leaf(graph):continue
                if graph in seen:continue
                seen.add(graph);out.append(graph)
                counts[(internal,target,'accepted')]+=1
    return out,counts
if __name__=='__main__':
    graphs,counts=sample_graphs()
    for i in range(5):
        print(i,[(p,counts[(i,p,'accepted')]) for p in range(3)])
    print('sampled_unique_labeled',len(graphs))
