"""Convert enumerated two-terminal labeled graphs into shared six-setting MNA circuits.

Graph nodes 0,1 denote input/output; internal graph nodes >=2. Ground is
not part of graph enumeration. Variable shunt C at both terminals is added.
"""
import numpy as np
from lpf.circuit import Branch,solve
from lpf.configuration import validate_six_settings
from lpf.evaluate import CASES

Q={'LQP01':15,'LQP02':25,'PCB_L':12,'GJM01':80,'PCB_PATTERN_C':40}
DEFAULT={'LQP01':2e-9,'LQP02':2e-9,'PCB_L':2e-9,'GJM01':2e-12,'PCB_PATTERN_C':.1e-12}
def build_settings(graph,values=None,caps=None,coupling=None):
    check_graph(graph)
    n,edges=graph
    if n<2:raise ValueError('Two terminals required')
    if values is None:values=[DEFAULT[t] for _,_,t in edges]
    if len(values)!=len(edges):raise ValueError('Value count mismatch')
    if caps is None:caps=np.zeros((6,2))
    caps=np.asarray(caps,float)
    if caps.shape!=(6,2):raise ValueError('Six settings x two C values required')
    from lpf.constraints import validate_pcb_pattern_caps
    validate_pcb_pattern_caps([float(v)*1e12 for (_,_,t),v in zip(edges,values) if t=='PCB_PATTERN_C'])
    inductors=[];capacitors=[]
    for (a,b,t),value in zip(edges,values):
        branch=Branch(a+1,b+1,float(value),Q[t])
        (capacitors if t in ('GJM01','PCB_PATTERN_C') else inductors).append(branch)
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
    if sum(t=='PCB_PATTERN_C' for _,_,t in edges)>3:raise ValueError('PCB pattern C limit')
    area=sum({'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2,'PCB_PATTERN_C':0}[t] for _,_,t in edges)
    if area>18:raise ValueError('Chip area >6')
    return area/3

def build_grounded_settings(graph,values=None,caps=None,coupling=None):
    """Graph 0=ground,1=input,2=output,>=3 internal."""
    check_graph(graph)
    n,edges=graph
    if n<3:raise ValueError('Ground and two terminals required')
    if values is None:values=[DEFAULT[t] for _,_,t in edges]
    if len(values)!=len(edges):raise ValueError('Value count mismatch')
    if caps is None:caps=np.zeros((6,2))
    caps=np.asarray(caps,float)
    if caps.shape!=(6,2) or np.any(caps<0) or np.any(caps>4):
        raise ValueError('Invalid variable capacitor settings')
    from lpf.constraints import validate_pcb_pattern_caps
    validate_pcb_pattern_caps([float(v)*1e12 for (_,_,t),v in zip(edges,values) if t=='PCB_PATTERN_C'])
    inductors=[];fixed=[]
    for (a,b,t),v in zip(edges,values):
        branch=Branch(a,b,float(v),Q[t])
        (fixed if t in ('GJM01','PCB_PATTERN_C') else inductors).append(branch)
    if sum(t=='PCB_L' for _,_,t in edges)>3:raise ValueError('PCB limit')
    if sum({'LQP01':2,'LQP02':3,'PCB_L':0,'GJM01':2,'PCB_PATTERN_C':0}[t] for _,_,t in edges)>18:
        raise ValueError('Chip area limit')
    out={}
    for case,cc in zip(CASES,caps):
        out[case]=dict(n_nodes=n-1,source_node=1,load_node=2,
            inductors=tuple(inductors),
            capacitors=tuple(fixed+[Branch(1,0,float(cc[0])*1e-12,80),
                                     Branch(2,0,float(cc[1])*1e-12,80)]),
            coupling=coupling)
    validate_six_settings(out,(len(fixed),len(fixed)+1))
    return out
