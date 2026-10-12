#!/usr/bin/env python3
import json,numpy as np
from pathlib import Path
from reopt import OLD,Network
D=Path(__file__).resolve().parent
ref=OLD['EXP011-01'];series=['HV','HQ','HV','HV'];records=[]
for maxL in (35,40,45,50,56):
 net=Network(ref,series,17);j=1
 net.bounds[j]=(np.log(.4),np.log(maxL));net.hi[j]=np.log(maxL)
 runs=[]
 for i in range(8):
  r=net.optimize(net.init(random=None if i==0 else 20261012+391*i),30.006,200)
  if min(r['H2'],r['H3'])>=30.005: runs.append(r)
 if not runs:print('CAP',maxL,'NO FEASIBLE');continue
 b=min(runs,key=lambda a:a['IL']);d=net.to_result(b,True)
 path=D/f'HQ_max{maxL:02d}_Q20.json';path.write_text(json.dumps(d,indent=2)+'\n')
 records.append({'max_HQ_L_nH':maxL,'worst_IL_db':d['worst_IL_db'],'H2_db':d['min_H2_db'],'H3_db':d['min_H3_db'],'actual_HQ_L_nH':d['L_nH'][1],'path':str(path)})
 print('CAP',maxL,'IL',round(d['worst_IL_db'],8),'H2',round(d['min_H2_db'],5),'H3',round(d['min_H3_db'],5),'L1',round(d['L_nH'][1],3),flush=True)
(D/'HQ_L_tradeoff.json').write_text(json.dumps(records,indent=2)+'\n')