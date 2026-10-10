import os
import json, numpy as np
from weak_search import opt, MED, SMALL, DENSE
from continue_search import extend
pth=os.path.join(os.path.dirname(os.path.abspath(__file__)),'results.json');prev=json.load(open(pth));seed=next(x for x in prev if x['edges']==[[1,-1],[2,3]] and x['good'])
print('SEED',seed['IL'],flush=True)
patterns=[((2,-1),2),((1,3),3),((0,2),0),((0,1),0),((1,-1),1)]
for e,chip in patterns:
 edges=seed['edges']+[list(e)];cp=seed['cp']+[chip]
 r=opt(edges,cp,initial=extend(seed,newedge=e),maxiter=170)
 prev.append(r);json.dump(prev,open(pth,'w'),indent=2)
 print('THREE',edges,cp,round(r['IL'],6),round(r['H2'],4),round(r['H3'],4),r['good'],r['time'],flush=True)
valid=sorted((r for r in prev if r['good'] and len(r['edges'])==3),key=lambda d:d['IL'])
for r in valid[:2]:
 rr=opt(r['edges'],r['cp'],initial=np.array(r['x']),grid=MED,maxiter=220)
 prev.append(rr);json.dump(prev,open(pth,'w'),indent=2)
 print('REFINE',rr['edges'],round(rr['IL'],6),round(rr['H2'],4),round(rr['H3'],4),rr['good'],rr['time'],flush=True)
print('BEST',[(round(z['IL'],6),z['edges'],z['extraC']) for z in sorted((r for r in prev if r['good']),key=lambda r:r['IL'])[:9]],flush=True)
