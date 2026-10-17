"""Deterministic theoretical pi-coupling notch re-target tests (not EXP-NNN).

Series Ls, two symmetric shunt Lh-C series branches, mutuals (+M,-M), M_ab=0.
No parasitics, Q(f), capacitor loss, or electromagnetic extraction.
"""
import numpy as np
from scipy.optimize import brentq

F0, FZ, R0, Q0, LH = 1e9, 2e9, 50., 25., 5e-9
A = np.array([[1., -1.], [1., 0.], [0., 1.]])


def matrices(ls, c, k, f, q=Q0):
    w = 2*np.pi*f
    m = k*np.sqrt(ls*LH)
    lm = np.array([[ls, m, -m], [m, LH, 0.], [-m, 0., LH]])
    assert np.linalg.eigvalsh(lm).min() > 0
    rr = np.diag(w*np.diag(lm)/q) if np.isfinite(q) else np.zeros((3,3))
    z = rr + 1j*w*lm + np.diag([0, 1/(1j*w*c), 1/(1j*w*c)])
    return lm, rr, z


def solve(ls, c, k, f, q=Q0):
    lm, rr, z = matrices(ls, c, k, f, q)
    g = np.eye(2)/R0
    j = np.array([1/R0, 0], dtype=complex)
    v = np.linalg.solve(A.T@np.linalg.solve(z, A)+g, j)
    i = np.linalg.solve(z, A@v)
    # Distinct 5x5 voltage + branch-current formulation.
    block = np.block([[g.astype(complex), A.T], [-A, z]])
    sol = np.linalg.solve(block, np.r_[j, np.zeros(3, dtype=complex)])
    assert np.max(abs(sol[:2]-v)) < 1e-12
    assert np.max(abs(sol[2:]-i)) < 1e-12
    pd = np.vdot(i, rr@i).real
    po = abs(v[1])**2/R0
    pin = (v[0]*((1-v[0])/R0).conjugate()).real
    assert abs(pin-po-pd) < 1e-12
    il = -10*np.log10(po/(1/(4*R0)))
    qm = 2*np.pi*f*np.vdot(i, lm@i).real/pd if pd else np.nan
    return il, abs(2*v[0]-1), pd, qm


def zero_cap(ls, k):
    m = k*np.sqrt(ls*LH)
    return 1/((2*np.pi*FZ)**2*(LH-m))


def lossless_match_residual(ls, k):
    w = 2*np.pi*F0
    m = 1j*w*k*np.sqrt(ls*LH)
    zs = 1j*w*ls
    zh = 1j*(w*LH-1/(w*zero_cap(ls,k)))
    ye = 1/zh
    yo = 1/zh + 2*(zh-m)**2/(zh*(zs*zh-2*m*m))
    return (ye*yo).real-1/R0**2


def design(k):
    ls = brentq(lambda n: lossless_match_residual(n*1e-9, k),
                4., 12., xtol=1e-12)*1e-9
    c = zero_cap(ls,k)
    assert solve(ls,c,k,F0,q=np.inf)[1] < 1e-10
    return ls,c


def test_equal_notch_and_passband_match():
    expected = {
      0.: (6.588978822240173, 1.2665147955292222,
           .2444528638327971, 51.203072840301864, 25.),
      .1: (7.894057907320348, 1.4485227995815977,
           .29874340987549663, 51.470932591135835, 23.5420447232),
      -.1: (5.675550495169165, 1.144570486565727,
            .20982742247144942, 51.531961396572335, 26.4412948777)
    }
    for k,(l_nh,c_pf,pass_il,stop_il,mag_q) in expected.items():
        ls,c=design(k)
        assert abs(ls*1e9-l_nh) < 1e-8
        assert abs(c*1e12-c_pf) < 1e-8
        il, refl, copper, qm=solve(ls,c,k,F0)
        assert abs(il-pass_il) < 1e-8
        assert abs(qm-mag_q) < 1e-6
        assert abs(solve(ls,c,k,FZ)[0]-stop_il) < 1e-7


def test_capacitor_error():
    ls,c=design(-.1)
    assert abs(solve(ls,c*.99,-.1,FZ)[0]-50.779048189857) < 1e-5
    assert abs(solve(ls,c*1.01,-.1,FZ)[0]-51.003223739188) < 1e-5
