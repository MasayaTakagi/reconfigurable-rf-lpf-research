import json,sys,time,csv,argparse
import numpy as np
from pathlib import Path
P=Path('/mnt/data/exp010');R=Path('/mnt/data/_smoke_root/experiments/chatgpt_topology_search/runs/EXP-010');sys.path.insert(0,str(R))
from mixed_study import Model,jobs,BANDS,local_optimize,reference_vector
m=Model(jobs('baseline')[0],list(csv.DictReader(BANDS.open())))
records=json.load(open(P/'multistart_test.json'))['records']
refs={r['index']:r['result'] for r in records}
checks=[]
for ix in (1,6,2,0,3):
 x=np.array(refs[ix]['x']);
 for n,target,iter in ((31,30.001,250),(61,30.002,250)):
  t=time.monotonic();s=local_optimize(m,x,n,target,iter)
  x=np.array(s['x']); a=m.metrics(x,7001)
  v={'source_index':ix,'grid':n,'target':target,'metrics':a.tolist(),'maxIL':float(a[:,0].max()),'H2':float(a[:,1].min()),'H3':float(a[:,2].min()),'x':s['x'],'elapsed_seconds':float(time.monotonic()-t),'converged':s['converged'],'evaluations':s['model_evaluations']}
  checks.append(v);(P/'recovered_v2.json').write_text(json.dumps(checks,indent=2)+'\n')
  print(ix,n,'IL',round(v['maxIL'],9),'H2',round(v['H2'],7),'H3',round(v['H3'],7),'eval',s['model_evaluations'],'secs',round(v['elapsed_seconds'],1),flush=True)