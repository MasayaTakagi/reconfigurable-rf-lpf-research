#!/usr/bin/env python3
"""Lightweight, stdlib-only audit of the historical evidence package.

Confirms file integrity, band table arithmetic, required cases and saved numerical
candidate metadata. This is NOT an EM, interval, or full circuit-model verification.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ('B71','B12','B28','B13+B14','B26','B8')

def readcsv(name):
    with (ROOT/name).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def audit(detail=False):
    issues=[]
    bands=readcsv('data/bands.csv')
    for c in CASES:
        rows=[x for x in bands if x['case']==c]
        ul=[x for x in rows if x['region']=='UL']
        dl=[x for x in rows if x['region']=='DL']
        h2=[x for x in rows if x['region']=='H2']
        h3=[x for x in rows if x['region']=='H3']
        if not ul or not dl or len(h2)!=len(ul) or len(h3)!=len(ul):
            issues.append(f'{c}: incomplete pass/stop regions')
        for mult, stop in ((2,h2),(3,h3)):
            for u,s in zip(ul,stop):
                if float(s['low_mhz'])!=mult*float(u['low_mhz']) or float(s['high_mhz'])!=mult*float(u['high_mhz']):
                    issues.append(f'{c}: harmonic range error {mult}')
    evidence=readcsv('data/evidence_register.csv')
    if len(evidence)<4:issues.append('Not enough registered evidence records')
    for r in evidence:
        if not (ROOT/r['evidence']).is_file(): issues.append('Missing evidence: '+r['evidence'])
        if not r['globally_proven'].lower()=='no':issues.append('Unsupported optimality flag '+r['id'])
        if float(r['min_h2_db'])<30 or float(r['min_h3_db'])<30:issues.append('Noncompliant saved candidate '+r['id'])
    independent=json.loads((ROOT/'data/independent_validation/independently_verified.json').read_text())
    items=[x for x in independent if abs(x['k']-.98)<1e-9]
    if len(items)!=1:issues.append('Missing unique independent k=.98 case')
    else:
        x=items[0]
        if abs(x['maxIL']-.2952083694863997)>0.00001:issues.append('Independent best-case IL mismatch')
        if x['H2']<35.0 or x['H3']<35.0:issues.append('Independent strong-coupling H2/H3 below 35dB')
    perband=readcsv('data/independent_validation/stack_band_verified.csv')
    p=[x for x in perband if abs(float(x['k'])-.98)<1e-9]
    if {x['band'].replace('B13+14','B13+B14') for x in p}!=set(CASES):issues.append('Missing 6-band independent validation')
    manifest=readcsv('data/archive_manifest.csv')
    for r in manifest:
        f=ROOT/r['relative_path']
        if not f.is_file():issues.append('Missing source archive '+str(f));continue
        digest=hashlib.sha256(f.read_bytes()).hexdigest()
        if digest!=r['sha256']:issues.append('SHA256 mismatch '+str(f))
    if detail:
        print('Bands:',len(CASES),'segments:',len(bands),'evidence:',len(evidence),'archives:',len(manifest))
        if items:print('Independent k=.98 case:', {k:items[0][k] for k in ['maxIL','H2','H3','qeff','leff']})
    return issues

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--detail',action='store_true')
    args=parser.parse_args()
    errors=audit(args.detail)
    if errors:
        print('FAILED:',*errors,sep='\n- ')
        sys.exit(1)
    print('PASS: table arithmetic, 6-band coverage, evidence paths, SHA256 archive integrity, independent validation metadata.')
