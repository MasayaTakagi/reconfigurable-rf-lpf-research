#!/usr/bin/env python3
"""EXP-023: verify saved RF-F002 candidates with repository branch-current MNA."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.lpf.circuit import Branch, solve
from src.lpf.evaluate import load_bands, CASES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--points', type=int, default=101)
    args = parser.parse_args()
    if args.points < 2:
        parser.error('--points must be at least 2')
    d = json.loads(args.candidate.read_text(encoding='utf-8'))
    if d['constraint_id'] != 'RF-F002':
        raise ValueError('Requires RF-F002 candidate')
    c, t = d['components'], d['topology']
    L = np.array(c['LQP02HV_nH'], dtype=float)
    if not np.all((.4 <= L) & (L <= 27)):
        raise ValueError('HV coil value out of bounds')
    K = np.eye(len(L))
    row = t['chip_physical_order']
    for a, b, k in zip(row[:-1], row[1:], c['chip_neighbor_k']):
        if abs(k) > .15 + 1e-10:
            raise ValueError('Excessive neighboring chip coupling')
        K[a, b] = K[b, a] = k
    if np.linalg.eigvalsh(K).min() <= 0:
        raise ValueError('Non SPD coupling matrix')
    fG = c['GJM01_pF']
    pC = c['PCB_PATTERN_C_pF']
    if not (.02 <= pC <= .2) or any(not(0 <= z <= 100) for z in fG):
        raise ValueError('Fixed capacitor out of bounds')
    inds = [Branch(a, b, float(v)*1e-9, 25.) for (a,b),v in zip(t['inductor_edges'], L)]
    all_caps = (
        [Branch(a,b,float(v)*1e-12,80.) for (a,b),v in zip(t['fixed_gjm_edges'],fG)]
        + [Branch(*t['pcb_pattern_capacitor_edge'],pC*1e-12,40.)])
    min_h2 = float('inf')
    min_h3 = float('inf')
    worst = float('-inf')
    critical = {}
    for case in CASES:
        tunable = c['variable_C_by_setting_pF'][case]
        if len(tunable) != 2 or any(not(0 <= v <= 1.5+1e-10) for v in tunable):
            raise ValueError('IC capacitor constraint violation')
        caps = all_caps + [Branch(a,b,float(v)*1e-12,50.) for (a,b),v in zip(t['variable_capacitor_edges'],tunable)]
        by_region = {}
        for band in load_bands():
            if band['case'] != case:
                continue
            region = band['region']
            for f in np.linspace(float(band['low_mhz']),float(band['high_mhz']),args.points):
                s = solve(float(f)*1e6, 5, t['input_node'], t['output_node'],
                          inductors=inds, capacitors=caps, coupling=K,
                          source_ohms=50, load_ohms=60-40j)
                prev = by_region.get(region)
                key = (float(s['il_db']),float(f))
                if prev is None or (key[0]>prev[0] if region in ('UL','DL') else key[0]<prev[0]):
                    by_region[region] = key
        missing = {'UL','DL','H2','H3'}-set(by_region)
        if missing:
            raise ValueError(f'Missing bands for {case}: {missing}')
        worst = max(worst,by_region['UL'][0],by_region['DL'][0])
        min_h2 = min(min_h2,by_region['H2'][0])
        min_h3 = min(min_h3,by_region['H3'][0])
        critical[case] = by_region
    print(json.dumps({'candidate':d['candidate_id'],'grid_points_per_segment':args.points,
                      'worst_IL_db':worst, 'min_H2_db':min_h2,
                      'min_H3_db':min_h3,'critical_per_case':critical},
                     ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
