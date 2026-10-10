"""Coupling-matrix validation for real symmetric inductance matrices."""
import numpy as np

def positive_definite_inductance(matrix):
    a=np.asarray(matrix,dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.all(np.isfinite(a)):
        return False
    if not np.allclose(a,a.T,rtol=1e-10,atol=1e-15):
        return False
    try:
        np.linalg.cholesky(a)
        return True
    except np.linalg.LinAlgError:
        return False
