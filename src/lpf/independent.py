"""Independent nodal admittance assembly, algebraic cross-check of MNA."""
import numpy as np
from .circuit import incidence
def solve_gain(f_hz,n_nodes,source_node,load_node,inductors=(),capacitors=(),
               coupling=None,source_voltage=1.0,source_ohms=50.0,load_ohms=60-40j):
    w=2*np.pi*f_hz; L=list(inductors); C=list(capacitors); n=len(L)
    k=np.eye(n) if coupling is None else np.asarray(coupling,float)
    values=np.array([x.value for x in L])
    M=k*np.sqrt(np.outer(values,values))
    if n and np.linalg.eigvalsh(M).min()<=0: raise ValueError('Non-PD inductance')
    Y=np.zeros((n_nodes,n_nodes),complex)
    if n:
        Z=1j*w*M+np.diag(w*values/np.array([x.q for x in L]))
        B=incidence(L,n_nodes)
        Y+=B@np.linalg.solve(Z,B.T)
    for c in C:
        b=incidence([c],n_nodes)[:,0]
        Y+=np.outer(b,b)*w*c.value/(1/c.q-1j)
    Y[source_node-1,source_node-1]+=1/source_ohms
    Y[load_node-1,load_node-1]+=1/load_ohms
    rhs=np.zeros(n_nodes,complex);rhs[source_node-1]=source_voltage/source_ohms
    v=np.linalg.solve(Y,rhs)
    return float((abs(v[load_node-1])**2*(1/load_ohms).real)/(abs(source_voltage)**2/(4*source_ohms)))
