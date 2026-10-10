import os,json,csv,zipfile,glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT='/mnt/data/lpf_phase2_extension'
j=lambda p:json.load(open(f'{OUT}/{p}'))
a=j('search_results.json');ms=j('multistart.json');k=j('krelax.json');fr=j('frontier.json');fc=j('fifthC_results.json');pcb=j('pcb_shunt_results.json');b=j('first.json')
# simple comparisons
rows=[]
def add(name,group,cand):
 if not cand:return
 x=min(cand,key=lambda r:r['IL'])
 rows.append(dict(group=group,topology=name,IL_dB=x['IL'],H2min_dB=x['H2'],H3min_dB=x['H3'],passes35=bool(x['H2']>=35 and x['H3']>=35),num_candidates=len(cand)))
add('3-stage coupled LC, middle shunt','4L+4C',[d for d in a if d['feasible'] and d['topology']=='3series_middle'])
add('3-stage coupled LC, moved shunt','4L+4C',[d for d in a if d['feasible'] and d['topology'].startswith('3series_shunt')])
add('2-stage, two shunts','4L+4C',[d for d in a if d['feasible'] and d['topology'].startswith('2series')])
add('reassigned bridge capacitor','4L+4C',[d for d in a if d['feasible'] and d['topology'].startswith('bridge')])
add('extra capacitor bridge or shunt','4L+5C',[d for d in fc if d['feasible']])
add('extra PCB inductor and capacitor','4 chip L + PCB L / 5C',[d for d in pcb if d['feasible']])
with open(OUT+'/topology_comparison.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

fig,ax=plt.subplots(figsize=(8.4,4.7))
X=np.array([d['target'] for d in fr]);Y=np.array([d['IL'] for d in fr]);order=np.argsort(X)
ax.plot(X[order],Y[order],'-o',label='3-stage, 4L + 4C, nominal optimization')
ax.axhline(.30,linestyle='--',linewidth=1.2,label='0.30 dB target')
ax.axvline(35,linestyle=':',linewidth=1.2,label='35 dB nominal attenuation')
ax.set_xlabel('Minimum H2 / H3 attenuation target (dB)');ax.set_ylabel('Worst-case passband IL across 6 cases (dB)')
ax.set_title('Nominal IL – harmonic attenuation tradeoff');ax.grid(True,alpha=.25);ax.legend(loc='upper left',fontsize=9)
fig.tight_layout();fig.savefig(OUT+'/attenuation_tradeoff.png',dpi=180);plt.close(fig)

text=f'''# 可変ノッチLPF Phase 2 拡張探索報告（2026-10-10）

## 結論
6ケース共通L・結合係数、バンド別の理想連続Cの初期モデル（LQP02HV Q=25、C Q=80）で、35.05dB公称減衰と最大IL <=0.30dBを同時に達成する解は今回の探索では未発見。現行型の確認済み解は最大IL {b['IL']:.8f}dB、H2 {b['H2']:.8f}dB、H3 {b['H3']:.8f}dB。

これは大域最適値の証明ではない。見つかったすべてのILは実現可能解による**上限値**であり、真の最適値の数学的下界ではない。

## 仕様
- 6ケース：B71、B12、B28、B13＋B14（同一C設定）、B26、B8。
- 通過域：各ケースのUL＋DL、高調波阻止：各ケースULの2倍・3倍全域。
- 入力50Ω、出力60-j40Ω（周波数一定）。
- 4個チップLのQ25、4個CのQ80。4 Lの電磁結合（符号付き、行列正定値を要請）。
- 主結合2組（L1-L4、L2-L3） |k|<=0.25、副結合4組 |k|<=0.16。
- L=0.4～27nH、C=0.1～100pF。
- Phase 3（離散C化）は依然として停止。

## 現行最良設計（主結合 L1-L4 および L2-L3）
- L1,L2,L3,L4 (nH): {', '.join(f'{z:.7f}' for z in b['x'][:4])}
- k12,k13,k14,k23,k24,k34: {', '.join(f'{z:+.7f}' for z in b['x'][4:10])}
- 最小固有値 K: {b['PSD']:.7f}。
- C設定は dense_verification.csv に収録。

## 数値探索の規模と限界
- 4L+4Cトポロジー・結合ペア変更の単発最適化：{len(a)}件。結果内の35.05dB達成候補は{sum(bool(d['feasible']) for d in a)}件。
- 同一トポロジー36本の初期点擾乱（multistart.json）、成立解は{sum(bool(d['feasible']) for d in ms)}件。最良成立解 {min(d['IL'] for d in ms if d['feasible']):.8f}dB。
- 5つ目のCを許可した感度試験：{len(fc)}件、最良成立解 {min(d['IL'] for d in fc if d['feasible']):.6f}dB。5Cはいまだ設計承認されていない。
- 内層PCB-L(QL=12, L<=3nH)＋Cを追加した感度試験：{len(pcb)}件、最良成立解 {min(d['IL'] for d in pcb if d['feasible']):.6f}dB。追加部品とCの面積は別途要確認。
- 現行型の結合強度主2組を緩めたとき35.05dBの試験：0.25:{k[0]['IL']:.6f}, 0.30:{k[1]['IL']:.6f}, 0.35:{k[2]['IL']:.6f}dB。副結合は<=0.16固定。
- 公称減衰目標35.05->33dB変更時にIL {next(d['IL'] for d in fr if d['target']==33.):.6f}dB。ただしこれは今回の35dB条件を満たさない。

## 認識すべき制限
1. 数値計算はSLSQP非凸局所最適化に基づき、網羅性・大域最適値は保証しない。
2. インダクタンス行列正定値は課しているが、すべての結合係数がLQP02HVの物理的配置で同時に実現できる保証ではない。
3. 0.05MHz以下の周波数走査に加え、局所極値の数値探索をした。連続周波数の解析的・区間演算による証明ではない。
4. 物理部品Sパラメータ、SRF、PCB寄生、制御スイッチ、非線形性と量産公差は未適用。
5. 35dBは公称減衰目標であり、最終必要仕様30dBより5dB大きい。
6. 強結合ペア選択のための候補探索を行ったが、**全ての受動L/C回路グラフを網羅したわけではない**。

## 次の段階で必要な『大域最適性証明』
- 評価対象トポロジーの網羅的グラフ列挙と重複除去。
- 一定Q集中定数有理伝達関数について、各帯域で極値の厳密包含。
- 各トポロジーについて区間分枝限定法や確証付き多項式最適化で目的関数下界を求める。
- その下界と実現可能解による上界の差を予め定めたepsilon未満へ縮める。
- 現在はこの確証付き計算を完了しておらず「大域最適性は未証明」。
'''
open(OUT+'/README_ja.md','w').write(text)
archive='/mnt/data/lpf_phase2_search_20261010.zip'
paths=[x for x in glob.glob(OUT+'/*') if os.path.isfile(x) and (x.endswith(('.py','.json','.csv','.png','.md')))]
paths.append('/mnt/data/lpf_next/explore.py')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in paths:z.write(p,arcname=os.path.basename(p))
print('FILES',len(paths),archive,os.path.getsize(archive),flush=True)
print('COMPARISON',rows)
