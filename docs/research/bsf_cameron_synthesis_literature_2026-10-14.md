# BSF合成理論・Cameron結合行列法 文献調査（2026-10-14）
**区分:** Phase 2、文献・理論レビュー（新規回路最適化・数値性能評価は未実行）。**制約変更なし:** 正式 RF-F002、比較試験 RF-T004。Phase 3 未承認。

## 0. 背景と参照正本
- GitHub mainの `docs/chatgpt_project_instructions.md`、`data/constraints/registry.json`、`data/constraints/formal/RF-F002.json`、`data/constraints/trial/RF-T004.json`、`data/bands.csv`、`docs/research/exp021_dual_bandstop_review_2026-10-14.md`を参照。
- 入力50Ω、負荷60−j40Ω一定。6設定の各UL/DL全域でILを評価し、H2/H3各個別帯域全域で30dB必須・35dB公称、IL≤0.30dB目標。
- RF-F002は2独立可変C枝、RF-T004は最大3枝（いずれも0–1.5 pF・Q50、接続位置可）。固定回路共通・設定ごとに容量のみ変更。チップL物理一列・強結合は隣接のみ|k|≤0.15、非隣接公称0、L行列SPD。面積ハード上限なし、パレート軸。
- EXP-021は固定/可変C橋絡・内部共振ノードを持つ二重BSF的応答。プロジェクトのRF-T004/35dB最良基準の一つはEXP-020、面積13⅔、IL0.297114dB（公称一定Q、独立MNA）。

## 1. 主要な合成手法
| 系列 | 原理 | 本研究の適性と制約 |
| --- | --- | --- |
| 古典的挿入損失法（Butterworth/Chebyshev/elliptic） | LPFプロトタイプからBSF周波数変換。代表的に s_LP = B s / (s² + ω₀²)、B=ω₂−ω₁、ω₀²=ω₁ω₂ | 単一BSFの基準に適するが、二重BSF＋低損失整合への直接対応は限定的 |
| 直接多項式合成 | S21=P/E、S11=F/Eを指定し、零点を設計 | 零点と帯域最悪値を直接扱えるが、実装可能LCは別途合成 |
| Cameron一般化Chebyshev + 結合行列 | 指定有限TZの多項式→ canonical N+2 matrix→ 等価トポロジー変換 | 中核理論。正規化行列Mと物理磁気結合kは同一でない |
| Cameron系BSF直接合成 | S21/S11の多項式交換またはCul-de-Sac形；単一／二重BSF | H2/H3の二重阻止帯に最も直接的 |
| 結合行列逆行列変換 | 特定規格化/可逆条件のBPF MからBSF M^{-1} | 低域・高域の等リップルRL制御。ただしMの特異性・巨大な結合に注意 |
| Extracted-pole / trisection / nonresonating-node | 零点を含む共振セクションを抽出して局所化 | LC共振セルへの対応が見通しやすく、トポロジー制約下で候補 |
| 二経路位相打ち消し | BPFの組合せ・結合経路の干渉をBSFへ | EXP-021の橋絡経路とのアナロジー。磁気結合を極小化できる可能性 |
| 可変行列要素によるチューナブル合成 | M(C)の零点感度、モード依存同調 | 6設定を一つの固定回路で切り替える研究に対応。ただし容量枝数制約厳守 |

## 2. 優先文献（内容は公開済み要旨・出版者目次・公開原著PDFに限定して確認）
1. **R. J. Cameron (1999)**, *General Coupling Matrix Synthesis Methods for Chebyshev Filtering Functions*, IEEE TMTT 47(4), 433–442. DOI https://doi.org/10.1109/22.754877 。非対称TZ含む一般化Chebyshev多項式→canonical結合行列→非最適化の行列トポロジー再構成。
2. **R. J. Cameron (2003)**, *Advanced Coupling Matrix Synthesis Techniques for Microwave Filters*, IEEE TMTT 51(1), 1–10. DOI https://doi.org/10.1109/TMTT.2002.806937 。N+2 transversal行列、Source–Load直接結合、foldedへの再構成、fully canonicalケース。
3. **R. J. Cameron, M. Yu, Y. Wang (2005)**, *Direct-Coupled Microwave Filters with Single and Dual Stopbands*, IEEE TMTT 53(11), 3288–3297. DOI https://doi.org/10.1109/TMTT.2005.859032 。公開抄録で確認：3構成(a)一般直接結合BSF、(b)負・対角結合不要なCul-de-Sac型、(c)Cul-de-Sacの二重BSFへの拡張。単一4次BSF実測、二重BSFの設計例。**最優先文献**。本文の具体的LC化は今回未検証。
4. **E. Corrales, P. de Paco, O. Menéndez (2011)**, *Direct Coupling Matrix Synthesis of Bandstop Filters*, PIER Letters 27, 85–91. DOI https://doi.org/10.2528/PIERL11091512 。出版社公開PDFでは (i) BPFの反射/透過多項式を交換するBSF（阻止帯の等リップル減衰）、(ii) 正規化BPF行列の逆行列 M_BSF=M_BPF^{-1} により周波数反転（阻止帯両側の等リップル反射）を区別。式は論文で採用する正規化・可逆行列の文脈に限る。https://www.jpier.org/pierl/pier.php?paper=11091512
5. **Cameron, Kudsia, Mansour (2018)**, *Microwave Filters for Communication Systems*, 第10章 **Synthesis and Application of Extracted Pole and Trisection Elements**，とくに§10.2 **Synthesis of Bandstop Filters Using the Extracted Pole Technique**、§10.2.1 Direct-Coupled Bandstop Filters。 DOI https://doi.org/10.1002/9781119292371.ch10 。公開目次/章要旨を確認。
6. **S. Saeedi, J. Lee, H.H. Sigmarsson (2015)**, *Novel Coupling Matrix Synthesis for Single-Layer Substrate-Integrated Evanescent-Mode Cavity Tunable Bandstop Filter Design*, IEEE TMTT 63(12), 3929–3938. DOI https://doi.org/10.1109/TMTT.2015.2490075 。2つのBPFの位相打ち消しでBSFを合成、Source-to-Load直接結合を不要にできる。可変BSFの設計・実例。異なる物理技術なのでLPF用チップLCへ直接の移植は未確認。
7. **S. Amari, U. Rosenberg, R. Wu (2006)**, *In-line Pseudoelliptic Band-Reject Filters with Nonresonating Nodes and/or Phase Shifts*, IEEE TMTT 54(1), 428–436. DOI https://doi.org/10.1109/TMTT.2005.860494 。NRNによる反射零点制御、位相要素が本研究に適するかは別。
8. **F. Xiao (2016)**, *Direct Synthesis Techniques for General Chebyshev Filters: Lowpass, Highpass, and Bandstop Cases*, IJCTA 44(3), 584–601. DOI https://doi.org/10.1002/cta.2095 。BSF領域の直接多項式合成。
9. **H. Cheng et al. (2026)**, *Design of a Tunable Dual-Band Bandstop Filter Based on Dual-Mode Resonators*, Microwave and Optical Technology Letters 68(8), e70705. DOI https://doi.org/10.1002/mop.70705 。異なる二つの共振モードを容量調整する2026年の検証例。分布定数技術、L/C値や性能の転用を主張しない。

## 3. Cameron法を本件へ使う際の理論上の境界
- 一般化ChebyshevのP/F/Eの構築、losslessでの|S11|²+|S21|²=1、N+2行列への合成は**理想回路応答の段階**。
- 一般化Chebyshev行列の非零要素は正規化した共振モード間結合を示す。**チップL間磁気結合kとは同一ではない**。理想的な等価行列操作・回転で得たグラフが合法LCで実現可能とは限らない。
- 50Ω/50Ωの単純なRL/equiripple想定を負荷60−j40Ωへ直接代入しない。本件はGT=Pload/Pavsを用い、低域の整合と通過帯素子損失を**最終MNA**で評価する。一定複素負荷の広周波数実現性は別。
- BSF内の完全透過零点はlossless極限の議論。有限Qで実軸の厳密なTZや無限減衰を必須とはしない。
- 単一設定に独立合成されたM_iを単純に6個並べても6設定共通の固定L/C・物理結合と可変2/3容量だけで実現できる証拠にならない。**M(C1,C2[,C3])が6つの目標応答を覆う低次元可変行列族**を合成する必要がある。
- H2/H3の比f3/f2≃1.5はモード比設計の先験条件。B13+B14の不連続UL/DL/H2/H3区間は独立区間のまま評価する。阻止帯より上方の第3透過域は仕様上要求されておらず、両側通過帯の等リップルRLへの自由度投入は不必要な可能性。
- 応答レベル設計→正規化結合行列→許可LC回路と対応付け→有限Q/6設定同時最適化→独立MNA・電力収支・SPD・SRF/実装性。この区別を維持。

## 4. 次に検討する理論検証（未実行）
1. Cameron 2005 Cul-de-Sac dual-stopbandの公開可能な本文を精読し、最小モード数・零点/反射零点構造を抽出。
2. Corrales 2011の2方式（多項式交換とM逆行列）について正規化4次系の小規模自前再現（lossless；両側RLと帯内減衰を比較）。論文式を一般の実LC行列へ無条件適用しない。
3. Saeedi 2015の干渉系統とCameron Cul-de-Sacの2系統について、物理要素へ写像可能な最小結合グラフを列挙。無効な強結合符号/遠隔配置は除外。
4. H2/H3の零点/反射零点と6設定容量感度 J_ij=∂log(f_zi)/∂C_j の有効ランクを検証。各設定の阻止帯端を含む有限Q最悪性能を確認。
5. RF-F002（2C）とRF-T004（最大3C）の **別ID/別Pareto系列**。EXP-021を同面積参照、EXP-020（35dB/面積13⅔/0.297114dB）をプロジェクト先行基準とする。いずれも新規最適化・優位性は**未実行／未証明**。

## 5. 仮結論
優先順位：(1) Cameron/Yu/Wang 2005 Cul-de-Sac二重BSF、(2) Cameron 1999/2003多項式→結合行列、(3) Saeedi 2015位相干渉型、(4) Corrales 2011逆行列/多項式交換による単一BSF基準、(5) Extracted-Pole/NRNによる物理LCへの変換。
これは**文献に基づく理論候補の優先順位であり、回路の実装可能性やIL改善を実証したものではない**。
