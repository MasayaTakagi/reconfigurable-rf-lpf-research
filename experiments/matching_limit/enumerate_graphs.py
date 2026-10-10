"""Finite labeled RF network graph enumeration, NOT all physically possible networks.

Terminals 0,1 are fixed. At most 3 nodes and 4 branches by default.
Parallel edges allowed. Coupling/layout configurations are NOT enumerated.
"""
import argparse
import csv
import itertools
from collections import Counter
from pathlib import Path

TYPES=('LQP01','LQP02','PCB_L','GJM01')
COST={'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2}  # thirds of area unit
def canonical(n,edges):
    """Only internal nodes can be permuted; terminals remain fixed."""
    candidates=[]
    for perm in itertools.permutations(range(2,n)):
        mapping={0:0,1:1,**dict(zip(range(2,n),perm))}
        candidates.append(tuple(sorted((min(mapping[a],mapping[b]),max(mapping[a],mapping[b]),t) for a,b,t in edges)))
    return min(candidates)
def connected(n,edges):
    reachable={0}
    while True:
        new=reachable|{b for a,b,_ in edges if a in reachable}|{a for a,b,_ in edges if b in reachable}
        if new==reachable:break
        reachable=new
    return len(reachable)==n
def enumerate_graphs(max_nodes=3,max_branches=6):
    if not 2<=max_nodes<=4 or not 1<=max_branches<=6:
        raise ValueError('Use 2-4 nodes and 1-6 branches')
    counts=Counter();examples={}
    for n in range(2,max_nodes+1):
        options=[(a,b,t) for a,b in itertools.combinations(range(n),2) for t in TYPES]
        for k in range(1,max_branches+1):
            for edges in itertools.combinations_with_replacement(options,k):
                counts['raw']+=1
                if sum(COST[t] for _,_,t in edges)>18:continue
                if sum(t=='PCB_L' for _,_,t in edges)>3:continue
                if not connected(n,edges):continue
                counts['feasible_labeled']+=1
                key=canonical(n,edges)
                if key in examples:continue
                examples[key]=True
                area=sum(COST[t] for _,_,t in edges)
                phase='P2' if area<=6 else 'P3' if area<=12 else 'P4'
                counts[phase]+=1
    counts['unique']=len(examples)
    return counts,examples
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--nodes',type=int,default=3)
    p.add_argument('--branches',type=int,default=6)
    p.add_argument('--out')
    args=p.parse_args()
    counts,examples=enumerate_graphs(args.nodes,args.branches)
    print('scope=nodes<=%d branches<=%d; no layout/coupling enumeration'%(args.nodes,args.branches))
    print(dict(counts))
    if args.out:
        with open(args.out,'w',newline='') as f:
            w=csv.writer(f);w.writerow(('node_count','area_units','phase','edges'))
            for (n,edges) in sorted(examples,key=str):
                area=sum(COST[t] for _,_,t in edges)/3
                w.writerow((n,area,'P2' if area<=2 else 'P3' if area<=4 else 'P4',repr(edges)))
if __name__=='__main__':main()
