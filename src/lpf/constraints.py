"""Canonical policy access and lightweight topology constraints."""
import json
from pathlib import Path
POLICY_PATH = Path(__file__).resolve().parents[2] / 'data' / 'design_constraints.json'

def load_policy():
    return json.loads(POLICY_PATH.read_text(encoding='utf-8'))

def chip_area(n_lqp02=0,n_lqp01=0,n_lqw04=0,n_gjm01=0):
    return (3*n_lqp02+2*n_lqp01+9*n_lqw04+2*n_gjm01)/3

def check_counts(n_lqp02=0,n_lqp01=0,n_lqw04=0,n_gjm01=0,n_pcb=0,n_var=0):
    p=load_policy()
    return chip_area(n_lqp02,n_lqp01,n_lqw04,n_gjm01)<=p['area_budget']['hard_cap'] and n_pcb<=p['components']['PCB_L']['max_count_principle'] and n_var<=p['components']['IC_VARIABLE_C']['max_branches_principle']
