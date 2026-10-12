# Phase 2 制約群ごとの現行LPF候補と損失分解（2026-10-12）

## 条件差による代表比較

| 制約群 | 候補 | 最悪IL dB | H2 dB | H3 dB | 反射 dB | L dB | GJM dB | IC可変C dB | PCB-C dB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 基準: 2GND-C、35dB、cost≤6 | LPF-007 | 0.51317 | 35.06997 | 35.07000 | 0.12834 | 0.30009 | 0.01089 | 0.07385 | 0.00000 |
| 2GND-C＋PCBパターンC、35dB、cost≤6 | LPF-009 | 0.51606 | 35.09927 | 35.10570 | 0.04396 | 0.35596 | 0.02577 | 0.08961 | 0.00076 |
| 2GND-C、35dB、cost≤7（実験） | A7-04 | 0.50695 | 35.00199 | 35.00200 | 0.04134 | 0.35147 | 0.02729 | 0.08685 | 0.00000 |
| 3C (1非GND)、35dB、cost≤6（実験） | C6-35 | 0.44449 | 35.00041 | 35.00500 | 0.00253 | 0.33783 | 0.02159 | 0.08253 | 0.00000 |
| 3C (1非GND)、30dB、cost≤6、PCB-Cなし | EXP009-02 | 0.30723 | 30.01176 | 30.01200 | 0.00500 | 0.23815 | 0.01754 | 0.04653 | 0.00000 |
| 3C (1非GND)、30dB、cost≤6、PCB-C×1 | EXP010-04 | 0.30000 | 30.00691 | 30.00699 | 0.00947 | 0.23250 | 0.03483 | 0.02310 | 0.00010 |
| 同条件・最小IL | EXP010-05 | 0.29989 | 30.00096 | 30.00097 | 0.00986 | 0.23224 | 0.03481 | 0.02288 | 0.00010 |

## 回路の狙いと読み取り方

- **正式群（LPF-007/008/009）**: 2個のGND接続可変CでL1とL2のシャント・トラップを独立調整し、L0/L3を含む伝送経路のILを抑えながらH2/H3=35dBを満たす。入力反射およびLの散逸が大きな項。
- **面積拡張群（A7-03/04）**: L0並列に固定Cf3を加え、固定回路設計の自由度を増やす代わりにチップコストが正式上限6を超える。
- **3可変C群（C6）**: Cv2をL3並列に配置し反共振を切り替える。35dB解C6-35と30dB解C6-02は部品値も異なり、IL差を減衰条件単独の因果効果と見なさない。
- **EXP009**: GJM Cf3をL1並列へ移すことによりL1側共振器を再設計。L1≤12,15,27nHの比較は同じQ25一定の数値探索範囲による感度。
- **EXP010**: 固定GJM Cf3をL0並列へ戻し、L1並列をQ40の0.02pF近辺のPCB固定Cへ置換。3可変C・30dB群で初めて0.30dBを下回る局所解を得た。L1は50nH付近となり、Q(f)/SRF/実基板の妥当性は未検証。

## 現状の損失ボトルネック

**EXP010-05**の最悪点（B8 DL 960 MHz）では、反射約0.00986dB、L全体約0.23224dB、GJM約0.03481dB、IC可変C約0.02288dB、PCBパターン固定C約0.00010dB。
L3とL0の損失配分が相対的に大きい。したがって、L3/L0の高周波電流、磁気結合分配、共振器のエネルギー滞留を減らすことが次の探索仮説。ただし同定数のままLやCを除いた差分ではなく、あくまで電力配分に基づく仮説である。

## 損失分解の式と基準

電源のテブナン電圧1 Vrms/抵抗50Ωを採用し、利用可能電力 `Pavs=1²/(4×50)=0.005W`。出力負荷は60−j40Ωで負荷への実電力 `Pload=|Vout|² Re(1/Zload)`。
`Pavs = P_reflection + ΣP_inductor + ΣP_GJM + ΣP_IC_C + ΣP_PCB_C + Pload`。相互結合の虚数項はエネルギーの保存・交換にのみ寄与し、直接散逸には加算しない。
`IL = -10 log10(Pload/Pavs) = L_reflection + L_dissipation`、ここで `L_reflection=-10log10((Pavs-P_reflection)/Pavs)`、`L_dissipation=-10log10(Pload/(Pavs-P_reflection))`。素子ごとのdB会計値は `L_dissipation×(P_component/ΣP_dissipation)`。
この和がちょうどILに一致することを全17候補で検査。別のRF候補同士の「反射dB」「散逸dB」を単純に引き算して特定部品変更の原因と解釈することはできない。

## データ・再現

各候補の回路定数は元の候補JSONに保持。結果は各フォルダの `LOSS_REVIEW.md` と `LOSS_BREAKDOWN.json`。Python計算エンジンは [`scripts/loss_decomposition.py`](../scripts/loss_decomposition.py)。
各区間7,001点と最悪点の独立9×9MNAによる数値検証であり、連続周波数の厳密保証、EM検証、強結合実現、温度・ばらつき耐性は含まない。**Phase 2のみ**。

## 項目ごとの保存先

- [candidates/LOSS_REVIEW.md](../candidates/LOSS_REVIEW.md)：LPF-007, LPF-008, LPF-009
- [experiments/chatgpt_topology_search/runs/EXP-005/LOSS_REVIEW.md](../experiments/chatgpt_topology_search/runs/EXP-005/LOSS_REVIEW.md)：A7-03
- [experiments/chatgpt_topology_search/runs/EXP-006/LOSS_REVIEW.md](../experiments/chatgpt_topology_search/runs/EXP-006/LOSS_REVIEW.md)：A7-04
- [experiments/chatgpt_topology_search/runs/EXP-008/LOSS_REVIEW.md](../experiments/chatgpt_topology_search/runs/EXP-008/LOSS_REVIEW.md)：C6-01, C6-02, C6-35
- [experiments/chatgpt_topology_search/runs/EXP-009/LOSS_REVIEW.md](../experiments/chatgpt_topology_search/runs/EXP-009/LOSS_REVIEW.md)：EXP009-L12, EXP009-L15, EXP009-01, EXP009-02
- [experiments/chatgpt_topology_search/runs/EXP-010/LOSS_REVIEW.md](../experiments/chatgpt_topology_search/runs/EXP-010/LOSS_REVIEW.md)：EXP010-01, EXP010-02, EXP010-03, EXP010-04, EXP010-05