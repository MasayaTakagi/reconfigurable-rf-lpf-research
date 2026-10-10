import numpy as np, json, time, os
from variants import opt, eval3
root=os.path.dirname(os.path.abspath(__file__))
records=json.load(open(root+'/refined_results.json'))
seeds=sorted((r for r in records if r.get('good')),key=lambda r:r['IL'])
out=[]
for idx in [0,1,2]:
 s=seeds[idx]
 for fixed,mi in [(True,160),(False,205)]:
  tic=time.time()
  r=opt(s['edges'],s['cp'],km=.999,seed=s,grid=__import__('dynamic').MED,maxiter=mi,fix=fixed)
  r['source']=idx;out.append(r)
  json.dump(out,open(root+'/theory_step1_results.json','w'),indent=2)
  print('TEST',idx,'fixed',fixed,'IL',r['IL'],'H2',r['H2'],'H3',r['H3'],'eig',r['psd'],'k',np.round(r['k'],4),'good',r['good'],'elapsed',round(time.time()-tic,1),flush=True)
