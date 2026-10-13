"""Physical topology and positive-definite coupling checks."""
import numpy as np
from .constraint_versions import load_constraint

def positive_definite_inductance(matrix):
    a=np.asarray(matrix,float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.all(np.isfinite(a)): return False
    if not np.allclose(a,a.T,rtol=1e-10,atol=1e-15): return False
    try:
        np.linalg.cholesky(a)
        return True
    except np.linalg.LinAlgError:
        return False

def validate_couplings(k,types,chip_order,strong_pairs=(),nominal=True,*,resolved_policy=None):
    """Validate couplings against active formal limits, or a pinned historical policy."""
    policy = load_constraint() if resolved_policy is None else resolved_policy
    limits = policy["coupling_limits"]
    a=np.asarray(k,float);n=len(types);errors=[]
    if a.shape!=(n,n) or not np.all(np.isfinite(a)): return ["Invalid coupling matrix"]
    if not np.allclose(a,a.T,atol=1e-12): errors.append("Asymmetric coupling")
    if not np.allclose(np.diag(a),1,atol=1e-12): errors.append("Invalid diagonal")
    if sorted(chip_order)!=[i for i,t in enumerate(types) if t=="chip"]:
        errors.append("Invalid chip physical order")
    adjacent={frozenset((i,j)) for i,j in zip(chip_order,chip_order[1:])}
    strong={frozenset(pair) for pair in strong_pairs}
    if not strong<=adjacent: errors.append("Nonadjacent strong pair")
    for i in range(n):
        for j in range(i+1,n):
            pair=frozenset((i,j))
            if types[i]=="chip" and types[j]=="chip":
                limit=(limits["chip_chip_strong_adjacent_abs_k_max"] if pair in strong
                       else (0 if nominal else limits["chip_chip_nonstrong_abs_k_max"]))
            elif types[i]=="pcb" and types[j]=="pcb": limit=limits["pcb_pcb_abs_k_max_default"]
            else: limit=limits["chip_pcb_abs_k_max"]
            if abs(a[i,j])>limit+1e-12: errors.append("Coupling limit exceeded: %d,%d"%(i,j))
    if not positive_definite_inductance(a): errors.append("Non-positive-definite coupling")
    return errors
