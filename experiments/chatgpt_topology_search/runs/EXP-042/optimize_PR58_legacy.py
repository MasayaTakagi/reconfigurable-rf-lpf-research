#!/usr/bin/env python3
"""EXP-042 / RF-T005; 4L C-H30p0002; Cf2 and Cv2 are PARALLEL (2,3).

Use original fixed RF-F003 S2P files from repository. Phase 2 only.
Run: OPENBLAS_NUM_THREADS=1 uv run python experiments/chatgpt_topology_search/runs/EXP-042/optimize.py --starts 3 --iterations 100 --npts 9 --verify-npts 301
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lpf.port_parasitics import get_two_port_s, s_to_abcd

CASES = ("B71", "B12", "B28", "B13+B14", "B26", "B8")
# Label 1->0,2->1,3->2,4->3,5->4
L_EDGES = [(0,1),(1,3),(1,4),(1,2)]
C_EDGES = [(0,1),(4,-1),(1,2),(0,3),(3,-1),(4,-1),(1,2)]
PAIRS = [(0,1),(1,3),(3,2)]  # L0-L1-L3-L2 physical order
Q = np.array([80.,80.,80.,40.,35.,35.,35.])
START = np.array([
    3.19434,20.28559,14.68923,5.08008,
    2.08995,.38434,.73114,.02557,
    .1,.008,-.1,
    .60832,.13887,1.5, .54990,.05834,1.30617,
    .52128,0.,1.33630, .36989,.24202,.26572,
    .26962,.19171,.13990, .19227,.07347,0.,
],dtype=float)
BOUNDS = ([(.4,27.)]*4+[(.0001,100.)]*3+[(.02,.2)]+
          [(-.1,.1)]*3+[(0.,3.)]*18)
assert len(START)==len(BOUNDS)==29

def incidence(edges):
    b=np.zeros((5,len(edges)))
    for j,(i,k) in enumerate(edges):
        b[i,j]=1.
        if k>=0: b[k,j]=-1.
    return b

BL=incidence(L_EDGES)
BC=incidence(C_EDGES)

def model(x):
    l=x[:4]
    m=np.diag(l)
    for (a,b),k in zip(PAIRS,x[8:11]):
        m[a,b]=m[b,a]=k*np.sqrt(l[a]*l[b])
    if np.linalg.eigvalsh(m).min()<=0:
        raise ValueError("non-SPD inductance")
    H=np.diag(l/25.)+1j*m
    return BL @ np.linalg.inv(H) @ BL.T,m

def load_policy():
    r=json.loads((ROOT/"data/constraints/registry.json").read_text())
    assert r["active_formal_id"]=="RF-F003"
    assert r["trial"]["RF-T005"]["state"]=="study_authorized"
    assert r["trial"]["RF-T005"]["base_constraint_id"]=="RF-F003"
    p=json.loads((ROOT/"data/constraints/formal/RF-F003.json").read_text())
    assert p["components"]["IC_VARIABLE_C"]["q"]==35
    assert p["components"]["IC_VARIABLE_C"]["max_total_variable_pf_per_branch"]==3
    assert p["coupling_limits"]["chip_chip_strong_adjacent_abs_k_max"]==.1
    assert p["external_port_parasitics"]["status"]=="mandatory_fixed_precomputed_touchstone_S2P"
    return p

class Evaluator:
    def __init__(self,policy,rows,npoints):
        self.f,self.setting,self.role,self.segment=[],[],[],[]
        for idx,row in enumerate(rows):
            fr=np.linspace(float(row["low_mhz"]),float(row["high_mhz"]),npoints)
            self.f.extend(fr)
            self.setting.extend([CASES.index(row["case"])]*len(fr))
            self.role.extend([0 if row["type"]=="pass" else
                             (1 if row["region"]=="H2" else 2)]*len(fr))
            self.segment.extend([idx]*len(fr))
        self.f=np.asarray(self.f)
        self.setting=np.asarray(self.setting)
        self.role=np.asarray(self.role)
        self.segment=np.asarray(self.segment)
        self.omega=2e6*np.pi*self.f
        # SHA verification / file cache / complex interpolation are provided
        # by the repository's canonical port_parasitics module.
        self.pre=np.asarray([s_to_abcd(get_two_port_s(policy,"input_parasitic",f*1e6,root=ROOT)) for f in self.f])
        self.post=np.asarray([s_to_abcd(get_two_port_s(policy,"output_parasitic",f*1e6,root=ROOT)) for f in self.f])
        self.last_x=None
        self.last_y=None

    def il(self,x):
        x=np.asarray(x,float)
        if self.last_x is not None and np.array_equal(x,self.last_x):
            return self.last_y
        L,m=model(x)
        n=len(self.f)
        y=(L[None,:,:]/(self.omega[:,None,None]*1e-9)).copy()
        cv=x[11:].reshape((6,3))[self.setting]
        C=np.column_stack((np.broadcast_to(x[4:8],(n,4)),cv))
        yc=self.omega[:,None]*1e-12*C/(1./Q[None,:]-1j)
        y+=np.einsum("nb,ib,jb->nij",yc,BC,BC,optimize=True)
        port=[0,2]; interior=[1,3,4]
        P=y[:,port,:][:,:,port]
        U=y[:,port,:][:,:,interior]
        V=y[:,interior,:][:,:,port]
        E=y[:,interior,:][:,:,interior]
        R=P-U@np.linalg.solve(E,V)
        y11,y12,y21,y22=R[:,0,0],R[:,0,1],R[:,1,0],R[:,1,1]
        if np.min(np.abs(y21))<1e-16:
            raise ValueError("singular LPF 2-port")
        t=np.empty((n,2,2),complex)
        t[:,0,0]=-y22/y21
        t[:,0,1]=-1./y21
        t[:,1,0]=-(y11*y22-y12*y21)/y21
        t[:,1,1]=-y11/y21
        z=self.pre@t@self.post
        load=60-40j
        den=z[:,0,0]*load+z[:,0,1]+50*(z[:,1,0]*load+z[:,1,1])
        gt=12000./np.abs(den)**2
        il=-10*np.log10(np.maximum(gt,1e-300))
        self.last_x=x.copy();self.last_y=il
        return il

    def summary(self,x):
        y=self.il(x)
        where=[];vals=[]
        for r in range(3):
            ids=np.flatnonzero(self.role==r)
            j=ids[np.argmax(y[ids]) if r==0 else np.argmin(y[ids])]
            vals.append(float(y[j]))
            where.append({"case":CASES[int(self.setting[j])],
                          "mhz":float(self.f[j]),
                          "segment":int(self.segment[j])})
        return dict(worst_il_db=vals[0],min_h2_db=vals[1],
                    min_h3_db=vals[2],where=where,
                    min_L_eigenvalue_nh=float(np.linalg.eigvalsh(model(x)[1])[0]))

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--starts",type=int,default=2)
    a.add_argument("--iterations",type=int,default=80)
    a.add_argument("--npts",type=int,default=5)
    a.add_argument("--verify-npts",type=int,default=301)
    a.add_argument("--target",type=float,choices=(30.,35.),default=30.)
    a.add_argument("--seed",type=int,default=20261016)
    a.add_argument("--output",default="results/EXP-042/rf_t005_screen.json")
    z=a.parse_args()
    rows=list(csv.DictReader((ROOT/"data/bands.csv").open()))
    if len(rows)!=28:
        raise ValueError("expected all 28 discontinuous band segments")
    p=load_policy()
    e=Evaluator(p,rows,z.npts)
    rng=np.random.default_rng(z.seed)
    results=[]
    for j in range(z.starts):
        x=START.copy()
        if j:
            x[:4]*=np.exp(rng.normal(0,.09,4))
            x[4:7]*=np.exp(rng.normal(0,.08,3))
            x[11:]+=rng.normal(0,.06,18)
            x=np.clip(x,np.array(BOUNDS)[:,0],np.array(BOUNDS)[:,1])
        x=np.r_[x,e.summary(x)["worst_il_db"]]
        def constraint(v):
            h=e.il(v[:-1])
            return np.where(e.role==0,v[-1]-h,h-z.target)
        sol=minimize(lambda v:v[-1],x,method="SLSQP",
                     bounds=BOUNDS+[(0.,10.)],
                     constraints=[{"type":"ineq","fun":constraint}],
                     options={"maxiter":z.iterations,"ftol":1e-8})
        summary=e.summary(sol.x[:-1])
        slack=float(np.min(constraint(sol.x)))
        results.append(dict(start=j,success=bool(sol.success),
                            message=str(sol.message),nfev=int(sol.nfev),
                            nit=int(sol.nit),constraint_slack_db=slack,
                            epigraph_db=float(sol.x[-1]),
                            coarse=summary,x=sol.x[:-1].tolist()))
        print("start",j,"success",sol.success,"slack",slack,
              "IL",summary["worst_il_db"],"H2",summary["min_h2_db"],
              "H3",summary["min_h3_db"],flush=True)
    best=min(results,key=lambda q:(max(0,-q["constraint_slack_db"]),
                                   q["coarse"]["worst_il_db"]))
    check=Evaluator(p,rows,z.verify_npts).summary(np.array(best["x"]))
    ok=(best["constraint_slack_db"]>=-1e-5 and
        min(check["min_h2_db"],check["min_h3_db"])>=z.target)
    output=dict(experiment_id="EXP-042",trial="RF-T005",phase=2,
                topology="C-H30p0002; Cf2 and Cv2 parallel on nodes 2-3",
                source="main data/constraints/formal/RF-F003.json; fixed S2P verified",
                npts=z.npts,verification_npts=z.verify_npts,
                target_db=z.target,seed=z.seed,
                best_start=best["start"],coarse_runs=results,
                verification=check,compliant_finite_grid=bool(ok),
                no_independent_branch_MNA_yet=True,
                no_Qf_SRF_EM_layout_validation=True)
    out=Path(z.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print("output",out,"candidate_ok",ok,flush=True)

if __name__=="__main__":
    main()
