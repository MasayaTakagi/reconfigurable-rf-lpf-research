import json,sys,csv,time,argparse
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mixed_study as engine
p=argparse.ArgumentParser();p.add_argument('--id',type=int,default=19);p.add_argument('--seed-index',type=int,default=0);p.add_argument('--grid',type=int,default=31);p.add_argument('--maxiter',type=int,default=300);p.add_argument('--target',type=float,default=30.001);args=p.parse_args()
P=Path(__file__).resolve().parent;r=json.load(open(P/'followup_results_compact.json'))
s=[z for z in r['trials'] if z['job']['id']==args.id and 'x' in z][args.seed_index]
engine.CHIP_ROW=s['job']['physical_row']
m=engine.Model(s['job'],list(csv.DictReader(open(P.parents[3]/'data'/'bands.csv'))))
x=np.array(s['x'])
print('initial',m.metrics(x,201)[:,0].max(),m.metrics(x,201)[:,1:].min(),flush=True)
o=engine.local_optimize(m,x,args.grid,args.target,args.maxiter)
a=m.metrics(np.array(o['x']),7001)
record={'job':s['job'],'seed_index':args.seed_index,'target':args.target,'grid':args.grid,'result':o,'dense_metrics':a.tolist(),'maxIL':float(a[:,0].max()),'H2':float(a[:,1].min()),'H3':float(a[:,2].min())}
path=P/f'pcb2_recover_{args.id}_{args.seed_index}_{args.grid}.json';path.write_text(json.dumps(record,indent=2)+'\n')
print('DONE',record['maxIL'],record['H2'],record['H3'],'secs',o['seconds'],flush=True)