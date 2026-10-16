"""Deterministic Phase-2 T-shunt LC checks; not a formal EXP run."""
import numpy as np

Q = 25.
B = np.array([[1., 0.], [0., -1.], [1., 1.]])
A = np.array([[1., -1., 0.], [0., 1., -1.], [0., 1., 0.]])


def solve(freq, k, parallel=False):
    w = 2*np.pi*freq
    lseries, ltarget = 1e-9, 10e-9
    lsh = (lseries if parallel else
           (np.sqrt(ltarget + k*k*lseries) - k*np.sqrt(lseries))**2)
    m = k*np.sqrt(lseries*lsh)
    L = np.array([[lseries, 0, m], [0, lseries, -m],
                  [m, -m, lsh]])
    assert np.linalg.eigvalsh(L).min() > 0
    R = np.diag(w*np.diag(L)/Q)
    Z = R + 1j*w*L
    if parallel:
        C = 1/((2*np.pi*1e9)**2*lsh)
        ZZ = np.zeros((4, 4), complex)
        ZZ[:3,:3] = Z
        ZZ[3,3] = 1/(1j*w*C)
        incidence = np.vstack((A, [0.,1.,0.]))
        Z = ZZ
    else:
        C = 1/((2*np.pi*2e9)**2*ltarget)
        Z[2,2] += 1/(1j*w*C)
        assert max(abs((B.T@L@B - B.T@np.diag([lseries,lseries,ltarget])@B)).flat)<1e-20
        incidence = A
    G = np.diag([1/50.,0.,1/50.]).astype(complex)
    J = np.array([1/50.,0.,0.], complex)
    V = np.linalg.solve(incidence.T@np.linalg.solve(Z,incidence)+G,J)
    I = np.linalg.solve(Z, incidence@V)
    VI = np.linalg.solve(np.block([[G,incidence.T],[-incidence,Z]]),
                         np.r_[J,np.zeros(len(I),complex)])
    assert max(abs(V-VI[:3])) < 1e-12
    assert max(abs(I-VI[3:])) < 1e-12
    diss = np.vdot(I[:3],R@I[:3]).real
    pload=abs(V[2])**2/50.
    pin=(V[0]*((1-V[0])/50.).conjugate()).real
    assert abs(pin-diss-pload)<1e-12
    IL=-10*np.log10(pload/0.005)
    modal_q=w*np.vdot(I[:3],L@I[:3]).real/diss
    return IL,modal_q,I,diss


def test_series_shunt_lc_large_stopband_current():
    vals=[
      (1e9,0,.059673223819,25.,2.6680424011),
      (1e9,.1,.058715000693,25.4110563830,2.6683649274),
      (1e9,.4,.056185229725,26.5645208017,2.6692080271),
      (2e9,0,16.12799721786,25.,16.1692262152),
      (2e9,.1,16.59213959122,26.4479978609,16.3284416024),
      (2e9,.4,18.00592169060,31.2450887852,16.7637393136)
    ]
    for f,k,il,q,shunt_mA in vals:
        actual,mag,branches,_=solve(f,k)
        assert abs(actual-il)<1e-8
        assert abs(mag-q)<1e-8
        assert abs(abs(branches[2])*1000-shunt_mA)<1e-7
    _,_,I,_=solve(2e9,.4)
    assert abs(I[2]/I[1])>13


def test_parallel_tank_circulating_current_has_no_Q_gain_at_self_resonance():
    expected=[
        (0,1.3940923082,68.593738,1.2324647681),
        (.1,1.1855224685,63.8896136,1.0755652155),
        (.4,.7909114287,52.54993885,.7433208632)
    ]
    for k,il,shunt_mA,loss_mW in expected:
        val,q,branches,loss=solve(1e9,k,parallel=True)
        assert abs(val-il)<1e-8
        assert abs(q-25)<1e-8
        assert abs(abs(branches[2])*1000-shunt_mA)<1e-5
        assert abs(loss*1000-loss_mW)<1e-7
        assert abs(branches[2])>10*abs(branches[2]+branches[3])
