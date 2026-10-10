"""Physical topology and positive-definite coupling checks."""
import numpy as np

def positive_definite_inductance(matrix):
    a=np.asarray(matrix,float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.all(np.isfinite(a)): return False
    if not np.allclose(a,a.T,rtol=1e-10,atol=1e-15): return False
    try:
        np.linalg.cholesky(a)
        return True
    except np.linalg.LinAlgError:
        return False

def validate_couplings(k,types,chip_order,strong_pairs=(),nominal=True):
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
                limit=.4 if pair in strong else (0 if nominal else .1)
            elif types[i]=="pcb" and types[j]=="pcb": limit=.6
            else: limit=.03
            if abs(a[i,j])>limit+1e-12: errors.append("Coupling limit exceeded: %d,%d"%(i,j))
    if not positive_definite_inductance(a): errors.append("Non-positive-definite coupling")
    return errors
