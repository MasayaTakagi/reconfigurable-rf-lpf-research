#!/usr/bin/env python3
"""Aggregate only observed EXP011 shards; never label partial search complete."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--shards',type=int,default=4);a=p.parse_args()
shards=[]
for n in range(a.shards):
 paths=list(a.input_dir.rglob('exp011-shard-'+str(n)+'/checkpoint.json'))
 if not paths:
  paths=list(a.input_dir.rglob('shard-'+str(n)+'/checkpoint.json'))
 if not paths:shards.append({'index':n,'status':'missing'});continue
 s=json.loads(paths[0].read_text());records=s.get('records',[])
 feasible=[r for r in records if 'run' in r and min(r['run']['H2min201'],r['run']['H3min201'])>=s['settings']['rejection']-1e-7]
 shards.append({'index':n,'status':'completed' if not s.get('unfinished',True) else 'partial',
                'assigned_completed_count':len(s.get('completed',[])),
                'finished_local_runs':len(records),'failed_starts':len(s.get('failures',[])),
                'best_201_grid_feasible_il_db':min([v['run']['IL201'] for v in feasible],default=None),
                'unverified_at_dense_frequency_grid':True})
res={'shards':shards,'all_shards_complete':all(x['status']=='completed' for x in shards),'global_optimality_proven':False,
    'dense_independent_verification_still_needed_for_new_winners':True}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))