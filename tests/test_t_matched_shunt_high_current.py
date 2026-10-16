"""Fixed analytical 50-ohm T matching example, not a numbered EXP."""
import numpy as np

R0=50.
Q0=25.
fp=1e9
fz=2e9
wp=2*np.pi*fp
Lseries=R0/wp
Lshunt=(R0/3)/wp
Cshunt=1/((2*np.pi*fz)**2*Lshunt)
B=np.array([[1.,0.],[0.,-1.],[1.,1.]])
A=np.array([[1.,-1.,0.],[0.,1.,-1.],[0.,1.,0.]])

def simulate(k,frequency):
    w=2*np.pi*frequency
    lh=(np.sqrt(Lshunt+k*k*Lseries)-k*np.sqrt(Lseries))**2
    mutual=k*np.sqrt(lh*Lseries)
    inductance=np.array([[Lseries,0,mutual],[0,Lseries,-mutual],
                         [mutual,-mutual,lh]])
    assert np.linalg.eigvalsh(inductance).min()>0
    assert np.max(abs(B.T@inductance@B-
               B.T@np.diag([Lseries,Lseries,Lshunt])@B))<1e-20
    resistive=np.diag(w*np.diag(inductance)/Q0)
    z=resistive+1j*w*inductance+np.diag([0,0,1/(1j*w*Cshunt)])
    G=np.diag([1/R0,0,1/R0]).astype(complex)
    J=np.array([1/R0,0,0],complex)
    voltage=np.linalg.solve(A.T@np.linalg.solve(z,A)+G,J)
    curr=np.linalg.solve(z,A@voltage)
    solution=np.linalg.solve(np.block([[G,A.T],[-A,z]]),
                   np.r_[J,np.zeros(3,complex)])
    assert np.max(abs(solution[:3]-voltage))<1e-12
    assert np.max(abs(solution[3:]-curr))<1e-12
    loss=np.vdot(curr,resistive@curr).real
    p_out=abs(voltage[2])**2/R0
    p_in=(voltage[0]*((1-voltage[0])/R0).conjugate()).real
    assert abs(p_in-p_out-loss)<1e-12
    il=-10*np.log10(p_out/(1/(4*R0)))
    qmag=w*np.vdot(curr,inductance@curr).real/loss
    return il,qmag,curr,lh

def test_matched_shunt_high_current_and_notch():
    cases=[
      (0,.4622264510624,25.,13.678822578,39.82189908308),
      (.1,.4289065326035,26.9505455261,13.732004575,42.7870701737),
      (.4,.3790252006292,30.5223662139,13.811615358,50.98607582029)
    ]
    for k,pass_il,magq,shunt_ma,notch_attenuation in cases:
        IL,Qm,I,_=simulate(k,1e9)
        assert abs(IL-pass_il)<1e-8
        assert abs(Qm-magq)<1e-8
        assert abs(abs(I[2])*1e3-shunt_ma)<1e-6
        assert abs(simulate(k,2e9)[0]-notch_attenuation)<1e-7
        assert abs(I[2])>abs(I[0])
        assert abs(I[1])>0.94*abs(I[0])
