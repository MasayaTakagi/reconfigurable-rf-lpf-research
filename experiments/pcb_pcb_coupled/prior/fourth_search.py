import os
import json, numpy as np
from weak_search import opt, MED, SMALL
from continue_search import extend
pth=os.path.join(os.path.dirname(os.path.abspath(__file__)),'results.json');prev=json.load(open(pth));seed=next(x for x in prev if x['edges']==[[1,-1],[2,3],[0,2]] and x['good'] and x['IL']<.32435)
print('SEED',seed['IL'],seed['H2'],seed['H3'],flush=True)
for edge,chip in [((2,-1),2),((1,3),3),((1,2),3),((0,1),0),((1,-1),1)]:
 r=opt(seed['edges']+[list(edge)],seed['cp']+[chip],initial=extend(seed,newedge=edge),maxiter=160)
 prev.append(r);json.dump(prev,open(pth,'w'),indent=2)
 print('FOUR',edge,chip,round(r['IL'],6),round(r['H2'],4),round(r['H3'],4),r['good'],r['time'],flush=True)
for cap in [(1,3),(0,3),(0,-1),(2,-1),(1,-1)]:
 r=opt(seed['edges'],seed['cp'],[cap],initial=extend(seed,newce=cap),maxiter=160)
 prev.append(r);json.dump(prev,open(pth,'w'),indent=2)
 print('CAP',cap,round(r['IL'],6),round(r['H2'],4),round(r['H3'],4),r['good'],r['time'],flush=True)
print('BEST',[(round(z['IL'],6),z['edges'],z['extraC']) for z in sorted((r for r in prev if r['good']),key=lambda r:r['IL'])[:10]],flush=True)
