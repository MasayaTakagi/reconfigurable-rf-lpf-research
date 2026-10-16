"""Phase-2 deterministic coil-geometry checks (not a numbered optimization run).

Three ideal coplanar single-turn circular filaments, mutually non-overlapping.
Mutual inductance uses the Neumann double-line integral.  The standalone L
approximation assumes a thin circular conductor at high frequency; this is NOT
an EM/SRF/Q(f) validation and ignores winding terminals and leads.
"""
import numpy as np
from scipy.linalg import eigh

MU0 = 4 * np.pi * 1e-7
BRANCH_MAP = np.array([[1., 0.], [0., -1.], [1., 1.]])


def circle_mutual(radius_m: float, centre1: tuple[float, float],
                  centre2: tuple[float, float], samples: int = 512) -> float:
    angle = 2 * np.pi * (np.arange(samples) + .5) / samples
    cs, sn = np.cos(angle), np.sin(angle)
    dx = centre1[0] - centre2[0] + radius_m * (cs[:, None] - cs[None, :])
    dy = centre1[1] - centre2[1] + radius_m * (sn[:, None] - sn[None, :])
    distance = np.hypot(dx, dy)
    if np.min(distance) <= 0:
        raise ValueError("Coincident filament points")
    tangents_dot = np.cos(angle[:, None] - angle[None, :])
    return MU0 / (4 * np.pi) * (2 * np.pi * radius_m / samples)**2 * np.sum(
        tangents_dot / distance
    )


def circular_self_L_thin_wire(radius_m: float, wire_radius_m: float) -> float:
    """High-frequency thin-wire self inductance; rough model only."""
    return MU0 * radius_m * (np.log(8 * radius_m / wire_radius_m) - 2)


def equal_triangle(d: float = 2.1e-3, third_x_shift: float = 0.,
                   samples: int = 512) -> tuple[np.ndarray, float, list[float]]:
    radius = 1e-3
    locations = [(0., 0.), (d, 0.),
                 (d / 2 + third_x_shift, np.sqrt(3) * d / 2)]
    l_self = circular_self_L_thin_wire(radius, 20e-6)
    k_raw = np.eye(3)
    mvals = []
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        mutual = circle_mutual(radius, locations[i], locations[j], samples)
        mvals.append(mutual)
        k_raw[i, j] = k_raw[j, i] = mutual / l_self
    # Relabel the winding connection/dot convention for branches 2 and 3.
    polarity = np.diag([1., -1., -1.])
    return polarity @ k_raw @ polarity, l_self, mvals


def test_triangle_negative_product_gauge_invariant():
    k, l_self, m = equal_triangle()
    assert all(x < 0 for x in m)
    amp = -m[0] / l_self
    assert np.allclose(np.array(m), m[0], atol=1e-15)
    assert abs(l_self * 1e9 - 5.0158222793) < 1e-8
    assert abs(amp - .0550707939064) < 1e-7
    assert np.allclose([k[0, 1], k[0, 2], k[1, 2]],
                       [amp, amp, -amp], atol=1e-13)
    assert np.linalg.eigvalsh(k).min() > 0
    gains = eigh(BRANCH_MAP.T @ k @ BRANCH_MAP,
                 BRANCH_MAP.T @ BRANCH_MAP, eigvals_only=True)
    assert np.allclose(gains, [1 + amp, 1 + amp], atol=1e-12)


def test_non_near_contact_quadrature_converged():
    centre1, centre2 = (0., 0.), (2.1e-3, 0.)
    vals = [circle_mutual(1e-3, centre1, centre2, n)
            for n in (256, 512, 1024)]
    assert np.max(np.abs(np.diff(vals))) < 1e-15


def test_one_coil_position_perturbation_keeps_gain_positive():
    k, _, _ = equal_triangle(third_x_shift=0.1e-3)
    gains = eigh(BRANCH_MAP.T @ k @ BRANCH_MAP,
                 BRANCH_MAP.T @ BRANCH_MAP, eigvals_only=True)
    assert abs(gains[0] - 1.04360810) < 1e-6
    assert abs(gains[1] - 1.06919555) < 1e-6
    assert np.linalg.eigvalsh(k).min() > 0
