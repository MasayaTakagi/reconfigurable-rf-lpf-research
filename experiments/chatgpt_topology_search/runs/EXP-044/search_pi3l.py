#!/usr/bin/env python3
"""EXP-044: three-chip-L pi network with two shunt-L resonators, RF-T005.

All numbers are complete external input S2P @ LPF @ output S2P transducer IL.
The schematic is not an ideal single shunt resonator: two inductively independent
series arms each carry a parallel capacitance, while a tapped third L has a
capacitive ground/feedback network. Supports six setting-dependent 3-pF IC Cs.
Run with --variant two_gjm_pi / one_gjm_pi / zero_gjm_pi etc. A finite-grid result is not a bound.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/"src"))
from lpf.port_parasitics import get_two_port_s, s_to_abcd

CASES=("B71","B12","B28","B13+B14","B26","B8")
L_EDGES=((0,1),(0,2),(1,3))  # Ls central series, La left shunt, Lb right shunt
PHYSICAL_ORDER=(1,0,2)       # physical linear row La-Ls-Lb; strong adjacent only
CF_EDGES=((2,-1),(3,-1),(0,1))  # fixed shunt resonator capacitors and optional series-L bypass
# each tuple: fixed capacitor types then Cv0/Cv1/Cv2 edges.
CONFIGS={
 "two_gjm_pi":(("GJM","GJM","PCB"),((2,-1),(3,-1),(0,1))),
 "one_gjm_pi":(("GJM","PCB","PCB"),((2,-1),(3,-1),(0,1))),
 "zero_gjm_pi":(("PCB","PCB","PCB"),((2,-1),(3,-1),(0,1))),
 "two_gjm_cross":(("GJM","GJM","PCB"),((2,-1),(3,-1),(2,3))),
 "one_gjm_cross":(("GJM","PCB","PCB"),((2,-1),(3,-1),(2,3))),
 "two_gjm_fork":(("GJM","GJM","PCB"),((2,-1),(0,3),(0,1))),
}

def incidence(edges):
    mat=np.zeros((4,len(edges)))
    for j,(a,b) in enumerate(edges):
        mat[a,j]=1.
        if b>=0:mat[b,j]=-1.
    return mat

BL=incidence(L_EDGES)
B_LIM=np.array([(0.4,27.)]*3,float)
B_VAR=np.array([(0.,3.)]*18,float)
B_K=np.array([(-.1,.1)]*2,float)
def bounds_and_q(config):
    types, var_edges=CONFIGS[config]
    assert len(var_edges)==3 and sum(t=="PCB" for t in types)<=3
    qb=np.array([80 if t=="GJM" else 40 for t in types]+[35]*3,float)
    cb=np.array([(0.02,100.) if t=="GJM" else (0.02,0.2) for t in types],float)
    bounds=np.vstack((B_LIM,cb,B_K,B_VAR))
    area=3.+(2./3.)*sum(t=="GJM" for t in types)
    return bounds,qb,area,incidence(CF_EDGES+var_edges)

def parse_bands():
    with (ROOT/"data/bands.csv").open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==28
    return rows

class Evaluator:
    def __init__(self,policy,config,points,inductor_q=(25.,25.,25.)):
        self.bounds,self.Q_C,self.area,self.BC=bounds_and_q(config)
        self.inductor_q=np.asarray(inductor_q,float)
        if self.inductor_q.shape!=(3,) or np.any(~np.isin(self.inductor_q,[25.,33.])):
            raise ValueError('Inductor Q series must be 25 (LQP02HV) or 33 (LQW04)')
        self.area+=2.*np.count_nonzero(self.inductor_q==33.)
        rows=parse_bands()
        freq=[];setting=[];role=[];segment=[]
        for seg,r in enumerate(rows):
            fs=np.linspace(float(r["low_mhz"]),float(r["high_mhz"]),points)
            freq.extend(fs);setting.extend([CASES.index(r["case"])]*points)
            role.extend([0 if r["type"]=="pass" else 1 if r["region"]=="H2" else 2]*points)
            segment.extend([seg]*points)
        self.f=np.array(freq,float)
        self.omega=2e6*np.pi*self.f
        self.setting=np.array(setting,int)
        self.role=np.array(role,int)
        self.segment=np.array(segment,int)
        self.pre=np.asarray([s_to_abcd(get_two_port_s(
            policy,"input_parasitic",float(f*1e6),root=ROOT)) for f in self.f])
        self.post=np.asarray([s_to_abcd(get_two_port_s(
            policy,"output_parasitic",float(f*1e6),root=ROOT)) for f in self.f])
        self.cache_x=None;self.cache_il=None
    def matrices(self,x):
        L=np.asarray(x[:3],float)
        M=np.diag(L.copy())
        for (i,j),k in zip(((0,1),(0,2)),x[6:8]):
            M[i,j]=M[j,i]=k*np.sqrt(L[i]*L[j])
        H=np.diag(L/self.inductor_q)+1j*M
        return BL@np.linalg.solve(H,BL.T),M,H
    def il(self,x):
        x=np.asarray(x,float)
        if self.cache_x is not None and np.array_equal(self.cache_x,x):
            return self.cache_il
        n=len(self.f)
        K,M,H=self.matrices(x)
        Y=np.broadcast_to(K,(n,4,4)).copy()/(self.omega[:,None,None]*1e-9)
        cv=x[8:].reshape((6,3))[self.setting]
        cap=np.column_stack((np.broadcast_to(x[3:6],(n,3)),cv))
        y=self.omega[:,None]*1e-12*cap/(1/self.Q_C[None,:]-1j)
        Y+=np.einsum("nb,ib,jb->nij",y,self.BC,self.BC,optimize=True)
        ports=[0,1];interior=[2,3]
        P=Y[:,ports,:][:,:,ports]
        U=Y[:,ports,:][:,:,interior]
        V=Y[:,interior,:][:,:,ports]
        E=Y[:,interior,:][:,:,interior]
        red=P-U @ np.linalg.solve(E,V)
        a,b,c,d=red[:,0,0],red[:,0,1],red[:,1,0],red[:,1,1]
        if np.any(np.abs(c)<1e-20): raise ValueError("Singular 2-port")
        t=np.empty((n,2,2),complex)
        t[:,0,0]=-d/c; t[:,0,1]=-1/c
        t[:,1,0]=-(a*d-b*c)/c;t[:,1,1]=-a/c
        complete=self.pre @ t @ self.post
        zl=60.-40j;zs=50.
        den=(complete[:,0,0]*zl+complete[:,0,1]+
             zs*(complete[:,1,0]*zl+complete[:,1,1]))
        gain=4*zs*zl.real/np.abs(den)**2
        result=-10*np.log10(np.maximum(gain,1e-300))
        self.cache_x=x.copy();self.cache_il=result
        return result
    def summary(self,x):
        vals=self.il(x)
        ids=[]
        for kind in range(3):
            ii=np.flatnonzero(self.role==kind)
            ids.append(int(ii[np.argmax(vals[ii]) if kind==0 else np.argmin(vals[ii])]))
        return {
            "worst_IL_db":float(vals[ids[0]]),
            "min_H2_db":float(vals[ids[1]]),
            "min_H3_db":float(vals[ids[2]]),
            "locations":[{"case":CASES[self.setting[i]],"MHz":float(self.f[i]),
                          "segment":int(self.segment[i])} for i in ids],
            "L_matrix_min_eig_nH":float(np.linalg.eigvalsh(self.matrices(x)[1])[0]),
        }

def seed_vector(ev,rng,j):
    # EXP-042 four-L bridge: approximately L0=2nH, L1_series=7nH,
    # Lshunt ~ 15nH. Different random starts avoid artificial topology bias.
    Lbase=np.array([3.8,8.5,7.0])
    x=np.empty(26,float)
    x[:3]=Lbase*np.exp(rng.normal(0,.20 if j else .01,3))
    # resonance across series 0.7-1.3 nH/pF product variation
    for q in range(3):
        low,high=ev.bounds[3+q]
        guess=[0.30,0.15,0.10][q]*np.exp(rng.normal(0,.65 if j else .02))
        x[3+q]=np.clip(guess,low,high)
    x[6:8]=np.clip(np.array([-.075,+.075])+rng.normal(0,.045 if j else .003,2),-.1,.1)
    # Put the two independent shunt series-LC resonances initially near
    # the H2 and H3 band centers; the optimizer moves transmission zeros.
    h2_ghz=np.array([1.361,1.415,1.450,1.575,1.663,1.795])
    h3_ghz=np.array([2.040,2.1225,2.176,2.360,2.4945,2.693])
    for q in range(6):
        left_target=1000./((2*np.pi*h2_ghz[q])**2*x[1])
        right_target=1000./((2*np.pi*h3_ghz[q])**2*x[2])
        var=np.array([max(0.,left_target-x[3]),
                      max(0.,right_target-x[4]),.55])
        if j: var=var*np.exp(rng.normal(0,.50,3))
        x[8+3*q:11+3*q]=np.clip(var,0,3)
    return np.clip(x,ev.bounds[:,0],ev.bounds[:,1])

def evaluate_objective(ev,x,target,weight):
    try:
        il=ev.il(x)
        p=il[ev.role==0];h=il[ev.role!=0]
        penalty=np.maximum(target-h,0.)
        # scale penalty by maximum violation, not by point count
        return float(logsumexp(6*p)/6+weight*(np.max(penalty)**2+
                         2*np.mean(penalty*penalty)))
    except (ValueError,np.linalg.LinAlgError,FloatingPointError,OverflowError):
        return 1.e7

def search(config,policy,starts=4,maxiter=140,coarse=5,dense=301,seed=20261015,inductor_q=(25.,25.,25.)):
    ev=Evaluator(policy,config,coarse,inductor_q)
    rng=np.random.default_rng(seed+sum(ord(c) for c in config))
    results=[]
    for j in range(starts):
        x0=seed_vector(ev,rng,j)
        # Stage A: unconstrained scaled cost to get the harmonic rejection
        for penalty_weight in (.12,2.5):
            try:
                warm=minimize(lambda v:evaluate_objective(ev,v,30.12,penalty_weight),
                              x0,method="L-BFGS-B",bounds=ev.bounds,
                              options={"maxiter":maxiter,"maxfun":maxiter*60,
                                       "ftol":1e-7})
                x0=np.clip(warm.x,ev.bounds[:,0],ev.bounds[:,1])
            except (ValueError,np.linalg.LinAlgError):
                pass
        warm_summary=ev.summary(x0)
        # Stage B: actual constrained minimax epigraph, not a penalty optimum
        v0=np.r_[x0,max(.01,warm_summary["worst_IL_db"])]
        def slacks(v):
            z=ev.il(v[:-1])
            return np.where(ev.role==0,v[-1]-z,z-30.02)
        try:
            sol=minimize(lambda v:v[-1],v0,method="SLSQP",
                         bounds=[tuple(q) for q in ev.bounds]+[(0.,100.)],
                         constraints={"type":"ineq","fun":slacks},
                         options={"maxiter":maxiter*2,"ftol":1e-8})
            x=sol.x[:-1]
            sm=ev.summary(x)
            min_slack=float(np.min(slacks(sol.x)))
            convergence=bool(sol.success)
            msg=str(sol.message)
            nfev=int(sol.nfev)
        except (ValueError,np.linalg.LinAlgError) as exc:
            x=x0;sm=warm_summary
            min_slack=min(sm["min_H2_db"],sm["min_H3_db"])-30.02
            convergence=False;msg="exception: "+str(exc);nfev=0
        rec={"start":j,"solver_success":convergence,"solver_message":msg,
             "solver_evaluations":nfev,"min_coarse_constraint_slack_db":min_slack,
             "coarse":sm,"vector":x.tolist()}
        results.append(rec)
        print("RUN",config,j,"area",ev.area,"IL",round(sm["worst_IL_db"],5),
              "H2",round(sm["min_H2_db"],5),"H3",round(sm["min_H3_db"],5),
              "slack",round(min_slack,5),"solved",convergence,flush=True)
    def lex(r):
        m=r["coarse"];g=max(0.,30.02-m["min_H2_db"],30.02-m["min_H3_db"])
        return (float(g>1e-5),g,m["worst_IL_db"])
    chosen=min(results,key=lex)
    fine=Evaluator(policy,config,dense,inductor_q)
    fm=fine.summary(chosen["vector"])
    print("FINAL",config,"area",ev.area,"dense",fm,"PASS30",
          fm["min_H2_db"]>=30 and fm["min_H3_db"]>=30,
          "IL0.8",fm["worst_IL_db"]<=0.8,flush=True)
    return {
       "experiment":"EXP-044","constraints":"RF-T005","phase":"Phase 2",
       "source":"Pi 3L central-series and independent two-shunt resonances (Phase 2)",
       "variant":config,"L_connections":L_EDGES,"fixed_C_connections":CF_EDGES,
       "fixed_C_types":CONFIGS[config][0],
       "variable_C_connections":CONFIGS[config][1],
       "physical_L_order":["La","Ls","Lb"],"inductor_Q":list(map(float,inductor_q)),"adjacent_k_max":.1,
       "variable_C_max_pF":3,"variable_C_Q":35,
       "chip_area_units":ev.area,
       "coarse_points_per_csv_interval":coarse,"verification_points_per_interval":dense,
       "interim_IL_target_db":.8,"formal_IL_nominal_target_db":.3,
       "harmonic_mandatory_db":30,"harmonic_nominal_target_db":35,
       "random_seed":seed,"starts":starts,
       "records":results,"selected":chosen,"verification":fm,
       "passes_30db_on_dense_grid":bool(fm["min_H2_db"]>=30 and fm["min_H3_db"]>=30),
       "passes_0p8db_on_dense_grid":bool(fm["worst_IL_db"]<=.8),
       "limitations":["finite grid","local search; no exhaustive/global infeasibility proof",
                      "independent branch-current MNA not done",
                      "Q(f), SRF, EM, tolerance and coupling physical realization not verified"]
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",required=True,choices=CONFIGS)
    ap.add_argument("--starts",type=int,default=4)
    ap.add_argument("--maxiter",type=int,default=140)
    ap.add_argument("--coarse",type=int,default=5)
    ap.add_argument("--dense",type=int,default=301)
    ap.add_argument("--seed",type=int,default=20261015)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--inductor-q",default="25,25,25",help="Ls,La,Lb intrinsic Q values 25=LQP02HV / 33=LQW04")
    a=ap.parse_args()
    from lpf.constraint_versions import load_constraint
    policy=load_constraint("RF-T005",allow_trial=True)
    reg=json.loads((ROOT/"data/constraints/registry.json").read_text())
    assert reg["active_formal_id"]=="RF-F003"
    assert policy["components"]["IC_VARIABLE_C"]["max_total_variable_pf_per_branch"]==3
    assert policy["components"]["IC_VARIABLE_C"]["max_branches_principle"]==3
    assert policy["coupling_limits"]["chip_chip_strong_adjacent_abs_k_max"]==0.1
    assert (HERE/"manifest.json").exists(), "Pre-run manifest missing"
    q=tuple(float(v) for v in a.inductor_q.split(','))
    result=search(a.variant,policy,a.starts,a.maxiter,a.coarse,a.dense,a.seed,q)
    file=a.output or ROOT/"results"/"EXP-044"/("search_"+a.variant+".json")
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("OUTPUT",file,flush=True)

if __name__=="__main__":
    main()
