"""Coupled-inductor MNA with RMS phasors; nodes are numbered from 1, ground=0."""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Branch:
    a: int
    b: int
    value: float
    q: float

def incidence(branches, n):
    b=np.zeros((n,len(branches)),complex)
    for j,x in enumerate(branches):
        for node,sign in ((x.a,1),(x.b,-1)):
            if node:
                if node<1 or node>n: raise ValueError("Invalid node")
                b[node-1,j]+=sign
    return b

def solve(f_hz,n_nodes,source_node,load_node,inductors=(),capacitors=(),
          coupling=None,source_voltage=1.0,source_ohms=50.0,load_ohms=60-40j):
    if f_hz<=0 or n_nodes<1 or source_ohms<=0 or load_ohms.real<=0:
        raise ValueError("Invalid frequency or termination")
    if not 1<=source_node<=n_nodes or not 1<=load_node<=n_nodes:
        raise ValueError("Invalid source/load node")
    L=list(inductors); C=list(capacitors); w=2*np.pi*f_hz; nl=len(L)
    if any(x.value<=0 or x.q<=0 for x in L) or any(x.value<0 or x.q<=0 for x in C):
        raise ValueError("Positive component value and Q required")
    K=np.eye(nl) if coupling is None else np.asarray(coupling,float)
    if K.shape!=(nl,nl) or not np.all(np.isfinite(K)) or not np.allclose(K,K.T,atol=1e-12) or not np.allclose(np.diag(K),1):
        raise ValueError("Invalid coupling matrix")
    lv=np.array([x.value for x in L])
    M=K*np.sqrt(np.outer(lv,lv))
    if nl and np.linalg.eigvalsh(M).min()<=0: raise ValueError("Non-positive-definite inductance matrix")
    B=incidence(L,n_nodes); Y=np.zeros((n_nodes,n_nodes),complex)
    for cap in C:
        b=incidence([cap],n_nodes)[:,0]
        if cap.value==0: continue
        z=(1/cap.q-1j)/(w*cap.value)
        Y+=np.outer(b,b)/z
    Y[source_node-1,source_node-1]+=1/source_ohms
    Y[load_node-1,load_node-1]+=1/load_ohms
    Z=1j*w*M+np.diag(w*lv/np.array([x.q for x in L])) if nl else np.empty((0,0),complex)
    A=np.block([[Y,B],[-B.T,Z]])
    rhs=np.zeros(n_nodes+nl,complex);rhs[source_node-1]=source_voltage/source_ohms
    sol=np.linalg.solve(A,rhs);v=sol[:n_nodes];iL=sol[n_nodes:]
    iC=np.array([(incidence([c],n_nodes)[:,0]@v)*w*c.value/(1/c.q-1j) for c in C])
    pC=sum(abs(i)**2/(w*c.value*c.q) for i,c in zip(iC,C) if c.value>0)
    pL=sum(abs(i)**2*w*l.value/l.q for i,l in zip(iL,L))
    pLoad=abs(v[load_node-1])**2*(1/load_ohms).real
    pAvs=abs(source_voltage)**2/(4*source_ohms)
    pRef=abs(source_voltage-2*v[source_node-1])**2/(4*source_ohms)
    gain=pLoad/pAvs
    return dict(voltage=v,inductor_current=iL,capacitor_current=iC,
                gain=gain,il_db=-10*np.log10(gain) if gain>0 else float('inf'),
                p_available=pAvs,p_load=pLoad,p_reflected=pRef,
                p_inductor=pL,p_capacitor=pC,
                power_residual=pAvs-pLoad-pRef-pL-pC)
