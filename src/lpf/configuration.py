"""Enforce that only two identified shunt IC capacitances vary by setting."""
import numpy as np
from .evaluate import CASES

def validate_six_settings(settings,variable_cap_indices):
    if set(settings)!=set(CASES): raise ValueError('Exactly six settings required')
    if len(set(variable_cap_indices))!=len(variable_cap_indices) or len(variable_cap_indices)>2:
        raise ValueError('At most two distinct variable capacitor branches')
    reference=settings[CASES[0]]
    for case in CASES:
        cfg=settings[case]
        if set(cfg)!=set(reference): raise ValueError('Configuration keys differ')
        for key in reference:
            if key in ('capacitors','inductors','coupling'): continue
            if cfg[key]!=reference[key]: raise ValueError('Non-capacitor setting change: '+key)
        if list(cfg.get('inductors',()))!=list(reference.get('inductors',())):
            raise ValueError('Inductors must be fixed')
        a=cfg.get('coupling');b=reference.get('coupling')
        if (a is None)!=(b is None) or (a is not None and not np.array_equal(np.asarray(a),np.asarray(b))):
            raise ValueError('Coupling must be fixed')
        caps=list(cfg.get('capacitors',()))
        base=list(reference.get('capacitors',()))
        if len(caps)!=len(base):raise ValueError('Capacitor topology differs')
        for i,(c,d) in enumerate(zip(caps,base)):
            if i in variable_cap_indices:
                if c.a!=d.a or c.b!=0 or d.b!=0 or c.q!=d.q or c.q!=80:
                    raise ValueError('Variable C must be fixed shunt-to-ground with Q80')
                if not (0<c.value<=4e-12):raise ValueError('Variable C outside (0,4]pF')
            elif c!=d:
                raise ValueError('Fixed C changed')
    if any(i<0 or i>=len(reference.get('capacitors',())) for i in variable_cap_indices):
        raise ValueError('Variable C index out of range')
    return True
