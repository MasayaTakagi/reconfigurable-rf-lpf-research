"""Independent nodal-admittance analysis, separate from augmented main MNA."""
import numpy as np


def _checked_solve(matrix, rhs, label):
    condition=float(np.linalg.cond(matrix))
    if not np.isfinite(condition) or condition>1e13:
        raise ValueError(f"{label} system is singular or ill-conditioned (cond={condition:.3g})")
    result=np.linalg.solve(matrix,rhs)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} system returned non-finite values")
    return result,condition


def solve_state(f_hz, n_nodes, source_node, load_node, inductors=(), capacitors=(),
                coupling=None, source_voltage=1.0, source_ohms=50.0,
                load_ohms=60-40j):
    """Solve by eliminating inductor currents and locally stamping nodal Y.

    Branch endpoints are expanded into node/sign pairs here; no main-MNA
    incidence matrix or assembly routine is imported or shared.
    """
    if (not np.isfinite(f_hz) or f_hz<=0 or type(n_nodes) is not int or n_nodes<1
            or not 1<=source_node<=n_nodes or not 1<=load_node<=n_nodes
            or not np.isfinite(source_ohms) or source_ohms<=0
            or not np.isfinite(load_ohms.real) or not np.isfinite(load_ohms.imag)
            or load_ohms.real<=0
            or not np.isfinite(source_voltage.real) or not np.isfinite(source_voltage.imag)
            or abs(source_voltage)==0):
        raise ValueError("Invalid circuit inputs")
    w=2*np.pi*f_hz
    inductors=tuple(inductors);capacitors=tuple(capacitors);n=len(inductors)
    values=np.array([x.value for x in inductors],float)
    qs=np.array([x.q for x in inductors],float)
    if (np.any(~np.isfinite(values)) or np.any(~np.isfinite(qs))
            or np.any(values<=0) or np.any(qs<=0)):
        raise ValueError("Invalid inductors")
    k=np.eye(n) if coupling is None else np.asarray(coupling,float)
    if (k.shape!=(n,n) or np.any(~np.isfinite(k))
            or not np.allclose(k,k.T,atol=1e-12,rtol=0)
            or not np.allclose(np.diag(k),1,atol=1e-12,rtol=0)):
        raise ValueError("Invalid magnetic coupling matrix")
    mutual=np.sqrt(values[:,None]*values[None,:])*k if n else np.zeros((0,0))
    if n:
        eigenvalues=np.linalg.eigvalsh(mutual)
        if eigenvalues.min()<=eigenvalues.max()*1e-12:
            raise ValueError("Non-positive-definite or ill-conditioned inductance matrix")
        z=np.diag(w*values/qs)+1j*w*mutual
        z_inverse,_=_checked_solve(z,np.eye(n,dtype=complex),"Inductor impedance")
    else:
        eigenvalues=np.array([]);z=np.zeros((0,0),complex);z_inverse=np.zeros((0,0),complex)

    y=np.zeros((n_nodes,n_nodes),complex)
    branch_pairs=[]
    for coil in inductors:
        if (type(coil.a) is not int or type(coil.b) is not int or coil.a==coil.b
                or min(coil.a,coil.b)<0 or max(coil.a,coil.b)>n_nodes):
            raise ValueError("Invalid inductor nodes")
        branch_pairs.append(((coil.a-1,1) if coil.a else None,
                             (coil.b-1,-1) if coil.b else None))
    for i,(a,b) in enumerate(branch_pairs):
        for j,(c,d) in enumerate(branch_pairs):
            gij=z_inverse[i,j]
            for left in (a,b):
                if left is None:continue
                for right in (c,d):
                    if right is not None:
                        y[left[0],right[0]]+=left[1]*right[1]*gij

    cap_admittances=[]
    for capacitor in capacitors:
        if (type(capacitor.a) is not int or type(capacitor.b) is not int
                or capacitor.a==capacitor.b or min(capacitor.a,capacitor.b)<0
                or max(capacitor.a,capacitor.b)>n_nodes
                or not np.isfinite(capacitor.value) or capacitor.value<0
                or not np.isfinite(capacitor.q) or capacitor.q<=0):
            raise ValueError("Invalid capacitor")
        adm=w*capacitor.value/(1/capacitor.q-1j)
        cap_admittances.append(adm)
        if capacitor.a:
            a=capacitor.a-1;y[a,a]+=adm
        if capacitor.b:
            b=capacitor.b-1;y[b,b]+=adm
        if capacitor.a and capacitor.b:
            a,b=capacitor.a-1,capacitor.b-1
            y[a,b]-=adm;y[b,a]-=adm
    y[source_node-1,source_node-1]+=1/source_ohms
    y[load_node-1,load_node-1]+=1/load_ohms
    current=np.zeros(n_nodes,complex);current[source_node-1]=source_voltage/source_ohms
    voltage,condition=_checked_solve(y,current,"Nodal admittance")

    inductor_drop=np.array([
        (voltage[coil.a-1] if coil.a else 0)
        -(voltage[coil.b-1] if coil.b else 0) for coil in inductors],complex)
    inductor_current,_=_checked_solve(z,inductor_drop,"Inductor impedance") if n else (
        np.zeros(0,complex),1.0)
    cap_current=np.array([
        adm*((voltage[cap.a-1] if cap.a else 0)
             -(voltage[cap.b-1] if cap.b else 0))
        for cap,adm in zip(capacitors,cap_admittances)],complex)
    p_inductor=float(np.sum(w*values/qs*np.abs(inductor_current)**2))
    p_capacitor=float(sum(adm.real*abs(
        (voltage[cap.a-1] if cap.a else 0)
        -(voltage[cap.b-1] if cap.b else 0))**2
        for cap,adm in zip(capacitors,cap_admittances)))
    p_load=float(abs(voltage[load_node-1])**2*(1/load_ohms).real)
    p_available=float(abs(source_voltage)**2/(4*source_ohms))
    p_reflected=float(abs(source_voltage-2*voltage[source_node-1])**2/(4*source_ohms))
    residual=p_available-p_load-p_reflected-p_inductor-p_capacitor
    if abs(residual)>max(1e-12,p_available*1e-9):
        raise ValueError(f"Independent power conservation failed (residual={residual:.3g} W)")
    return {
        "voltage":voltage,"inductor_current":inductor_current,
        "capacitor_current":cap_current,"gain":p_load/p_available,
        "p_available":p_available,"p_load":p_load,"p_reflected":p_reflected,
        "p_inductor":p_inductor,"p_capacitor":p_capacitor,
        "power_residual":residual,"nodal_condition_number":condition,
        "min_inductance_eigenvalue":float(eigenvalues.min()) if n else None,
    }


def solve_gain(f_hz, n_nodes, source_node, load_node, inductors=(), capacitors=(),
               coupling=None, source_voltage=1.0, source_ohms=50.0,
               load_ohms=60-40j):
    """Backward-compatible scalar interface for the independent nodal solver."""
    return solve_state(f_hz,n_nodes,source_node,load_node,inductors,capacitors,
                       coupling,source_voltage,source_ohms,load_ohms)["gain"]
