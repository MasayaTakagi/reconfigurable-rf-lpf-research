#!/usr/bin/env python3
import json,sys,itertools,time,argparse
import numpy as np
from pathlib import Path
from reopt import OLD,Network
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--variant',choices=['HV4','HQ1'],default='HV4');p.add_argument('--starts',type=int,default=3);p.add_argument('--grid',type=int,default=15);p.add_argument('--maxiter',type=int,default=240);p.add_argument('--target',type=float,default=30.006);p.add_argument('--base',default='EXP011-01');opt=p.parse_args()
series=['HV']*4 if opt.variant=='HV4' else ['HV','HQ','HV','HV']
ref0=OLD[opt.base];rows=[p for p in itertools.permutations(range(4)) if p[0]<p[-1]]
allruns=[];starting=time.time()
for i,row in enumerate(rows):
 ref={**ref0,'row':list(row),'k':ref0['k'] if tuple(row)==tuple(ref0['row']) else [0.01, -.2, .15]}
 net=Network(ref,series,grid=opt.grid)
 for seed in range(opt.starts):
  try:
   r=net.optimize(net.init(random=None if seed==0 else 20261013+101*i+seed),opt.target,opt.maxiter)
   allruns.append({'row':list(row),'start':seed,**r})
  except Exception as e:allruns.append({'row':list(row),'start':seed,'error':str(e)})
 print('ROW',i+1,'/',len(rows),list(row),'best',min([round(z['IL'],6) for z in allruns if z.get('row')==list(row) and z.get('H2',0)>=opt.target-.0001 and z.get('H3',0)>=opt.target-.0001],default=None),flush=True)
path=HERE/f'{opt.base}_{opt.variant}_rows.json';path.write_text(json.dumps({'settings':vars(opt),'results':allruns},indent=2)+'\n')
feasible=[z for z in allruns if 'IL' in z and z['H2']>=30.005 and z['H3']>=30.005]
print('TOTAL',len(allruns),'FEAS',len(feasible),'TIME',round(time.time()-starting,2))
if feasible:
 best=min(feasible,key=lambda a:a['IL']);bref={**ref0,'row':best['row'],'k':[.01,-.2,.15]};net=Network(bref,series,grid=opt.grid)
 d=net.to_result(best,True);p=HERE/f'{opt.base}_{opt.variant}_ROWBEST.json';p.write_text(json.dumps(d,indent=2)+'\n');print('BEST DENSE',d['worst_IL_db'],d['min_H2_db'],d['min_H3_db'],'row',best['row'],'L',d['L_nH'])