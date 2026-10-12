"""Independent nodal-admittance gain check, with local branch stamping.

This implementation does NOT import the main MNA incidence matrix builder.
It eliminates coupled inductor currents using the impedance block and stamps
nodal admittances explicitly, distinct from circuit.solve's augmented MNA.
"""
import numpy as np


def solve_gain(f_hz, n_nodes, source_node, load_node, inductors=(), capacitors=(),
               coupling=None, source_voltage=1.0, source_ohms=50.0,
               load_ohms=60-40j):
    if (not np.isfinite(f_hz) or f_hz <= 0 or
            type(n_nodes) is not int or n_nodes < 1 or
            not 1 <= source_node <= n_nodes or not 1 <= load_node <= n_nodes or
            source_ohms <= 0 or load_ohms.real <= 0):
        raise ValueError("Invalid circuit inputs")
    w = 2 * np.pi * f_hz
    inductors = tuple(inductors)
    capacitors = tuple(capacitors)
    n = len(inductors)
    values = np.array([x.value for x in inductors], float)
    qs = np.array([x.q for x in inductors], float)
    if (np.any(~np.isfinite(values)) or np.any(~np.isfinite(qs))
            or np.any(values <= 0) or np.any(qs <= 0)):
        raise ValueError("Invalid inductors")
    k = np.eye(n) if coupling is None else np.asarray(coupling, float)
    if (k.shape != (n, n) or not np.all(np.isfinite(k)) or
            not np.allclose(k, k.T, atol=1e-12) or
            not np.allclose(np.diag(k), 1, atol=1e-12)):
        raise ValueError("Invalid magnetic coupling matrix")
    if n:
        mutual = np.sqrt(values[:, None] * values[None, :]) * k
        if np.linalg.eigvalsh(mutual).min() <= 0:
            raise ValueError("Non-positive-definite inductance matrix")
        impedance = np.diag(w * values / qs) + 1j * w * mutual
        admittance = np.linalg.solve(impedance, np.eye(n, dtype=complex))
    else:
        admittance = np.zeros((0, 0), dtype=complex)
    y = np.zeros((n_nodes, n_nodes), dtype=complex)
    # Coupled inductor admittance stamps without using circuit.incidence().
    pairs = []
    for coil in inductors:
        if (type(coil.a) is not int or type(coil.b) is not int or
                coil.a == coil.b or min(coil.a, coil.b) < 0 or
                max(coil.a, coil.b) > n_nodes):
            raise ValueError("Invalid inductor nodes")
        pairs.append(((coil.a - 1, 1) if coil.a else None,
                      (coil.b - 1, -1) if coil.b else None))
    for i, (a, b) in enumerate(pairs):
        for j, (c, d) in enumerate(pairs):
            gij = admittance[i, j]
            for left in (a, b):
                if left is None:
                    continue
                for right in (c, d):
                    if right is None:
                        continue
                    y[left[0], right[0]] += left[1] * right[1] * gij
    for capacitor in capacitors:
        if (type(capacitor.a) is not int or type(capacitor.b) is not int or
                capacitor.a == capacitor.b or min(capacitor.a, capacitor.b) < 0 or
                max(capacitor.a, capacitor.b) > n_nodes or
                not np.isfinite(capacitor.value) or capacitor.value < 0 or
                not np.isfinite(capacitor.q) or capacitor.q <= 0):
            raise ValueError("Invalid capacitor")
        adm = w * capacitor.value / (1 / capacitor.q - 1j)
        if capacitor.a:
            a = capacitor.a - 1
            y[a, a] += adm
        if capacitor.b:
            b = capacitor.b - 1
            y[b, b] += adm
        if capacitor.a and capacitor.b:
            a, b = capacitor.a - 1, capacitor.b - 1
            y[a, b] -= adm
            y[b, a] -= adm
    y[source_node - 1, source_node - 1] += 1 / source_ohms
    y[load_node - 1, load_node - 1] += 1 / load_ohms
    current = np.zeros(n_nodes, dtype=complex)
    current[source_node - 1] = source_voltage / source_ohms
    v = np.linalg.solve(y, current)
    p_load = abs(v[load_node - 1]) ** 2 * (1 / load_ohms).real
    p_available = abs(source_voltage) ** 2 / (4 * source_ohms)
    return float(p_load / p_available)
