"""Convert enumerated two-terminal labeled graphs into shared six-setting MNA circuits.

Graph nodes 0,1 denote input/output; internal graph nodes >=2. Ground is
not part of graph enumeration. Variable shunt C at both terminals is added.
"""
import numpy as np
from lpf.circuit import Branch,solve
from lpf.configuration import validate_six_settings
from lpf.evaluate import CASES

Q={'LQP01':15,'LQP02':25,'PCB_L':12,'GJM01':80}
DEFAULT={'LQP01':2e-9,'LQP02':2e-9,'PCB_L':2e-9,'GJM01':2e-12}
def build_settings(graph,values=None,caps=None,coupling=None):
    n,edges=graph
    if n<2:raise ValueError('Two terminals required')
    if values is None:values=[DEFAULT[t] for _,_,t in edges]
    if len(values)!=len(edges):raise ValueError('Value count mismatch')
    if caps is None:caps=np.zeros((6,2))
    caps=np.asarray(caps,float)
    if caps.shape!=(6,2):raise ValueError('Six settings x two C values required')
    inductors=[];capacitors=[]
    for (a,b,t),value in zip(edges,values):
        branch=Branch(a+1,b+1,float(value),Q[t])
        (capacitors if t=='GJM01' else inductors).append(branch)
    fixed_count=len(capacitors)
    result={}
    for case,cc in zip(CASES,caps):
        result[case]=dict(n_nodes=n,source_node=1,load_node=2,
            inductors=tuple(inductors),
            capacitors=tuple(capacitors+[Branch(1,0,float(cc[0])*1e-12,80),
                Branch(2,0,float(cc[1])*1e-12,80)]),
            coupling=coupling)
    validate_six_settings(result,(fixed_count,fixed_count+1))
    return result
def check_graph(graph):
    n,edges=graph
    if n<2 or not edges:raise ValueError('Empty graph')
    if any(a==b or a<0 or b<0 or a>=n or b>=n for a,b,_ in edges):
        raise ValueError('Invalid edge')
    if any(t not in Q for _,_,t in edges):raise ValueError('Unknown component')
    if sum(t=='PCB_L' for _,_,t in edges)>3:raise ValueError('PCB L limit')
    area=sum({'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2}[t] for _,_,t in edges)
    if area>18:raise ValueError('Chip area >6')
    return area/3
