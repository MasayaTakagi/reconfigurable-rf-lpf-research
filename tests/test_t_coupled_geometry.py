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

# Independent 1D elliptic-integral vector-potential calculation.
from scipy.special import ellipk, ellipe


def circle_mutual_via_vector_potential(radius_m: float, separation_m: float,
                                      samples: int = 4096) -> float:
    theta = 2*np.pi*(np.arange(samples)+.5)/samples
    rho = np.sqrt(separation_m**2 + radius_m**2 +
                  2*separation_m*radius_m*np.cos(theta))
    m = 4*radius_m*rho/(radius_m+rho)**2
    a_phi = MU0/(np.pi*np.sqrt(m))*np.sqrt(radius_m/rho) * (
        (1-m/2)*ellipk(m) - ellipe(m))
    tangent_projection = radius_m*(radius_m+separation_m*np.cos(theta))/rho
    return np.sum(a_phi*tangent_projection)*2*np.pi/samples


def test_independent_elliptic_integral_matches_neumann():
    for distance_mm in (2.05, 2.10, 2.50, 3.00):
        distance_m = distance_mm * 1e-3
        direct = circle_mutual(1e-3, (0., 0.), (distance_m, 0.), 1024)
        independent = circle_mutual_via_vector_potential(1e-3, distance_m)
        assert abs(direct - independent) < 1e-15


def test_all_mode_non_degradation_inequality_is_exact():
    # For k12=a, k13=b, k23=-c and I1=I2+I3, all-mode
    # Q >= Q0 holds iff (a+b-c)^2 <= 4ab (plus a,b>=0).
    from scipy.linalg import eigvalsh
    for a, b, c in (
        (.0550707939, .0460477729, .0680869053),  # displaced circle
        (.01, .01, .10),  # correct signs, insufficient balance
        (.05507, .05507, .05507),  # exact uniform gain
    ):
        k_mat = np.array([[1., a, b], [a, 1., -c], [b, -c, 1.]])
        modes = eigvalsh(BRANCH_MAP.T @ k_mat @ BRANCH_MAP,
                        BRANCH_MAP.T @ BRANCH_MAP)
        psd_rule = (a + b - c)**2 <= 4*a*b
        assert psd_rule == bool(modes.min() >= 1 - 1e-12)
        assert np.linalg.eigvalsh(k_mat).min() > 0
