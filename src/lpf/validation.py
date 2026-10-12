"""Third-formulation circuit checks and independent connection audits."""
from collections import Counter

import numpy as np


def _checked_solve(matrix,rhs,label):
    condition=float(np.linalg.cond(matrix))
    if not np.isfinite(condition) or condition>1e13:
        raise ValueError(f"{label} is singular or ill-conditioned (cond={condition:.3g})")
    result=np.linalg.solve(matrix,rhs)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} returned non-finite values")
    return result,condition


def _edge_counts(branches):
    return Counter((branch.a,branch.b) for branch in branches)


def validate_connection_map(params, *, expected_inductor_edges=None,
                            expected_capacitor_edges=None):
    """Compare solver branches to an independently retained source topology map."""
    if expected_inductor_edges is not None:
        expected=Counter(tuple(edge) for edge in expected_inductor_edges)
        if _edge_counts(params.get("inductors",()))!=expected:
            raise ValueError("Inductor connection map differs from source topology")
    if expected_capacitor_edges is not None:
        expected=Counter(tuple(edge) for edge in expected_capacitor_edges)
        if _edge_counts(params.get("capacitors",()))!=expected:
            raise ValueError("Capacitor connection map differs from source topology")
    return True


def validate_inductor_coupling(types,values,coupling,physical_order=None,*,nominal=True):
    """Enforce RF-F001 nominal or explicit weak-coupling sensitivity rules.

    Nonadjacent chip pairs have nominal k=0. Only nominal=False permits
    |k|<=0.1 for a separate weak-coupling sensitivity calculation.
    """
    k=np.asarray(coupling,float);l=np.asarray(values,float);n=len(types)
    if type(nominal) is not bool:raise ValueError('nominal must be a boolean')
    if (l.shape!=(n,) or np.any(~np.isfinite(l)) or np.any(l<=0)
            or k.shape!=(n,n) or np.any(~np.isfinite(k))
            or not np.allclose(k,k.T,atol=1e-12,rtol=0)
            or not np.allclose(np.diag(k),1,atol=1e-12,rtol=0)):
        raise ValueError("Invalid coupling or inductor values")
    if n==0:
        return {"min_inductance_eigenvalue":None,
                "max_inductance_eigenvalue":None,
                "inductance_condition_number":None}
    chips=[i for i,t in enumerate(types)
           if t in ("LQP01","LQP02","LQP02HV","LQP02HQ","LQW04")]
    pcbs=[i for i,t in enumerate(types) if t=="PCB_L"]
    if len(pcbs)>3:raise ValueError("PCB count exceeds three")
    order=chips if physical_order is None else list(physical_order)
    if sorted(order)!=sorted(chips):raise ValueError("Physical chip order is invalid")
    adjacent={frozenset((a,b)) for a,b in zip(order,order[1:])}
    for i in range(n):
        for j in range(i+1,n):
            pair=frozenset((i,j));value=abs(k[i,j])
            if i in chips and j in chips:
                limit=.4 if pair in adjacent else (0.0 if nominal else .1)
            elif (i in chips and j in pcbs) or (j in chips and i in pcbs):
                limit=.03
            elif i in pcbs and j in pcbs:
                limit=.6
            else:
                limit=0.0
            if value>limit+1e-12:
                raise ValueError("Strong chip coupling is forbidden for physically nonadjacent inductors")
    mutual=k*np.sqrt(np.outer(l,l))
    eigenvalues=np.linalg.eigvalsh(mutual)
    if eigenvalues.min()<=eigenvalues.max()*1e-12:
        raise ValueError("Full inductance matrix is non-positive-definite or ill-conditioned")
    return {"min_inductance_eigenvalue":float(eigenvalues.min()),
            "max_inductance_eigenvalue":float(eigenvalues.max()),
            "inductance_condition_number":float(eigenvalues.max()/eigenvalues.min())}


def solve_branch_current(f_hz,n_nodes,source_node,load_node,inductors=(),
                         capacitors=(),coupling=None,source_voltage=1.0,
                         source_ohms=50.0,load_ohms=60-40j):
    """Independent all-branch-current MNA, including finite-Q capacitor currents."""
    if (not np.isfinite(f_hz) or f_hz<=0 or type(n_nodes) is not int or n_nodes<1
            or not 1<=source_node<=n_nodes or not 1<=load_node<=n_nodes
            or not np.isfinite(source_ohms) or source_ohms<=0
            or not np.isfinite(load_ohms.real) or not np.isfinite(load_ohms.imag)
            or load_ohms.real<=0
            or not np.isfinite(source_voltage.real) or not np.isfinite(source_voltage.imag)
            or abs(source_voltage)==0):
        raise ValueError("Invalid circuit inputs")
    inductors=tuple(inductors);capacitors=tuple(capacitors);nl=len(inductors)
    w=2*np.pi*f_hz
    l=np.asarray([x.value for x in inductors],float)
    ql=np.asarray([x.q for x in inductors],float)
    if np.any(~np.isfinite(l)) or np.any(l<=0) or np.any(~np.isfinite(ql)) or np.any(ql<=0):
        raise ValueError("Invalid inductor values or Q")
    k=np.eye(nl) if coupling is None else np.asarray(coupling,float)
    if (k.shape!=(nl,nl) or np.any(~np.isfinite(k))
            or not np.allclose(k,k.T,atol=1e-12,rtol=0)
            or not np.allclose(np.diag(k),1,atol=1e-12,rtol=0)):
        raise ValueError("Invalid coupling matrix")
    mutual=k*np.sqrt(np.outer(l,l)) if nl else np.zeros((0,0))
    if nl:
        eig=np.linalg.eigvalsh(mutual)
        if eig.min()<=eig.max()*1e-12:
            raise ValueError("Full inductance matrix is non-positive-definite or ill-conditioned")
        z_l=np.diag(w*l/ql)+1j*w*mutual
    else:z_l=np.zeros((0,0),complex)
    cap_active=[];cap_indices=[];cap_impedances=[]
    for index,cap in enumerate(capacitors):
        if (type(cap.a) is not int or type(cap.b) is not int or cap.a==cap.b
                or min(cap.a,cap.b)<0 or max(cap.a,cap.b)>n_nodes
                or not np.isfinite(cap.value) or cap.value<0
                or not np.isfinite(cap.q) or cap.q<=0):
            raise ValueError("Invalid capacitor")
        if cap.value>0:
            cap_active.append(cap);cap_indices.append(index)
            cap_impedances.append((1/cap.q-1j)/(w*cap.value))
    branches=inductors+tuple(cap_active);nb=len(branches)
    bmat=np.zeros((n_nodes,nb),complex)
    for j,branch in enumerate(branches):
        if (type(branch.a) is not int or type(branch.b) is not int
                or branch.a==branch.b or min(branch.a,branch.b)<0
                or max(branch.a,branch.b)>n_nodes):
            raise ValueError("Invalid branch endpoints")
        if branch.a:bmat[branch.a-1,j]+=1
        if branch.b:bmat[branch.b-1,j]-=1
    y=np.zeros((n_nodes,n_nodes),complex)
    y[source_node-1,source_node-1]+=1/source_ohms
    y[load_node-1,load_node-1]+=1/load_ohms
    z=np.zeros((nb,nb),complex)
    if nl:z[:nl,:nl]=z_l
    for j,impedance in enumerate(cap_impedances,nl):z[j,j]=impedance
    a=np.block([[y,bmat],[-bmat.T,z]])
    rhs=np.zeros(n_nodes+nb,complex);rhs[source_node-1]=source_voltage/source_ohms
    solution,condition=_checked_solve(a,rhs,"Branch-current MNA")
    voltage=solution[:n_nodes];currents=solution[n_nodes:]
    i_l=currents[:nl];i_c=np.zeros(len(capacitors),complex)
    for offset,index in enumerate(cap_indices):i_c[index]=currents[nl+offset]
    p_available=float(abs(source_voltage)**2/(4*source_ohms))
    p_load=float(abs(voltage[load_node-1])**2*(1/load_ohms).real)
    p_reflected=float(abs(source_voltage-2*voltage[source_node-1])**2/(4*source_ohms))
    p_inductor=float(np.sum(w*l/ql*np.abs(i_l)**2))
    p_cap=float(sum(abs(i_c[i])**2/(w*c.value*c.q)
                    for i,c in enumerate(capacitors) if c.value>0))
    residual=p_available-p_load-p_reflected-p_inductor-p_cap
    if abs(residual)>max(1e-12,p_available*1e-9):
        raise ValueError(f"Branch-current MNA power conservation failed (residual={residual:.3g} W)")
    return {"voltage":voltage,"inductor_current":i_l,"capacitor_current":i_c,
            "gain":p_load/p_available,"p_available":p_available,"p_load":p_load,
            "p_reflected":p_reflected,"p_inductor":p_inductor,"p_capacitor":p_cap,
            "power_residual":residual,"condition_number":condition,
            "min_inductance_eigenvalue":float(np.linalg.eigvalsh(mutual).min()) if nl else None}


def validate_circuit(params,frequencies_hz,*,expected_inductor_edges=None,
                     expected_capacitor_edges=None,inductor_types=None,
                     physical_order=None,gain_atol=1e-10,nominal=True):
    """Compare main MNA, nodal elimination, and all-branch-current MNA per Hz."""
    from .circuit import solve
    from .independent import solve_state
    validate_connection_map(params,expected_inductor_edges=expected_inductor_edges,
                            expected_capacitor_edges=expected_capacitor_edges)
    lmat=np.asarray(params.get("coupling") if params.get("coupling") is not None
                    else np.eye(len(params.get("inductors",()))),float)
    lv=[x.value for x in params.get("inductors",())]
    eigen={"min_inductance_eigenvalue":None}
    if inductor_types:
        eigen=validate_inductor_coupling(inductor_types,lv,lmat,physical_order,
                                         nominal=nominal)
    discrepancies=[];residuals=[];condition_numbers=[]
    for f_hz in frequencies_hz:
        primary=solve(f_hz,**params)
        nodal=solve_state(f_hz,**params)
        branch=solve_branch_current(f_hz,**params)
        gains=(primary["gain"],nodal["gain"],branch["gain"])
        discrepancy=max(abs(gains[0]-gains[1]),abs(gains[0]-gains[2]),abs(gains[1]-gains[2]))
        if discrepancy>gain_atol:
            raise ValueError(f"Independent gain mismatch at {f_hz:g} Hz: {discrepancy:.3g}")
        discrepancies.append(discrepancy)
        residuals.extend(abs(result["power_residual"]) for result in (primary,nodal,branch))
        condition_numbers.append(primary.get("mna_condition_number",0))
        condition_numbers.extend((nodal["nodal_condition_number"],branch["condition_number"]))
    return {"frequencies_hz":list(map(float,frequencies_hz)),
            "frequency_count":len(discrepancies),
            "max_gain_discrepancy":max(discrepancies,default=0.0),
            "max_power_residual_w":max(residuals,default=0.0),
            "max_condition_number":max(condition_numbers,default=0.0),
            **eigen}
