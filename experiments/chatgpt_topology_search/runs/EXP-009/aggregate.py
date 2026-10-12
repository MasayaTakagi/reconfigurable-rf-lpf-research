#!/usr/bin/env python3
"""Audit EXP009 shard artifacts. Missing/failed/unfinished != a completed search."""
import argparse,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True)
 p.add_argument('--expected-shards',type=int,default=8);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();aggregate={'expected_shards':a.expected_shards,'shards':[],'missing_shards':[],
  'runs':0,'valid_30dB_201_grid':0,'failed_starts':0,'recorded_completed_jobs':0,
  'declared_jobs':0,'best_grid_candidate':None,'complete':False,'does_not_prove_global_optimum':True}
 hashes=set();all_completed=set();all_expected=0
 for si in range(a.expected_shards):
  pth=a.input_dir/f'exp009-shard-{si}'/'checkpoint.json'
  if not pth.exists():
   aggregate['missing_shards'].append(si)
   aggregate['shards'].append({'index':si,'status':'missing_artifact'});continue
  data=json.loads(pth.read_text())
  hashes.add(data['fingerprint']);seen=data['completed_ids'];runs=data['runs'];failed=data['failures']
  assigned=data['assigned_count'];all_expected+=assigned
  all_completed.update(seen)
  aggregate['shards'].append({'index':si,'completed':len(seen),'assigned':assigned,
    'failed_starts':len(failed),'runs':len(runs),'unfinished':data['unfinished']})
  aggregate['runs']+=len(runs);aggregate['failed_starts']+=len(failed)
  aggregate['valid_30dB_201_grid']+=sum(bool(r['valid_30dB_on_verification_grid']) for r in runs)
  good=[r for r in runs if r['valid_30dB_on_verification_grid']]
  for r in good:
   c={'shard':si,'job_id':r['job']['id'],'job':r['job']['name'],
      'max_IL_db':r['max_IL_db'],'H2_db':r['min_H2_db'],'H3_db':r['min_H3_db'],
      'independent_MNA_verified':r['independent_MNA_verified']}
   if aggregate['best_grid_candidate'] is None or c['max_IL_db']<aggregate['best_grid_candidate']['max_IL_db']:
    aggregate['best_grid_candidate']=c
 aggregate['declared_jobs']=all_expected
 aggregate['recorded_completed_jobs']=len(all_completed)
 aggregate['same_fingerprint']=len(hashes)<=1
 aggregate['complete']=(not aggregate['missing_shards'] and aggregate['same_fingerprint']
   and aggregate['failed_starts']==0 and aggregate['recorded_completed_jobs']==all_expected
   and not any(r.get('unfinished',True) for r in aggregate['shards']))
 aggregate['validation_note']='Search outputs at 201-point per-interval grid are screening only; dense 7001-point independent MNA verification required before ranking a new reference.'
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(aggregate,indent=2)+'\n')
 print(json.dumps(aggregate,indent=2))
if __name__=='__main__':main()