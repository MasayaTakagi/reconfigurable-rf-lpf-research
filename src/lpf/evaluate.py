"""Six-band segmented frequency-grid evaluation; grid results are not interval proofs."""
import csv
from pathlib import Path
import numpy as np
from .circuit import solve
CASES=('B71','B12','B28','B13+B14','B26','B8')
REGIONS=('UL','DL','H2','H3')
def load_bands(path=None):
    path=path or Path(__file__).resolve().parents[2]/'data'/'bands.csv'
    with open(path,newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    for case in CASES:
        for region in REGIONS:
            if not any(r['case']==case and r['region']==region for r in rows):
                raise ValueError('Missing %s/%s'%(case,region))
    return rows
def evaluate_settings(make_circuit,samples_per_segment=21,bands=None):
    """make_circuit(case) returns circuit.solve kwargs; only variable C may differ."""
    if samples_per_segment<2: raise ValueError('Need at least two samples')
    bands=load_bands() if bands is None else bands
    results={}
    for case in CASES:
        params=make_circuit(case);regions={}
        for region in REGIONS:
            values=[]
            for row in bands:
                if (row['case'],row['region'])!=(case,region): continue
                for f in np.linspace(float(row['low_mhz']),float(row['high_mhz']),samples_per_segment):
                    r=solve(float(f)*1e6,**params)
                    values.append((float(r['il_db']),float(f),float(r['power_residual'])))
            if not values: raise ValueError('Missing band segment')
            worst=(max if region in ('UL','DL') else min)(values,key=lambda x:x[0])
            regions[region]={'db':worst[0],'frequency_mhz':worst[1],
                             'max_abs_power_residual':max(abs(x[2]) for x in values)}
        results[case]=regions
    return {'per_case':results,
            'worst_il_db':max((results[c][r]['db'],c,r) for c in CASES for r in ('UL','DL')),
            'min_h2_db':min((results[c]['H2']['db'],c) for c in CASES),
            'min_h3_db':min((results[c]['H3']['db'],c) for c in CASES),
            'grid_only':True,'samples_per_segment':samples_per_segment}
