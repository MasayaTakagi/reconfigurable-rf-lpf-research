"""Deterministic Phase 2 checks for two magnetic-coupling pairs in a 3L T.
Not a numbered optimization EXP; ideal C, constant intrinsic coil Q.
"""
import numpy as np

B = np.array([[1., 0.], [0., -1.], [1., 1.]])
A = np.array([[1., -1., 0.], [0., 1., -1.], [0., 1., 0.]])
PATTERNS = {
    "input": ((0, 1, +1), (0, 2, +1)),
    "output": ((0, 1, +1), (1, 2, -1)),
    "shunt": ((0, 2, +1), (1, 2, -1)),
}
HUB = {"input": 0, "output": 1, "shunt": 2}


def normalized_L(hub: str, k: float) -> np.ndarray:
    mat = np.eye(3)
    for i, j, sign in PATTERNS[hub]:
        mat[i, j] = mat[j, i] = sign*k
    return mat


def modal_eigenvalues(hub: str, k: float) -> np.ndarray:
    gram = B.T @ B
    invchol = np.linalg.inv(np.linalg.cholesky(gram))
    return np.linalg.eigvalsh(
        invchol @ (B.T @ normalized_L(hub, k) @ B) @ invchol.T)


def test_modal_bounds_and_passivity() -> None:
    for hub in HUB:
        for k in (0.01, 0.10, 0.20, 0.40, 0.60):
            assert np.allclose(modal_eigenvalues(hub, k), [1, 1+4*k/3],
                               atol=1e-12)
            assert np.isclose(np.linalg.eigvalsh(normalized_L(hub, k)).min(),
                              1-np.sqrt(2)*k)


def test_equivalent_branch_inductance() -> None:
    original = 10e-9
    k = 0.40
    for hub in HUB:
        actual = B.T @ (original*normalized_L(hub, k)) @ B
        equivalent = np.full(3, original)
        equivalent[HUB[hub]] *= 1+2*k
        assert np.allclose(actual, B.T @ np.diag(equivalent) @ B,
                           atol=1e-22)


def test_all_complex_currents_non_degradation() -> None:
    samples = [
        np.array([1, 1, 0], dtype=complex),
        np.array([1, .9, .1], dtype=complex),
        np.array([1, .5, .5], dtype=complex),
        np.array([1, 0, 1], dtype=complex),
        np.array([1, 1-.5j, .5j]),
        np.array([0, -1, 1], dtype=complex),
    ]
    for hub in HUB:
        for currents in samples:
            k=.40
            norm=np.vdot(currents, currents).real
            q=25*np.vdot(currents, normalized_L(hub, k)@currents).real/norm
            analytical=25*(1+2*k*abs(currents[HUB[hub]])**2/norm)
            assert abs(q-analytical)<1e-12
            assert q>=25-1e-12


FREQ = 1e9
OMEGA = 2*np.pi*FREQ
SOURCE_R = LOAD_R = 50.
L_TARGET = 10e-9
Q0 = 25.
XSERIES = 20.
XSHUNT = -72.5
CAPS = np.array([
    1/(OMEGA*(OMEGA*L_TARGET-XSERIES)),
    1/(OMEGA*(OMEGA*L_TARGET-XSERIES)),
    1/(OMEGA*(OMEGA*L_TARGET-XSHUNT)),
])


def circuit(hub: str | None, k: float):
    Lvec = np.full(3, L_TARGET)
    Lmat = np.diag(Lvec.copy())
    if hub is not None:
        h = HUB[hub]
        alpha=np.sqrt(1+k*k)-k
        Lvec[h]=L_TARGET*alpha**2
        mutual=k*np.sqrt(Lvec[h]*L_TARGET)
        assert np.isclose(Lvec[h]+2*mutual, L_TARGET, rtol=1e-12)
        Lmat=np.diag(Lvec.copy())
        for i,j,sign in PATTERNS[hub]:
            Lmat[i,j]=Lmat[j,i]=sign*mutual
    Rmat=np.diag(OMEGA*Lvec/Q0)
    Z=Rmat+1j*OMEGA*Lmat+np.diag(1/(1j*OMEGA*CAPS))
    Zport=B.T@Z@B
    ports=np.linalg.solve(Zport+np.diag([SOURCE_R,LOAD_R]),
                          np.array([1.+0j,0j]))
    branches=B@ports
    # Independently solve Vin,Vmid,Vout nodal voltages.
    Ynodal=A.T@np.linalg.solve(Z,A)+np.diag([1/SOURCE_R,0,1/LOAD_R])
    voltages=np.linalg.solve(Ynodal, np.array([1/SOURCE_R,0,0]))
    currents2=np.linalg.solve(Z,A@voltages)
    Pload=LOAD_R*abs(ports[1])**2
    Pdiss=np.vdot(branches,Rmat@branches).real
    Pin=(voltages[0]*((1-voltages[0])/SOURCE_R).conjugate()).real
    IL=-10*np.log10(Pload/(1/(4*SOURCE_R)))
    return IL,Pdiss,Pload,np.max(np.abs(currents2-branches)),Pin-Pload-Pdiss,Lmat


def test_same_ideal_reactance_independent_mna_and_power() -> None:
    expected={
        "input": (.4374325884821224, .0004780863305442332),
        "output": (.43743258848212085, .00047780316306749177),
        "shunt": (.48788906107051755, .0005272561907092054),
    }
    base=circuit(None, .4)
    assert abs(base[0]-.554499313269968)<1e-12
    assert abs(base[1]-.0005970554352457503)<1e-14
    for hub,(target_il,target_power) in expected.items():
        il,loss,p_load,diff,pbal,Lmat=circuit(hub,.4)
        assert np.allclose(B.T@Lmat@B,
                           B.T@(np.eye(3)*L_TARGET)@B,atol=2e-23)
        assert abs(il-target_il)<1e-12
        assert abs(loss-target_power)<1e-14
        assert diff<1e-13 and abs(pbal)<1e-13
        assert il<base[0]


def test_unintended_third_pair_breaks_robustness() -> None:
    for leakage in (-.02, 0, +.02):
        mat=normalized_L("input",.4)
        mat[1,2]=mat[2,1]=leakage
        invchol=np.linalg.inv(np.linalg.cholesky(B.T@B))
        modes=np.linalg.eigvalsh(invchol@(B.T@mat@B)@invchol.T)
        assert abs(modes[0]-(1-leakage))<1e-12
        assert np.linalg.eigvalsh(mat).min()>0
