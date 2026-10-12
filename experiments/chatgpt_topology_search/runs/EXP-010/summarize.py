#!/usr/bin/env python3
"""Aggregate EXP010 sharded calculation artifacts without claiming missing jobs succeeded."""
import argparse,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--input-dir',required=True,type=Path)
 p.add_argument('--output',required=True,type=Path);p.add_argument('--expected-shards',type=int,default=4)
 args=p.parse_args()
 state={'expected_shards':args.expected_shards,'found_shards':0,'completed_graph_units':0,
        'assigned_graph_units':0,'incomplete_shards':[],'missing_shards':[],'failed_starts':0,
        'completed_starts':0,'converged_starts':0,'best_screening_valid_IL_db':None,
        'no_claim_of_exhaustive_global_optimization':True}
 for i in range(args.expected_shards):
  candidates=list(args.input_dir.glob(f'**/exp010-shard-{i}/checkpoint.json'))
  candidates+=list(args.input_dir.glob(f'**/shard-{i}/checkpoint.json'))
  candidates+=list(args.input_dir.glob(f'**/shard-{i}/**/checkpoint.json'))
  # Artifact merging or names may vary. Refuse to double-count duplicates.
  unique=sorted(set(p.resolve() for p in candidates))
  if len(unique)!=1:
   if not unique:state['missing_shards'].append(i)
   else:state['incomplete_shards'].append({'shard':i,'reason':'multiple_checkpoint_candidates'})
   continue
  x=json.loads(unique[0].read_text());state['found_shards']+=1
  done=len(x.get('completed_ids',[]));assigned=x.get('assigned_count',0)
  state['completed_graph_units']+=done;state['assigned_graph_units']+=assigned
  state['failed_starts']+=len(x.get('failures',[]));state['completed_starts']+=len(x.get('results',[]))
  for r in x.get('results',[]):
   m=r.get('result',{});state['converged_starts']+=bool(m.get('converged',False))
   if min(m.get('H2min201_db',-1e9),m.get('H3min201_db',-1e9))>=30:
    il=m['worstIL201_db'];current=state['best_screening_valid_IL_db']
    state['best_screening_valid_IL_db']=il if current is None else min(current,il)
  if x.get('unfinished',True) or done!=assigned:
   state['incomplete_shards'].append({'shard':i,'completed':done,'assigned':assigned})
 state['all_assigned_graphs_have_attempts']=bool(state['found_shards']==args.expected_shards
   and not state['missing_shards'] and not state['incomplete_shards'])
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(state,indent=2))
if __name__=='__main__':main()