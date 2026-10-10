import sys, json, time, numpy as np
sys.path[:0]=['/mnt/data/lpf_limit_study','/mnt/data/lpf_next']
from run_limits import tune
from explore import three_series, evaluation, DENSE, psd
m=json.load(open('/mnt/data/lpf_limit_study/two_pair_best_refined.json'))
print('start',m['IL'],flush=True)
s=time.time()
r=tune(np.array(m['x']),35.05,.25,stage=None if False else __import__('explore').MED,maxiter=200,otherlimit=[.16,[2,3]])
print('RESULT',round(time.time()-s,1),r['IL'],r['H2'],r['H3'],r['PSD'],r['success'],np.round(r['x'][4:10],4),flush=True)
json.dump(r,open('/mnt/data/lpf_phase2_extension/first.json','w'),indent=2)
