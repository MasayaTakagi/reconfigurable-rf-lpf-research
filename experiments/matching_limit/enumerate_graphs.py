"""Budgeted topology enumeration; a truncated run is never exhaustive.

Two fixed terminals (0,1); internal node labels are canonicalized.
No physical chip order, coupling assignments, or IC variable C placement yet.
"""
import argparse
import csv
import itertools
from collections import Counter

TYPES=('LQP01','LQP02','PCB_L','GJM01')
COST={'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2}  # thirds
def canonical(n,edges):
    candidates=[]
    for perm in itertools.permutations(range(2,n)):
        m={0:0,1:1,**dict(zip(range(2,n),perm))}
        candidates.append(tuple(sorted((min(m[a],m[b]),max(m[a],m[b]),t) for a,b,t in edges)))
    return min(candidates)
def connected(n,edges):
    reached={0}
    while True:
        nxt=reached|{b for a,b,_ in edges if a in reached}|{a for a,b,_ in edges if b in reached}
        if nxt==reached:return len(reached)==n
        reached=nxt
def enumerate_graphs(max_nodes=3,max_branches=6,max_raw=None):
    if not 2<=max_nodes<=8 or not 1<=max_branches<=8:
        raise ValueError('Use 2-8 total nodes and 1-8 branches')
    if max_raw is not None and max_raw<1:raise ValueError('max_raw must be positive')
    counts=Counter();examples={};truncated=False
    for n in range(2,max_nodes+1):
        options=[(a,b,t) for a,b in itertools.combinations(range(n),2) for t in TYPES]
        for k in range(max(n-1,1),max_branches+1):
            for edges in itertools.combinations_with_replacement(options,k):
                if max_raw is not None and counts['raw']>=max_raw:
                    truncated=True
                    break
                counts['raw']+=1
                if sum(COST[t] for _,_,t in edges)>18:continue
                if sum(t=='PCB_L' for _,_,t in edges)>3:continue
                if not connected(n,edges):continue
                counts['feasible_labeled']+=1
                key=canonical(n,edges)
                if key in examples:continue
                examples[key]=True
                area=sum(COST[t] for _,_,t in edges)
                counts['P2' if area<=6 else 'P3' if area<=12 else 'P4']+=1
            if truncated:break
        if truncated:break
    counts['unique']=len(examples)
    counts['truncated']=truncated
    return counts,examples
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--nodes',type=int,default=3,help='total nodes, including two terminals')
    p.add_argument('--branches',type=int,default=6)
    p.add_argument('--max-raw',type=int,default=None,help='hard stop; output is incomplete if reached')
    p.add_argument('--out')
    args=p.parse_args()
    counts,examples=enumerate_graphs(args.nodes,args.branches,args.max_raw)
    print('scope=nodes<=%d branches<=%d max_raw=%s; no layout/coupling enumeration'%
          (args.nodes,args.branches,args.max_raw))
    print(dict(counts))
    print('coverage='+('TRUNCATED_INCOMPLETE' if counts['truncated'] else 'COMPLETE_WITHIN_DECLARED_GRAPH_CLASS'))
    if args.out:
        with open(args.out,'w',newline='') as f:
            w=csv.writer(f);w.writerow(('node_count','area_units','phase','edges'))
            for n,edges in sorted(examples,key=str):
                area=sum(COST[t] for _,_,t in edges)/3
                w.writerow((n,area,'P2' if area<=2 else 'P3' if area<=4 else 'P4',repr(edges)))
if __name__=='__main__':main()
