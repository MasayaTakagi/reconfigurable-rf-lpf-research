"""Deterministic Phase-2 theoretical checks for a 3L T network.

This file is NOT an EXP-NNN optimization run. It verifies algebraic identities
and one explicitly defined 1 GHz benchmark; no LPF constraints are evaluated.
Inductor Q is assumed constant when L changes. Capacitors are ideal.
"""

import numpy as np

B = np.array([[1.0, 0.0], [0.0, -1.0], [1.0, 1.0]])
A = np.array([[1.0, -1.0, 0.0],
              [0.0, 1.0, -1.0],
              [0.0, 1.0, 0.0]])
N = np.array([1.0, -1.0, -1.0])


def balanced_k(k: float) -> np.ndarray:
    return np.array([[1.0, k, k], [k, 1.0, -k], [k, -k, 1.0]])


def branch_network(k: float, Lhenry: float, freq_hz: float,
                   q: float, series_cap_f: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    omega = 2.0 * np.pi * freq_hz
    Lmatrix = Lhenry * balanced_k(k)
    Rmatrix = np.eye(3) * omega * Lhenry / q
    Zc = np.diag(1.0 / (1j * omega * series_cap_f))
    return Rmatrix + 1j * omega * Lmatrix + Zc, Rmatrix, Lmatrix


def solve_by_two_port(Zbranch: np.ndarray, source_r: float = 50.0,
                      load_r: float = 50.0) -> tuple[np.ndarray, np.ndarray]:
    # Iout points into the T network, so I2 = -Iout.
    Zport = B.T @ Zbranch @ B
    Iport = np.linalg.solve(
        Zport + np.diag([source_r, load_r]),
        np.array([1.0, 0.0], dtype=complex))
    return Iport, B @ Iport


def solve_by_independent_nodal(Zbranch: np.ndarray, source_r: float = 50.0,
                               load_r: float = 50.0) -> tuple[np.ndarray, np.ndarray]:
    # Explicit Vin, Vm, Vout with a Norton source at Vin.
    G = np.diag([1.0/source_r, 0.0, 1.0/load_r])
    V = np.linalg.solve(
        A.T @ np.linalg.solve(Zbranch, A) + G,
        np.array([1.0/source_r, 0.0, 0.0], dtype=complex))
    Ibranch = np.linalg.solve(Zbranch, A @ V)
    return V, Ibranch


def test_all_current_modes_are_scaled() -> None:
    k = 0.4
    K = balanced_k(k)
    assert np.linalg.eigvalsh(K).min() > 0
    assert np.allclose(K @ B, (1+k) * B, atol=1e-14)
    assert np.allclose(B.T @ K @ B, (1+k) * (B.T @ B), atol=1e-14)
    # No choice of complex terminal currents spoils this identity.
    for currents in (
        np.array([1.0+0j, -0.5+0j]),
        np.array([1+1j, 0.2-0.7j]),
        np.array([0+0j, 1.0+0j]),
    ):
        I = B @ currents
        modal_gain = np.vdot(I, K @ I).real / np.vdot(I, I).real
        assert abs(modal_gain - 1.4) < 1e-14


def test_analytic_minimum_mode_bound() -> None:
    # |k_ij|<=k means mode (I1,I2,I3)=(1,1,0) has gain <= 1+k.
    # Balanced K attains that bound on the entire KCL subspace.
    k = 0.4
    K = balanced_k(k)
    I = np.array([1.0, 1.0, 0.0])
    assert abs(np.dot(I, K @ I) / np.dot(I, I) - (1+k)) < 1e-14
    assert abs(np.linalg.eigvalsh(K).min() - (1-2*k)) < 1e-14


def test_fixed_reactance_benchmark_two_independent_solvers() -> None:
    frequency = 1e9
    omega = 2*np.pi*frequency
    Lbase = 10e-9
    Q0 = 25.0
    k = 0.4
    Cseries = 1 / (omega**2 * Lbase)
    caps = np.array([Cseries, Cseries, 0.1e-12])

    base_Z, base_R, base_L = branch_network(0.0, Lbase, frequency, Q0, caps)
    enh_Z, enh_R, enh_L = branch_network(
        k, Lbase / (1+k), frequency, Q0, caps)
    # Entire lossless TWO-PORT impedance must be identical.
    assert np.max(np.abs((B.T @ base_Z @ B).imag -
                         (B.T @ enh_Z @ B).imag)) < 1e-12
    assert np.max(np.abs(B.T @ enh_R @ B -
                         (B.T @ base_R @ B)/(1+k))) < 1e-12

    expected_ils = [0.4275080160456436, 0.3078084331017878]
    expected_coppers = [0.00045609542580743174, 0.00033487019812432334]
    for Zbranch, Rbranch, Lbranch, target_il, target_cu in [
        (base_Z, base_R, base_L, expected_ils[0], expected_coppers[0]),
        (enh_Z, enh_R, enh_L, expected_ils[1], expected_coppers[1]),
    ]:
        ports, currents = solve_by_two_port(Zbranch)
        voltages, nodal_currents = solve_by_independent_nodal(Zbranch)
        assert np.max(np.abs(currents - nodal_currents)) < 1e-12
        il = -10*np.log10(
            50*abs(ports[1])**2 / (1/(4*50)))
        copper = np.vdot(currents, Rbranch @ currents).real
        load_power = abs(voltages[2])**2 / 50
        # Power delivered by the Thevenin source to the 3L network.
        input_power = (voltages[0] * ((1-voltages[0])/50).conjugate()).real
        assert abs(input_power - copper - load_power) < 1e-14
        assert abs(il - target_il) < 1e-11
        assert abs(copper - target_cu) < 1e-13
        modal_q = omega*np.vdot(currents, Lbranch @ currents).real / copper
        assert abs(modal_q - (Q0*(1+k) if target_il<0.4 else Q0)) < 1e-10
