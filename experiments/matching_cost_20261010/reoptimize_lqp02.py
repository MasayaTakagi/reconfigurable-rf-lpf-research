"""Matching-only LQP02 adjacent-coupling minimax reproducibility experiment.

Run: python experiments/matching_cost_20261010/reoptimize_lqp02.py
No harmonic attenuation requirement. Not a global optimum proof.
"""
import csv
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[2]
CASES=('B71','B12','B28','B13+B14','B26','B8')
BANDS={name:[] for name in CASES}
with (ROOT/'data/bands.csv').open(newline='',encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['region'] in ('UL','DL'):
            BANDS[row['case']].append((float(row['low_mhz']),float(row['high_mhz'])))
OLD={2:.131991212,3:.122209045,4:.118042384,5:.115868661,6:.114837004}
SEEDS={
2:[2.837,2.837],3:[1.2855,2.571,1.2855],
4:[.68,1.78,1.78,.68],5:[.4,1.2,1.6,1.2,.4],
6:[.4,.835,1.135,1.135,.835,.4]}
def grids(step):
    return [np.unique(np.concatenate([np.linspace(a,b,max(2,int(np.ceil((b-a)/step))+1))
                 for a,b in BANDS[name]])) for name in CASES]
def worst_il(x,n,freq):
    L=x[:n];C=x[n:].reshape(6,2)
    K=np.eye(n)
    for j in range(n-1):K[j,j+1]=K[j+1,j]=.4
    leff=np.sqrt(L)@K@np.sqrt(L)
    rnorm=L.sum()/25
    worst=-np.inf
    for idx,f in enumerate(freq):
        w=2*np.pi*f*1e-3
        ys=1/(w*(rnorm+1j*leff))
        yin=w*C[idx,0]*1e-3/(1/80-1j)
        yout=w*C[idx,1]*1e-3/(1/80-1j)
        yl=1/(60-40j)
        b=yl+yout+ys
        vin=.02/(.02+yin+ys-ys*ys/b)
        vout=ys*vin/b
        il=-10*np.log10(200*yl.real*abs(vout)**2)
        worst=max(worst,float(np.max(il)))
    return worst
def main():
    coarse=grids(3.0);dense=grids(.02)
    cseed=np.array([[0,.2],[0,.28],[0,.29],[0,.30],[.07,.3],[.3,.3]])
    for n in OLD:
        x0=np.r_[SEEDS[n],cseed.ravel()]
        r=minimize(worst_il,x0,args=(n,coarse),method='SLSQP',
                   bounds=[(.4,8)]*n+[(0,4)]*12,
                   options={'maxiter':400,'ftol':1e-11})
        measured=worst_il(r.x,n,dense)
        print(f'area={n}, old={OLD[n]:.9f}, new={measured:.9f}, delta={measured-OLD[n]:+.3g}, optimizer_success={r.success}')
        if not r.success or abs(measured-OLD[n])>2e-5:
            raise RuntimeError('Reproduction failed for area %d'%n)
if __name__=='__main__':main()
