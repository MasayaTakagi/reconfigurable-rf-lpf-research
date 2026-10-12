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

def _checked_solve(matrix,rhs,label):
    """Reject numerically rank-deficient systems before trusting a solve."""
    condition=float(np.linalg.cond(matrix))
    if not np.isfinite(condition) or condition>1e13:
        raise ValueError(f'{label} system is singular or ill-conditioned (cond={condition:.3g})')
    result=np.linalg.solve(matrix,rhs)
    if not np.all(np.isfinite(result)):
        raise ValueError(f'{label} system returned non-finite values')
    return result,condition

def _valid_branch(branch,n_nodes,*,capacitor=False):
    if (type(branch.a) is not int or type(branch.b) is not int
            or branch.a==branch.b or min(branch.a,branch.b)<0
            or max(branch.a,branch.b)>n_nodes):
        raise ValueError('Invalid component branch endpoints')
    if (not np.isfinite(branch.value) or branch.value < 0
            or (not capacitor and branch.value==0)
            or not np.isfinite(branch.q) or branch.q<=0):
        raise ValueError('Invalid component value or Q')

def solve(f_hz,n_nodes,source_node,load_node,inductors=(),capacitors=(),
          coupling=None,source_voltage=1.0,source_ohms=50.0,load_ohms=60-40j):
    if (not np.isfinite(f_hz) or f_hz<=0 or type(n_nodes) is not int or n_nodes<1
            or not np.isfinite(source_ohms) or source_ohms<=0
            or not np.isfinite(load_ohms.real) or not np.isfinite(load_ohms.imag)
            or load_ohms.real<=0
            or not np.isfinite(source_voltage.real) or not np.isfinite(source_voltage.imag)
            or abs(source_voltage)==0):
        raise ValueError("Invalid frequency or termination")
    if not 1<=source_node<=n_nodes or not 1<=load_node<=n_nodes:
        raise ValueError("Invalid source/load node")
    L=list(inductors); C=list(capacitors); w=2*np.pi*f_hz; nl=len(L)
    for branch in L:_valid_branch(branch,n_nodes)
    for branch in C:_valid_branch(branch,n_nodes,capacitor=True)
    K=np.eye(nl) if coupling is None else np.asarray(coupling,float)
    if K.shape!=(nl,nl) or not np.all(np.isfinite(K)) or not np.allclose(K,K.T,atol=1e-12) or not np.allclose(np.diag(K),1):
        raise ValueError("Invalid coupling matrix")
    lv=np.array([x.value for x in L])
    M=K*np.sqrt(np.outer(lv,lv))
    if nl:
        eigenvalues=np.linalg.eigvalsh(M)
        if eigenvalues.min()<=eigenvalues.max()*1e-12:
            raise ValueError("Non-positive-definite or ill-conditioned inductance matrix")
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
    sol,condition=_checked_solve(A,rhs,'MNA');v=sol[:n_nodes];iL=sol[n_nodes:]
    iC=np.array([(incidence([c],n_nodes)[:,0]@v)*w*c.value/(1/c.q-1j) for c in C])
    pC=sum(abs(i)**2/(w*c.value*c.q) for i,c in zip(iC,C) if c.value>0)
    pL=sum(abs(i)**2*w*l.value/l.q for i,l in zip(iL,L))
    pLoad=abs(v[load_node-1])**2*(1/load_ohms).real
    pAvs=abs(source_voltage)**2/(4*source_ohms)
    pRef=abs(source_voltage-2*v[source_node-1])**2/(4*source_ohms)
    gain=pLoad/pAvs
    residual=pAvs-pLoad-pRef-pL-pC
    if abs(residual)>max(1e-12,pAvs*1e-9):
        raise ValueError(f'Power conservation check failed (residual={residual:.3g} W)')
    return dict(voltage=v,inductor_current=iL,capacitor_current=iC,
                gain=gain,il_db=-10*np.log10(gain) if gain>0 else float('inf'),
                p_available=pAvs,p_load=pLoad,p_reflected=pRef,
                p_inductor=pL,p_capacitor=pC,power_residual=residual,
                mna_condition_number=condition,
                min_inductance_eigenvalue=float(np.linalg.eigvalsh(M).min()) if nl else None)
