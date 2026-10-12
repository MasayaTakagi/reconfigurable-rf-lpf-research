#!/usr/bin/env python3
"""Replay saved EXP-015 metrics and audit topology with the common circuit model.

This script only reads historical EXP-015 candidate JSON. It writes a separate
audit record and never edits saved performance results.
"""
import json
import copy
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
RUN=ROOT/'experiments'/'chatgpt_topology_search'/'runs'/'EXP-015'
sys.path.insert(0,str(RUN))

from reopt import BANDS,CASES,OLD,Network
from lpf.circuit import Branch
from lpf.configuration import validate_six_settings
from lpf.constraint_versions import constraint_fingerprint,load_constraint
from lpf.evaluate import load_bands
from lpf.lqp02_series import select_series
from lpf.validation import validate_circuit


INDUCTOR_EDGES=((1,2),(3,4),(2,5),(2,3))
PRIORITY=('EXP015-HV3C-01','EXP015-HQ3C-01',
          'EXP015-HV2C-01','EXP015-HQ2C-01')


def _candidate_settings(saved,ref):
    series=list(saved['chip_series'])
    if len(series)!=len(saved['L_nH']) or len(series)!=4:
        raise ValueError('EXP-015 candidate has an unexpected inductor count')
    normalized=[]
    for declared,l,q in zip(series,saved['L_nH'],saved['Q_L']):
        if declared not in ('LQP02HV','LQP02HQ'):
            raise ValueError(f'Unspecified or unsupported series: {declared}')
        chosen=select_series(l,series=declared)
        if abs(float(q)-chosen['Q'])>1e-9:
            raise ValueError(f'Saved Q does not match {declared} at {l:g} nH')
        normalized.append(declared)
    fixed_edges=tuple(tuple(x) for x in ref['fixed_edges']+ref['pcb_edges'])
    variable_edges=tuple(tuple(x) for x in ref['cv_edges'])
    if tuple(map(tuple,saved['fixed_C_edges']))!=fixed_edges:
        raise ValueError('Saved fixed-C edges differ from base EXP topology')
    if tuple(map(tuple,saved['variable_C_edges']))!=variable_edges:
        raise ValueError('Saved variable-C edges differ from base EXP topology')
    if tuple(map(int,saved['physical_row']))!=tuple(saved['physical_row']) or \
            sorted(saved['physical_row'])!=list(range(4)):
        raise ValueError('Saved physical chip row is not a permutation')
    if len(saved['signed_neighbor_k'])!=3:
        raise ValueError('Saved adjacent coupling list must have three entries')

    inductors=[Branch(a,b,float(value)*1e-9,
                      select_series(value,series=declared)['Q'])
               for (a,b),value,declared in zip(INDUCTOR_EDGES,saved['L_nH'],normalized)]
    fixed_caps=[]
    fixed_values=list(saved['fixed_C_pf'])
    if len(fixed_values)!=len(fixed_edges):
        raise ValueError('Saved fixed-C value count differs from base topology')
    for i,((a,b),value) in enumerate(zip(fixed_edges,fixed_values)):
        is_pcb=i>=len(ref['fixed_edges'])
        fixed_caps.append(Branch(a,b,float(value)*1e-12,40 if is_pcb else 80))
    k=np.eye(4)
    physical_row=list(map(int,saved['physical_row']))
    for pair,value in enumerate(saved['signed_neighbor_k']):
        a,b=physical_row[pair:pair+2]
        k[a,b]=k[b,a]=float(value)

    settings={}
    for case in CASES:
        values=saved['Cv_by_setting_pF'][case]
        if len(values)!=len(variable_edges):
            raise ValueError('Saved variable-C value count differs from base topology')
        variable_caps=[Branch(a,b,float(value)*1e-12,80)
                       for (a,b),value in zip(variable_edges,values)]
        settings[case]={
            'n_nodes':5,'source_node':1,'load_node':2,
            'inductors':tuple(inductors),
            'capacitors':tuple(fixed_caps+variable_caps),'coupling':k,
        }
    return settings,normalized,k


def _old_model_replay(saved,ref,points):
    ref=copy.deepcopy(ref)
    ref['row']=list(map(int,saved['physical_row']))
    series=['HV' if label=='LQP02HV' else 'HQ' for label in saved['chip_series']]
    network=Network(ref,series,grid=3)
    cv=np.array([saved['Cv_by_setting_pF'][case] for case in CASES],float)
    x=np.r_[np.log(np.asarray(saved['L_nH'],float)),
            np.log(np.asarray(saved['fixed_C_pf'],float)),
            np.asarray(saved['signed_neighbor_k'],float),cv.ravel(),
            max(.3,float(saved['worst_IL_db']))]
    metrics=network.metrics(x,points)
    replay={
        'grid_points_per_frequency_segment':points,
        'worst_IL_db':float(metrics[:,0].max()),
        'min_H2_db':float(metrics[:,1].min()),
        'min_H3_db':float(metrics[:,2].min()),
        'per_setting_metrics':dict(zip(CASES,metrics.tolist())),
    }
    saved_per=saved['per_setting_metrics']
    replay['max_per_setting_metric_delta_db']=max(
        abs(float(replay['per_setting_metrics'][case][axis])-
            float(saved_per[case][axis]))
        for case in CASES for axis in range(3))
    replay['max_summary_metric_delta_db']=max(
        abs(replay['worst_IL_db']-float(saved['worst_IL_db'])),
        abs(replay['min_H2_db']-float(saved['min_H2_db'])),
        abs(replay['min_H3_db']-float(saved['min_H3_db'])))
    return replay


def _policy_checks(settings,saved,fixed_count,variable_edges):
    roles=tuple(None if 0 in edge else 'bridge' for edge in variable_edges)
    indices=range(fixed_count,fixed_count+len(variable_edges))
    records={}
    for constraint_id in ('RF-F001','RF-T001','RF-T002'):
        policy=load_constraint(constraint_id,allow_trial=constraint_id.startswith('RF-T'))
        try:
            validate_six_settings(settings,indices,resolved_policy=policy,
                                  variable_roles=roles)
            records[constraint_id]={'topology_compliant':True,'reason':None}
        except ValueError as exc:
            records[constraint_id]={'topology_compliant':False,
                                    'reason':str(exc)}
    minimum=min(float(saved['min_H2_db']),float(saved['min_H3_db']))
    for record in records.values():
        record['h2_h3_minimum_30db_pass']=minimum>=30.0
        record['h2_h3_nominal_35db_target_pass']=minimum>=35.0
        record['saved_worst_il_0p30db_pass']=float(saved['worst_IL_db'])<=.30
        record['topology_and_metrics_joint_30db_pass']=(
            record['topology_compliant'] and record['h2_h3_minimum_30db_pass'])
        record['topology_and_metrics_joint_35db_target_pass']=(
            record['topology_compliant'] and record['h2_h3_nominal_35db_target_pass'])
    return records


def audit_candidate(candidate_id,*,replay_points=7001):
    path=RUN/(candidate_id+'.json')
    saved=json.loads(path.read_text(encoding='utf-8'))
    ref=OLD[saved['base_candidate']]
    settings,series,k=_candidate_settings(saved,ref)
    variable_edges=tuple(tuple(x) for x in saved['variable_C_edges'])
    fixed_count=len(saved['fixed_C_edges'])
    formal=load_constraint('RF-F001')
    policy_checks=_policy_checks(settings,saved,fixed_count,variable_edges)
    spots=[]
    for case in CASES:
        for region in ('UL','DL','H2','H3'):
            segments=[row for row in BANDS
                      if row['case']==case and row['region']==region]
            all_points=np.concatenate([
                np.linspace(float(row['low_mhz']),float(row['high_mhz']),3)
                for row in segments])
            spots.extend((case,float(value)*1e6) for value in
                         (all_points[0],all_points[len(all_points)//2],all_points[-1]))
    checks=[]
    for case in CASES:
        checks.append(validate_circuit(
            settings[case],[f for c,f in spots if c==case],
            expected_inductor_edges=INDUCTOR_EDGES,
            expected_capacitor_edges=tuple(map(tuple,saved['fixed_C_edges']))+
                                       variable_edges,
            inductor_types=series,physical_order=list(map(int,saved['physical_row']))))
    combined={
        'frequency_count':sum(item['frequency_count'] for item in checks),
        'max_gain_discrepancy':max(item['max_gain_discrepancy'] for item in checks),
        'max_power_residual_w':max(item['max_power_residual_w'] for item in checks),
        'max_condition_number':max(item['max_condition_number'] for item in checks),
        'min_inductance_eigenvalue':min(item['min_inductance_eigenvalue'] for item in checks),
        'three_formulations':'main augmented MNA, independent nodal admittance, branch-current MNA',
        'connection_map_crosscheck':'PASS',
        'physical_adjacent_k_and_full_L_spd':'PASS',
    }
    replay=_old_model_replay(saved,ref,replay_points)
    tolerance=.015 if replay_points<saved['samples_per_frequency_interval'] else 1e-6
    replay['matches_saved_within_tolerance']=replay['max_summary_metric_delta_db']<=tolerance
    if not replay['matches_saved_within_tolerance']:
        raise ValueError(f"Old-model replay differs from archived metrics: {candidate_id}")
    return {
        'candidate_id':candidate_id,'source_candidate_file':str(path.relative_to(ROOT)),
        'source_commit_sha':'bc093c30400525534928addc96d50f3adacfb6f6',
        'source_candidate_sha256':__import__('hashlib').sha256(path.read_bytes()).hexdigest(),
        'saved_candidate_values_unchanged':True,
        'base_candidate':saved['base_candidate'],
        'converted_common_model':{
            'solver_nodes':5,'inductor_edges':[list(x) for x in INDUCTOR_EDGES],
            'fixed_capacitor_edges':saved['fixed_C_edges'],
            'variable_capacitor_edges':saved['variable_C_edges'],
            'variable_C_count':len(variable_edges),'inductor_series':series,
            'Q_by_series':[float(x) for x in saved['Q_L']],
            'effective_RF_F001_sha256':constraint_fingerprint(formal),
        },
        'old_model_numerical_replay':replay,
        'new_model_independent_spot_checks':combined,
        'policy_fit':policy_checks,
        'physical_implementation':{
            'series_and_inductance_range':'PASS',
            'neighbor_coupling_and_full_L_matrix':'PASS',
            'part_specific_SRF_Qf_parasitics_EM':'NOT_VERIFIED',
            'layout_and_manufacturing':'NOT_VERIFIED',
            'continuous_frequency_proof':'NOT_CLAIMED',
        },
        'performance_snapshot':{
            'worst_IL_db':saved['worst_IL_db'],
            'min_H2_db':saved['min_H2_db'],'min_H3_db':saved['min_H3_db'],
            'chip_area_cost_units':saved['chip_area_cost_units'],
            'saved_dense_grid_points_per_segment':saved['samples_per_frequency_interval'],
        },
    }


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--replay-points',type=int,default=7001)
    parser.add_argument('--output',default=str(ROOT/'docs'/'r2'/'EXP015_COMMON_MODEL_AUDIT.json'))
    args=parser.parse_args()
    if args.replay_points<2:parser.error('--replay-points must be at least 2')
    report={candidate_id:audit_candidate(candidate_id,replay_points=args.replay_points)
            for candidate_id in PRIORITY}
    payload={
        'phase':'Phase 2','source_commit_sha':'bc093c30400525534928addc96d50f3adacfb6f6',
        'active_formal_constraint_id':'RF-F001',
        'effective_RF_F001_sha256':constraint_fingerprint(load_constraint('RF-F001')),
        'scope':'historical model replay plus independent RF policy classification',
        'large_search_executed':False,
        'candidate_audits':report,
        'limitations':['Historical saved metrics remain unchanged.',
            'Three-formulation checks use independent topology metadata and selected frequency spots.',
            'Grid checks are not continuous-frequency proofs or physical implementation evidence.'],
    }
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':args.output,'candidates':{
        name:{'replay_delta_db':value['old_model_numerical_replay']['max_summary_metric_delta_db'],
              'MNA_spots':value['new_model_independent_spot_checks']['frequency_count'],
              'RF_F001':value['policy_fit']['RF-F001']['topology_compliant'],
              'RF_T001':value['policy_fit']['RF-T001']['topology_compliant'],
              'RF_T002':value['policy_fit']['RF-T002']['topology_compliant']}
        for name,value in report.items()}},indent=2))


if __name__=='__main__':main()
