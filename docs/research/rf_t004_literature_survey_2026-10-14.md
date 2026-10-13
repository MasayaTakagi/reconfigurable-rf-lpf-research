# RF-T004 文献調査とトポロジー探索仮説（2026-10-14）
**Status:** literature survey / analysis only; no RF-T004 optimization or independent circuit verification performed.
**Phase:** 2 only. Phase 3 is not authorized.
**Constraints:** `data/constraints/trial/RF-T004.json` (trial) + `data/constraints/formal/RF-F002.json` (base); `data/bands.csv`.
**Repository sources checked on main:** `docs/chatgpt_project_instructions.md`, `data/constraints/registry.json`, `docs/specification.md`, `docs/roadmap.md`, `experiments/chatgpt_topology_search/runs/EXP-015/README.md`. 旧制約の数値と混同しない。

## 1. 状況と重要な制約
- RF-T004はRF-F002の**IC可変Cを最大3枝**へ緩和した試験。各0〜1.5pF、Q=50、対GND・橋絡・直列を許可。他の正式RF-F002条件は変更しない。トポロジー／接続位置／固定素子／結合は6設定共通。0pF直列枝は開放。
- RF-F002の結合上限：チップ隣接強結合 |k|<=0.15、非強結合公称0、PCB–PCB |k|<=0.15、chip–PCB=0。PCB-L<=2nH/個。HV Q25 <=27nH、HQ Q20 <=56nH。LQW04 Q33。面積はハード上限でなくPareto軸。
- `data/bands.csv`：通過帯は合計617〜960MHz（設定ごとに非連続の区間を個別評価）、UL由来のH2区間の全体的な周波数レンジは1326〜1830MHz、H3は1989〜2745MHz。B13+B14のギャップを埋めて評価しない。
- 最終公称目標：6設定UL/DL最悪IL<=0.30dB、H2/H3>=35dB。必須高調波減衰30dB。
- `EXP-015`のHV3C 0.321403dB / HQ3C 0.301945dB は**RF-F001系旧容量・旧Q・旧結合の実行結果**。RF-T004の検証済み候補ではない。2026-10-13版ロードマップではRF-F002最適化・独立確認未実施。

## 2. 文献から有用な考え方（元論文の結果と本研究への外挿を分離）

| 文献 | 文献で述べられた内容 | RF-T004へ転用できる仮説 | 留意事項 |
|---|---|---|---|
| R. J. Cameron, *General Coupling Matrix Synthesis Methods for Chebyshev Filtering Functions* (1999), DOI [10.1109/22.754877](https://doi.org/10.1109/22.754877) | 任意位置の有限伝送零点を含むフィルタ関数の合成、実現可能な結合構造への変換 | まず目的となるポール/零点配置を合成し、物理的な固定LC/弱結合の回路グラフへ写像する | 主に結合共振器フィルタ理論。0.15の結合・一列配置で実装できるとは限らない |
| W. M. Fathelbab & M. B. Steer, *A Reconfigurable Bandpass Filter for RF/Microwave Multifunctional Systems* (2005), DOI [10.1109/TMTT.2005.843502](https://doi.org/10.1109/TMTT.2005.843502) | 可変容量のみで有限伝送零点の位置を動かす合成と試作原理 | 少数Cが複数のTZの位置／結合へ作用する設計を検討 | BPFのcombline実証であり、低損失LPFの直接実証でない |
| M. Ohira et al., *Coupling-Matrix-Based Systematic Design of Single-DC-Bias-Controlled Microstrip Higher Order Tunable Bandpass Filters With Constant Absolute Bandwidth and Transmission Zeros* (2019), DOI [10.1109/TMTT.2018.2873366](https://doi.org/10.1109/TMTT.2018.2873366) | 周波数依存性結合を活用して可変素子数を抑える合成 | 固定橋絡／結合を使い、3自由度で複数TZを同時制御する | 低周波・低Qの集中定数LPFへの直接適用は未検証 |
| L. Feng et al., *A design method for filter to achieve arbitrary distribution of multiple transmission zeros without cross-coupling* (2024), DOI [10.1016/j.aeue.2024.155317](https://doi.org/10.1016/j.aeue.2024.155317) | dual-modeのextracted-pole unitから複数の零点を生成 | 弱い磁気結合でも、主経路外に偶／奇モードの複数TZ発生単位を置く | 大型分布定数BPFの考え方。小型LC化・低損失は未実証 |
| C. Cai, J. Wang, G. Zhang, *Tunable microstrip lowpass filter with compact size and ultra-wide stopband* (2015), DOI [10.1049/el.2015.0829](https://doi.org/10.1049/el.2015.0829) | 可変カットオフ機構と広帯域阻止用の固定共振構造を組み合わせたLPFを試作 | **固定阻止機能 + 限定可変の整合／零点移動**へ役割分担し、すべてを可変にしない | coupled-line/radial patchの分布定数実装で、今回の部品・面積モデルとは異なる |
| S. Liu et al., *Compact lowpass filter with wide stopband using stepped impedance hairpin units* (2015), DOI [10.1049/el.2014.3673](https://doi.org/10.1049/el.2014.3673) | ネストした共振器による複数TZの生成と広域阻止 | 複数モード・複数TZを作る固定共振セルの抽象グラフ化 | マイクロストリップhairpinはそのまま許可部品ではない |
| *Internal Power Loss Formulas of Lumped-Element Matching Circuits for High-Efficiency Wireless Power Transfer* (2016), [IEICE論文](https://www.jstage.jst.go.jp/article/transele/E99.C/10/E99.C_1182/_article/-char/en) | 有限Qの集中定数整合回路について素子損失を定式化、低損失整合例を示す | 最悪ILの改善要因を各素子のR|I|²散逸で分解。整合と阻止用素子の役割分担を比較 | 本件の6設定・高調波制約を直接解いたわけではない |
| R. M. Fano, *Theoretical limitations on the broadband matching of arbitrary impedances* (1950), DOI [10.1016/0016-0032(50)90006-8](https://doi.org/10.1016/0016-0032(50)90006-8) | 受動リアクティブネットワークでの広帯域整合の理論制約 | lossless matching_onlyとfinite-Q full_lpfを分離して難しさを診断 | **60−j40Ωを周波数一定と置く負荷はグローバルに物理実現的なリアクタンスモデルではなく、Fano公式をそのまま当てて厳密下界と呼ばない** |
| Keysight, *RF, MW and Analog Filters Synthesis Using Genesys S/Filter*, [White paper](https://www.keysight.com/tw/zh/assets/7018-02793/white-papers/5990-6999.pdf) | 伝送零点を設計してから回路トポロジーへ変換する直接合成・ネットワーク変換 | ランダムグラフ生成に加え、目標TZから逆にネットワークを構築 | メーカーの技術資料。導出された回路は本件MNAで再確認必須 |

## 3. 制約から直ちに分かる数値（手計算に基づく解析例、最適化結果ではない）
- IL<=0.30dBは`Pload/Pavs >= 10^(-0.03)=0.933254`。入力反射と全素子散逸に割ける電力比の合計は最大約6.675%。
- 50Ω源→60−j40Ω負荷をネットワークなしで直結：`GT=4*50*60/|50+(60-j40)|²=0.875912`、IL約0.57539dB。整合をしながら減衰機能を作る必要がある。
- 単純なシャント直列LCの共振点`f0=1/(2π√LC)`。f0=1.4GHz、C=1.5pFならL≈8.616nH。HV Q25、IC C Q50の一定Q直列ESRモデルでは`Rtrap≈ωL/25 + 1/(ω C*50)≈4.55Ω`。50Ω–50Ω整合系の**独立した1個のシャントトラップ**近似では`|S21|=2Rtrap/(50+2Rtrap)`、減衰は約16.3dB。f0=2.1GHzではC=1.5pF、L≈3.829nH、Rtrap≈3.03Ωで約19.3dB。これは本件の全回路の達成上限ではなく、**単発高Qノッチだけで30dBを狙う危うさを示す局所近似**。
- 1個の`Cfixed+Cvar`と固定Lだけで共振位置を1.326〜1.830GHz全体に動かすには、`fmax/fmin=√((Cfixed+1.5)/Cfixed)`よりCfixed<=約1.658pF。高Q・低損失に有利な大容量を固定追加するだけでは必要なチューニング比を失う。H3の1.989〜2.745GHzも同じ周波数比。
- 実際には各設定における高調波区間の**全帯域最小減衰**を評価する。零点一点の深さだけでは成立しない。

## 4. 推奨する新トポロジー族（すべて未探索・未実証）
1. **T004-A: 固定広帯域阻止セル + 2個の可変TZ + 1個の可変整合セル。** 固定エリプティックな低次コアをまずRF-F002同等に合成し、H2用/H3用共振セルへ調整を分配。トラップの通過帯域電流を極小にする配置を目標化。
2. **T004-B: 2つの並列信号経路（電気的橋絡）で干渉零点を生成するマルチパスLPF。** 非隣接の磁気強結合を要求せず、固定C/PCBパターンCと1可変橋絡Cで迂回位相・振幅を調整。残り2Cを低損失整合と共振モードに分配。橋絡パスの通過帯域損失と高周波再透過に注意。
3. **T004-C: 弱結合デュアルモード共振セル + 3可変Cのポール／零点協調制御。** 強結合に依存せず共振器の電気的結合と内部枝を使い複数TZを生成。L行列SPDと一列物理配置を確認。
4. **T004-D: 零点からの逆合成 → 分岐回路への等価変換。** 目標は各設定のH2/H3帯域で最悪ケースを均衡化すること。Cameron/Genesysの合成を初期回路の発見手段とし、そのまま部品合法と扱わない。

## 5. 探索実験案（計画のみ）
1. 比較基準：RF-F002の2CとRF-T004の3Cを**同じ固定回路クラス・同じ有限グリッド**で最適化し、増分1枝の実価値を測る。35dB目標と30dB必須の各フロンティアを分ける。
2. 純リアクティブのlossless matching_onlyを計算し、次にfinite-Q matching_only、続いてfinite-Q full_lpf(30dB, 35dB)で制約を段階投入する。いずれも別目的の数字として識別する。
3. 6設定UL/DL/H2/H3の各不連続区間上の最大違反量をepigraph形式で最適化。初期値多様化・各bandの制御容量継承・適応的最悪周波数の追加を使う。
4. 可変Cの配置と相互モード感度：最悪ケース減衰の6設定×H2/H3について`∂A(fworst)/∂Cj`と特異値・条件数を記録。3枝でも実効ランクが低い配置は枝刈りする。
5. 連続帯域内のピークIL・底部減衰の極値を高密度メッシュおよび局所極値探索で確認。独立MNA、電力収支、L行列SPD、Qと容量範囲、直列C=0の開放と回路連結性を検証。
6. Passbandの素子別`I_rms² R_s`を集計し、部品数を増やしてでも大電流に入る低Q素子を減らす、または固定GJM01に付け替えるトポロジー比較。
7. 面積コスト、部品数、HV/HQ比、磁気結合位置、PCB/IC資源を含むパレート表。メーカーQ(f)／SRF／EM／寄生の未確認項目を明記。

## 6. 判断
まずT004-AとT004-Bに集中し、T004-C/Dを探索グラフの新規シードとして併走する。単純ノッチの1.5pF/低Q制約を打破するには、**阻止帯域の干渉による多重TZ**と**通過帯域での無駄な共振電流削減**が重要という仮説を立てる。達成見込みの定量的主張は最適化・独立解析の後でのみ行う。RF仕様の緩和やPhase 3への移行は提案・実施しない。
