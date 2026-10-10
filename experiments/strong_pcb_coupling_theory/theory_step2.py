import os,json,time,sys,numpy as np
from variants import opt
from dynamic import SMALL,MED
root=os.path.dirname(os.path.abspath(__file__))
prev=json.load(open(root+'/theory_step1_results.json'))
seed=sorted([r for r in prev if r['good']], key=lambda d:d['IL'])[0]
record=json.load(open(root+'/topology_results.json'))
chosen=[1,0,2,7,9,12,14,15]
out=[]
for id in chosen:
 base=record[id]
 ini=base.copy();ini['k']=seed['k'];ini['x']=seed['x']
 tic=time.time()
 v=opt(base['edges'],base['cp'],seed=ini,km=.999,grid=SMALL,maxiter=105,fix=False)
 v['topology_id']=id;out.append(v)
 json.dump(out,open(root+'/theory_step2_results.json','w'),indent=2)
 print('CASE',id,'IL',round(v['IL'],6),'H2',round(v['H2'],4),'H3',round(v['H3'],4),'eig',round(v['psd'],5),'k',np.round(v['k'],3),'ok',v['good'],'t',round(time.time()-tic,1),flush=True)
