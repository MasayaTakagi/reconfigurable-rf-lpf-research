#!/usr/bin/env python3
"""Write a reproducibility summary for a bounded P4-A checkpoint artifact."""
import argparse
import json
from pathlib import Path


def summarize(checkpoint,artifact_name):
    payload=json.loads(Path(checkpoint).read_text(encoding='utf-8'))
    config=payload['run_config'];scope=config['p4_a_limits']
    expected=set(payload['expected_graph_ids'])
    completed=set(payload['completed_graph_ids'])
    failed_graphs={row['graph_id'] for row in payload.get('unit_execution_log',[])
                   if row.get('status')=='failed'}
    failed_attempts=[row for row in payload.get('interrupted_candidate_attempts',[])
                     if row.get('status')=='failed_will_replay']
    candidate_log=payload.get('candidate_execution_log',[])
    completed_candidate_keys={row['candidate_key'] for row in candidate_log
                              if row.get('status')=='completed'}
    failed_candidate_keys={row['candidate_key'] for row in failed_attempts
                           if row.get('candidate_key') not in completed_candidate_keys}
    optimizer_success=(len(completed_candidate_keys) if candidate_log
                      else int(payload.get('completed_optimizer_candidates',0)))
    optimizer_failed=len(failed_candidate_keys)
    optimizer_planned=int(payload.get('planned_optimizer_candidates',0))
    optimizer_unrun=max(0,optimizer_planned-optimizer_success-optimizer_failed)
    evaluation_count=sum(int(row.get('objective_evaluation_count',0))
                         for row in payload.get('candidate_execution_log',[]))
    evaluation_count+=sum(int(row.get('objective_evaluation_count',0))
                          for row in payload.get('interrupted_candidate_attempts',[]))
    graphs=[(row.get('graph') or [None,[]])[1] for row in payload.get('results',[])]
    all_types=sorted({edge[2] for graph in graphs for edge in graph})
    series=sorted({'LQP02HV' if value=='LQP02' else value
                   for value in all_types if value in ('LQP02','LQP02HV','LQP02HQ')})
    variable_layouts=sorted({json.dumps(row.get('variable_cap_edges',[]),separators=(',',':'))
        for result in payload.get('results',[])
        for row in result.get('optimization_runs',[])})
    optimizer_records=[row for result in payload.get('results',[])
                       for row in result.get('optimization_runs',[])]
    optimizer_records.extend(row for records in payload.get('partial_optimization_runs',{}).values()
                             for row in records)
    failed_graphs-=completed
    evaluation=config['rf_design_constraints']['evaluation']
    validations=[row.get('validation',{}) for row in payload.get('results',[])]
    return {
        'source_commit_sha':payload.get('source_commit'),
        'constraint_id':scope['constraint_id'],
        'effective_constraint_sha256':scope['effective_constraint_sha256'],
        'variable_cap_layouts':[json.loads(item) for item in variable_layouts],
        'inductor_series':series,
        'rng_seed':config['topology_search']['seed'],
        'python_version':config['numeric_environment']['python_version'],
        'numpy_version':config['numeric_environment']['numpy'],
        'scipy_version':config['numeric_environment']['scipy'],
        'blas_lapack':config['numeric_environment']['blas_lapack'],
        'thread_environment':config['numeric_environment']['thread_environment'],
        'frequency_grid_mhz':config['frequency_grid_mhz'],
        'six_setting_evaluation':{
            'cases':['B71','B12','B28','B13+B14','B26','B8'],
            'optimization_regions':['UL','DL'],
            'coarse_points_per_segment':config['optimization']['coarse_points_per_band_segment'],
            'validation_points_per_segment':config['optimization']['validation_points_per_band_segment'],
        },
        'performance_observation':{
            'mode':config['analysis_mode'],
            'minimum_h2_h3_db':evaluation['full_phase2']['minimum_h2_h3_db'],
            'nominal_h2_h3_target_db':evaluation['full_phase2']['nominal_h2_h3_target_db'],
            'observed_minimum_h2_db':min((row['min_h2_db'] for row in validations
                                          if 'min_h2_db' in row),default=None),
            'observed_minimum_h3_db':min((row['min_h3_db'] for row in validations
                                          if 'min_h3_db' in row),default=None),
            'full_phase2_pass_claimed':False,
        },
        'optimization':{
            'method':config['optimization']['method'],
            'iterations_per_call':config['optimization']['iterations'],
            'planned_optimizer_candidates':optimizer_planned,
            'successful_optimizer_candidates':optimizer_success,
            'failed_optimizer_candidates':optimizer_failed,
            'unrun_optimizer_candidates':optimizer_unrun,
            'optimizer_converged_candidates':sum(bool(row.get('converged'))
                                                 for row in optimizer_records),
            'optimizer_nonconverged_candidates':sum(not bool(row.get('converged'))
                                                    for row in optimizer_records),
            'failed_optimizer_attempts':len(failed_attempts),
            'objective_evaluations_including_interrupted_attempts':evaluation_count,
            'planned_graphs':len(expected),
            'successful_graphs':len(completed),
            'failed_graphs':len(failed_graphs),
            'unrun_graphs':len(expected-completed-failed_graphs),
            'checkpoint_status':payload['status'],
            'resume_count':payload.get('resume_count',0),
        },
        'artifact_save_destination':{
            'artifact_names':[value for value in artifact_name.split(',') if value],
            'path':'results/','retention_days':14,
        },
        'search_scope':'small bounded numerical smoke; not a topology optimum or physical implementation validation',
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--checkpoint',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--artifact-name',required=True)
    args=parser.parse_args()
    report=summarize(args.checkpoint,args.artifact_name)
    Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
