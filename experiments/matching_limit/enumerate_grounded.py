"""Ground-aware finite RF graph enumeration.

Node 0=ground, 1=input, 2=output, 3..=internal nodes.
Source/load are attached externally. Only internal node labels may permute.
This is structural coverage only; no physical coupling or optimizer.
"""
import argparse,itertools
from collections import Counter
TYPES=('LQP01','LQP02','PCB_L','GJM01')
COST={'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2}
def canonical(n,edges):
    best=None
    for perm in itertools.permutations(range(3,n)):
        mapping={0:0,1:1,2:2,**dict(zip(range(3,n),perm))}
        mapped=tuple(sorted((min(mapping[a],mapping[b]),max(mapping[a],mapping[b]),t) for a,b,t in edges))
        if best is None or mapped<best:best=mapped
    return best
def active_connected(n,edges):
    """Require every internal node to be reachable from input/output or ground.

    Ground may be disconnected for pure two-terminal series circuits.
    Source and load must be in the same connected component through branches.
    """
    adj=[set() for _ in range(n)]
    for a,b,_ in edges:adj[a].add(b);adj[b].add(a)
    reached={1};pending=[1]
    while pending:
        a=pending.pop()
        for b in adj[a]-reached:reached.add(b);pending.append(b)
    if 2 not in reached:return False
    return all(k in reached for k in range(3,n))
def enumerate_grounded(max_internal=1,max_branches=4,max_raw=100000):
    if not 0<=max_internal<=6 or not 1<=max_branches<=8 or max_raw<1:
        raise ValueError('Invalid enumeration bounds')
    counts=Counter();seen=set();examples=[];truncated=False
    for internal in range(max_internal+1):
        n=internal+3
        options=[(a,b,t) for a,b in itertools.combinations(range(n),2) for t in TYPES]
        for k in range(1,max_branches+1):
            for edges in itertools.combinations_with_replacement(options,k):
                if counts['raw']>=max_raw:truncated=True;break
                counts['raw']+=1
                if sum(COST[t] for _,_,t in edges)>18:continue
                if sum(t=='PCB_L' for _,_,t in edges)>3:continue
                if not active_connected(n,edges):continue
                key=canonical(n,edges)
                if (n,key) in seen:continue
                seen.add((n,key))
                area=sum(COST[t] for _,_,t in edges)
                counts['P2' if area<=6 else 'P3' if area<=12 else 'P4']+=1
                examples.append((n,key))
            if truncated:break
        if truncated:break
    counts['unique']=len(seen);counts['truncated']=truncated
    return counts,examples
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--internal',type=int,default=1)
    p.add_argument('--branches',type=int,default=4)
    p.add_argument('--max-raw',type=int,default=100000)
    a=p.parse_args()
    counts,_=enumerate_grounded(a.internal,a.branches,a.max_raw)
    print(dict(counts))
    print('coverage='+('TRUNCATED_INCOMPLETE' if counts['truncated'] else 'COMPLETE_WITHIN_DECLARED_GROUNDED_GRAPH_CLASS'))
if __name__=='__main__':main()
