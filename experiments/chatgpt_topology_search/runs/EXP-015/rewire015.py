#!/usr/bin/env python3
import json,numpy as np,time,itertools
from pathlib import Path
from reopt import OLD,Network
D=Path(__file__).resolve().parent
base=OLD['EXP011-01'];src=json.loads((D/'HQ_max56_Q20.json').read_text())
orig={**base,'L':src['L_nH'],'k':src['signed_neighbor_k'],'Cfix':src['fixed_C_pf'],'cv':[src['Cv_by_setting_pF'][s] for s in ['B71','B12','B28','B13+B14','B26','B8']]}
series=['HV','HQ','HV','HV'];edges=list(itertools.combinations(range(6),2));results=[];start=time.time()
for family in ['fixed_gjm','pcb_add']:
 for edge in edges:
  if family=='fixed_gjm':ref={**orig,'fixed_edges':[edge], 'pcb_edges':[], 'Cfix':[orig['Cfix'][0]]}
  else:ref={**orig,'pcb_edges':[edge],'Cfix':orig['Cfix']+[.02]}
  n=Network(ref,series,13)
  for trial in range(2):
   try:
    r=n.optimize(n.init(random=None if trial==0 else 20261020+37*int(edge[0])+trial+edge[1]*41),30.006,180)
    results.append({'family':family,'edge':edge,'trial':trial,'run':r})
   except Exception as e:results.append({'family':family,'edge':edge,'trial':trial,'error':repr(e)})
 print(family,'done',round(time.time()-start,2),flush=True)
p=D/'rewire015_results.json';p.write_text(json.dumps(results,indent=2)+'\n')
valid=[z for z in results if 'run' in z and z['run']['H2']>=30.005 and z['run']['H3']>=30.005]
print('ALL',len(results),'FEASIBLE',len(valid),'ERRORS',sum('error' in z for z in results))
for z in sorted(valid,key=lambda t:t['run']['IL'])[:10]:
 print('BEST',z['family'],z['edge'],z['trial'],round(z['run']['IL'],8),round(z['run']['H2'],5),round(z['run']['H3'],5))
for j,z in enumerate(sorted(valid,key=lambda t:t['run']['IL'])[:3]):
 edge=tuple(z['edge'])
 if z['family']=='fixed_gjm':ref={**orig,'fixed_edges':[edge], 'pcb_edges':[], 'Cfix':[orig['Cfix'][0]]}
 else:ref={**orig,'pcb_edges':[edge],'Cfix':orig['Cfix']+[.02]}
 n=Network(ref,series,13);d=n.to_result(z['run'],True)
 fname=f'HQ_rewire_top{j+1}.json';(D/fname).write_text(json.dumps(d,indent=2)+'\n')
 print('DENSE',fname,d['worst_IL_db'],d['min_H2_db'],d['min_H3_db'],d['L_nH'],flush=True)