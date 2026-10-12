"""EXP-010 selected exploratory topology variants, Q25/80/40, area cost6."""
import csv,sys,json,os,time,hashlib,argparse
import numpy as np
from pathlib import Path
sys.path.insert(0,'/mnt/data/_smoke_root/experiments/chatgpt_topology_search/runs/EXP-010')
import mixed_study as engine
P=Path('/mnt/data/exp010');BANDS=list(csv.DictReader(open('/mnt/data/_smoke_root/data/bands.csv')))
REF=json.load(open(P/'EXP010-02.json'))
BASE=engine.jobs('baseline')[0]
SEEDS=[20261012,20261013]
rows=[(1,2,3,0),(1,3,2,0),(2,1,3,0),(3,1,2,0),(1,3,0,2),(1,0,2,3)]
var_edges=[(0,1),(0,2),(0,3),(0,4),(1,3),(1,4),(2,3),(2,4),(2,-1),(0,-1),(3,-1)]
pcb2_edges=[(1,-1),(0,4),(2,4),(0,1),(4,-1),(0,3)]
variants=[]
for e in var_edges:
 if e==BASE['variable_edges'][2]:continue
 v=dict(BASE);v.update({'family':'variable_C3_edge','variable_edges':BASE['variable_edges'][:2]+(e,),'name':str(e),'physical_row':(1,2,3,0)});variants.append(v)
for row in rows[1:]:
 v=dict(BASE);v.update({'family':'physical_row','physical_row':row,'name':str(row)});variants.append(v)
for e in pcb2_edges:
 v=dict(BASE);v.update({'family':'second_pcb','pcb_edges':BASE['pcb_edges']+(e,),'name':str(e),'physical_row':(1,2,3,0)});variants.append(v)
for n,v in enumerate(variants):v['id']=n
p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=5);p.add_argument('--iterations',type=int,default=160);p.add_argument('--points',type=int,default=13);p.add_argument('--atten',type=float,default=30.003);p.add_argument('--filename',default='followup_results.json');args=p.parse_args()
file=P/args.filename
state={'experiment':'EXP-010','method':'SLSQP epigraph minimax local','Q_L':25,'Q_GJM':80,'Q_IC_C':80,'Q_PCB':40,'count_topology_variations':len(variants),'max_IL_reference':.29990744384685586,'attempts':[],'complete':False}
if file.exists():state=json.load(open(file))
for v in variants[args.start:args.start+args.count]:
 if any(a['job']['id']==v['id'] for a in state['attempts']):continue
 engine.CHIP_ROW=v['physical_row']
 mod=engine.Model(v,BANDS)
 start=engine.reference_vector(REF,mod.npcb)
 for k in range(2):
  seed=20261012+v['id']*100+k;rng=np.random.default_rng(seed)
  x=start.copy()
  if k:
   x[:4]+=rng.normal(0,.08,4);x[4:7+mod.npcb]+=rng.normal(0,.1,3+mod.npcb)
   x[7+mod.npcb:10+mod.npcb]+=rng.normal(0,.03,3)
   x[10+mod.npcb:-1]+=rng.normal(0,.065,18)
  bounds=np.array(mod.bounds());x=np.clip(x,bounds[:,0]+1e-12,bounds[:,1]-1e-12)
  try:
   res=engine.local_optimize(mod,x,args.points,args.atten,args.iterations)
   m=mod.metrics(np.array(res['x']),201)
   rec={'seed':seed,'iteration_max':args.iterations,'result':res,'verified201':{'IL':float(m[:,0].max()),'H2':float(m[:,1].min()),'H3':float(m[:,2].min()),'all_6_metrics':m.tolist()},'global_minimum_proven':False}
  except Exception as ex:rec={'seed':seed,'error':repr(ex)}
  state['attempts'].append({'job':v,'run':rec})
  file.write_text(json.dumps(state,indent=2)+'\n')
  if 'verified201' in rec: print('job',v['id'],v['family'],v['name'],'start',k,'IL',round(rec['verified201']['IL'],7),'reject',round(min(rec['verified201']['H2'],rec['verified201']['H3']),4),flush=True)
  else:print('job',v['id'],'ERROR',rec['error'],flush=True)
state['complete']=len({z['job']['id'] for z in state['attempts']})==len(variants)
file.write_text(json.dumps(state,indent=2)+'\n')