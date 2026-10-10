"""P2/P3/P4 pilot: parallel coupled-chip-inductor paths, matching-only.

Not exhaustive. Six-setting worst UL/DL IL. Prints dense-grid results.
"""
import csv
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[2]
CASES=('B71','B12','B28','B13+B14','B26','B8')
BANDS={c:[] for c in CASES}
with (ROOT/'data/bands.csv').open(newline='') as f:
    for row in csv.DictReader(f):
        if row['region'] in ('UL','DL'):
            BANDS[row['case']].append((float(row['low_mhz']),float(row['high_mhz'])))
def grid(step):
    return [np.unique(np.concatenate([np.linspace(a,b,max(2,int(np.ceil((b-a)/step))+1))
        for a,b in BANDS[c]])) for c in CASES]
def il(x,n,freq):
    L=x[:n]
    C=x[n:].reshape(6,2)
    K=np.eye(n)
    for i in range(n-1):K[i,i+1]=K[i+1,i]=.4
    M=K*np.sqrt(np.outer(L,L))
    worst=-1e9
    yl=1/(60-40j)
    for b,f in enumerate(freq):
        w=2*np.pi*f*1e-3
        # Branch admittance between terminals for parallel coupled inductors:
        # Y_series = ones^T Z_L^-1 ones, Z_L=w*(diag(L/Q)+j*M)
        z=np.diag(L/25)+1j*M
        ybase=np.ones(n)@np.linalg.solve(z,np.ones(n))
        ys=ybase/w
        yin=w*C[b,0]*1e-3/(1/80-1j)
        yout=w*C[b,1]*1e-3/(1/80-1j)
        bb=yl+yout+ys
        vin=.02/(.02+yin+ys-ys*ys/bb)
        vout=ys*vin/bb
        gain=200*yl.real*abs(vout)**2
        worst=max(worst,float(np.max(-10*np.log10(gain))))
    return worst
def main():
    coarse=grid(5.0)
    dense=grid(.02)
    caps=np.array([[0,.2],[0,.27],[0,.28],[0,.29],[.05,.30],[.25,.29]])
    for n in (2,4,6):
        starts=[np.r_[np.full(n,4.0),caps.ravel()],
                np.r_[np.full(n,6.0),caps.ravel()]]
        results=[]
        for x0 in starts:
            res=minimize(il,x0,args=(n,coarse),method='SLSQP',
                bounds=[(.4,8)]*n+[(0,4)]*12,
                options={'maxiter':220,'ftol':1e-9})
            results.append((il(res.x,n,dense),res))
        best,res=min(results,key=lambda p:p[0])
        print('parallel_chips=%d area=%d dense_IL=%.9f optimizer_success=%s L_nH=%s'%
              (n,n,best,res.success,np.round(res.x[:n],5).tolist()))
if __name__=='__main__':main()
