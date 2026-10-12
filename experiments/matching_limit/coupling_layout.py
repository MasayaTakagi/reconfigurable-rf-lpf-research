"""Physical chip row and coupled-inductor admissibility.

Nominal non-strong chip pairs are zero. Signs are electrical dot choices
requiring subsequent physical polarity verification.
"""
import itertools
import numpy as np
def admissible_matrix(types,values,chip_order=None,chip_edges=None,pcb_pairs=None,chip_pcb=None):
    n=len(types)
    if len(values)!=n:raise ValueError('Length mismatch')
    chips=[i for i,t in enumerate(types)
           if t in ('LQP01','LQP02','LQP02HV','LQP02HQ','LQW04')]
    pcbs=[i for i,t in enumerate(types) if t=='PCB_L']
    if len(pcbs)>3:raise ValueError('PCB count exceeds three')
    if chip_order is None:chip_order=chips
    if sorted(chip_order)!=sorted(chips):raise ValueError('Chip order must be a permutation')
    chip_edges=chip_edges or {}
    pcb_pairs=pcb_pairs or {}
    chip_pcb=chip_pcb or {}
    neighbors={frozenset((a,b)) for a,b in zip(chip_order,chip_order[1:])}
    K=np.eye(n)
    def add(pairs,allowed,limit):
        for pair,k in pairs.items():
            a,b=tuple(pair)
            if a==b or frozenset((a,b)) not in allowed or not np.isfinite(k) or abs(k)>limit+1e-12:
                raise ValueError('Invalid coupling')
            K[a,b]=K[b,a]=float(k)
    add(chip_edges,neighbors,.4)
    add(pcb_pairs,{frozenset(p) for p in itertools.combinations(pcbs,2)},.6)
    add(chip_pcb,{frozenset((a,b)) for a in chips for b in pcbs},.03)
    L=np.asarray(values,float)
    if np.any(L<=0):raise ValueError('Positive L required')
    validate_coupling_matrix(types,L,K,chip_order=chip_order)
    return K

def validate_coupling_matrix(types,values,coupling,chip_order=None,
                             chip_strong_max=.4,chip_weak_max=.1,
                             chip_pcb_max=.03,pcb_pcb_max=.6):
    """Independently enforce the one-row physical-neighbor coupling policy."""
    n=len(types);L=np.asarray(values,float);K=np.asarray(coupling,float)
    if (L.shape!=(n,) or np.any(~np.isfinite(L)) or np.any(L<=0)
            or K.shape!=(n,n) or np.any(~np.isfinite(K))
            or not np.allclose(K,K.T,atol=1e-12,rtol=0)
            or not np.allclose(np.diag(K),1,atol=1e-12,rtol=0)):
        raise ValueError('Invalid coupling or inductor values')
    chips=[i for i,t in enumerate(types)
           if t in ('LQP01','LQP02','LQP02HV','LQP02HQ','LQW04')]
    pcbs=[i for i,t in enumerate(types) if t=='PCB_L']
    if len(pcbs)>3:raise ValueError('PCB count exceeds three')
    order=chips if chip_order is None else list(chip_order)
    if sorted(order)!=sorted(chips):raise ValueError('Chip order must be a permutation')
    neighbors={frozenset((a,b)) for a,b in zip(order,order[1:])}
    for i in range(n):
        for j in range(i+1,n):
            pair=frozenset((i,j));k=abs(K[i,j])
            if i in chips and j in chips:
                limit=chip_strong_max if pair in neighbors else chip_weak_max
            elif (i in chips and j in pcbs) or (j in chips and i in pcbs):
                limit=chip_pcb_max
            elif i in pcbs and j in pcbs:
                limit=pcb_pcb_max
            else:
                limit=0.0
            if k>limit+1e-12:
                raise ValueError('Strong chip coupling requires physical neighbors; pair exceeds its allowed limit')
    M=K*np.sqrt(np.outer(L,L))
    if np.linalg.eigvalsh(M).min()<=0:
        raise ValueError('Inductance matrix not SPD')
    return True
def adjacent_patterns(types,chip_order=None):
    chips=[i for i,t in enumerate(types)
           if t in ('LQP01','LQP02','LQP02HV','LQP02HQ','LQW04')]
    order=chips if chip_order is None else chip_order
    if sorted(order)!=sorted(chips):raise ValueError('Invalid order')
    pairs=list(zip(order,order[1:]))
    for states in itertools.product((0,-.4,.4),repeat=len(pairs)):
        yield {frozenset(p):v for p,v in zip(pairs,states) if v}
