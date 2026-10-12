import json,os
from pathlib import Path
D=Path(__file__).resolve().parent
sel={
 'EXP015-HV3C-01':'EXP011-01_HV4_ROWBEST.json',
 'EXP015-HQ3C-01':'EXP011-01_HQ1.json',
 'EXP015-HV2C-01':'EXP014-02_HV4.json',
 'EXP015-HQ2C-01':'EXP014-02_HQ1.json',
 'EXP015-HQ35-01':'HQ_max35_Q20.json',
 'EXP015-HQ40-01':'HQ_max40_Q20.json',
 'EXP015-HQ45-01':'HQ_max45_Q20.json',
 'EXP015-HQ50-01':'HQ_max50_Q20.json',
 'EXP015-HQ56-01':'HQ_max56_Q20.json'
}
manifest={'phase':'2','date':'2026-10-12','project_model':'constant_Q_series_specific_HV25_to27_HQ20_to56','scope':'six_setting_full_lpf_minimax','historical_reference_only':{'EXP011-01_Q25_all_L':'old model IL0.293821738, L1 56nH','EXP014-02_Q25_all_L':'old model IL0.343189953, L1 28.560nH'},'approved_hard_bounds':{'chip_area_cost':6,'chip_neighbor_abs_k_max':.4,'HV_L_nH':[.4,27],'HQ_L_nH':[.2,56],'HV_Q':25,'HQ_Q':20,'IC_C_pf':[0,4],'PCB_C_pf':[.02,.2],'GJM_Q':80,'IC_C_Q':80,'PCB_C_Q':40},'new_candidates':{},'large_actions_dispatched':False,'physical_SRF_EM_validated':False,'global_optimum_proven':False}
for tag,name in sel.items():
 p=D/name;d=json.loads(p.read_text());
 d['id']=tag;d['phase']='Phase 2';d['policy_revision']='2026-10-12_LQP02HV_Q25_HQ_Q20';d['part_series_per_L']={f'L{i}':s for i,s in enumerate(d['chip_series'])};d['source_original_experiment']=d['base_candidate']
 d['status']='pass_numerical_only' if d['meets_0p30_and_30db'] else 'harmonic_pass_IL_over_0p30'
 d['chip_area_cost_units']=4+(2/3)*len([e for e in d['fixed_C_edges'] if e not in [(3,1)]])
 d['LQP02_HQ_present']=any(s=='LQP02HQ' for s in d['chip_series']);d['physical_SRF_verified']=False
 d['note']='Prior GJM count inferred from original base; independent MNA in *_independent_MNA.json. Prior nominal reference values remain historical.'
 dst=D/(tag+'.json');dst.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 m={'file':dst.name,'base':d['base_candidate'],'variable_C_count':len(d['variable_C_edges']),'chip_area':d['chip_area_cost_units'],'HQ_count':sum('HQ' in s for s in d['chip_series']),'largest_L_nH':max(d['L_nH']),'worst_IL_db':d['worst_IL_db'],'min_H2_db':d['min_H2_db'],'min_H3_db':d['min_H3_db'],'meets_IL_0p30':d['worst_IL_db']<=.3,'dense_grid_samples_per_interval':d['samples_per_frequency_interval'],'independent_9x9_verified':(D/(p.stem+'_independent_MNA.json')).exists()}
 manifest['new_candidates'][tag]=m
(D/'summary.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('manifest candidates',len(sel))