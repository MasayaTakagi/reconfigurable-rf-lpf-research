# EXP-022 — RF-T004 area ≤6 Phase-2 topology search (2026-10-14)

> **2026-10-14 PR #43監査追記・重要：以下のIL／H2／H3数値は元研究アーカイブの報告値であり、mainの`src/lpf/circuit.py`と同一の直列ESRコンデンサ損失モデルで再計算すると一致しない。** 元の「独立MNA検証済み」は元実験の報告であり、現行基準の再検証済みと見なさない。保存定数による7,001点／各区間＋独立9×9 MNAの監査では、`C-H30p0002`はIL=0.305315738、H2=29.987752596、H3=29.984924992 dB（**30dB必須条件に不適合**）。`C-H30p02`はIL=0.305554647、H2=30.007901914、H3=30.004719741 dB（必須30dBを満たすが、元の30.02dB設定・報告値は再現不能）。差は容量損失モデルの一致や数値実装の追加調査を要する。**いずれもIL≤0.30dB未達。元の報告値は履歴として保持し、候補昇格しない。** 再現用`audit_archive.py`で監査値を確認する。元PRで用いたEXP-021はmainの別EXP-021と重複したため、本資料の保存先を**EXP-022**へ改番した。Phase 2のみ。


**回路発見経緯・探索方法・次期トポロジー仮説：** [DISCOVERY_PLAYBOOK.md](DISCOVERY_PLAYBOOK.md)（EXP-022の主要ベクトル、失敗試行、未実行仮説を区別した引継ぎ記録）。

## 再利用のための発見経緯・探索指針

- [topology_discovery_lessons.md](topology_discovery_lessons.md) — EXP-016 V→PCB-C追加→L1(3,4)から(2,4)への再接続→PCB-C(1,4)への橋絡変更という発見系列、成功/失敗した探索手法、回路グラフと精密候補、今後のP1–P6仮説と検証ゲートを記録。**検証済みと未実行仮説は区別**。
- 今後の最優先シード：`C-H30p02.json`と`C-H30p0002.json`。面積6でIL0.30548dBは30dB/0.30dB同時達成ではなく、引き続きPhase 2のbest-found。


**Status: branch-only exploratory research, NOT promoted to formal RF-F002 or main candidate index. Phase 3 remains paused.**

## Goal and constraints
User requested preservation of the EXP-017 W3-F4 performance (6-setting maximum passband IL ≤0.30dB and all UL H2/H3 minimum attenuation ≥30dB, baseline worst IL 0.298355657dB) while reducing the chip-area cost from 8⅔ to **≤6**. Six LTE settings: B71/B12/B28/B13+B14 shared/B26/B8; UL/DL and UL-H2/H3 use all separate ranges in `data/bands.csv`. Input 50Ω, fixed complex load 60−j40Ω.

RF-T004 is a **trial** over formal RF-F002. Registry trial effective SHA256 `c66302a281a1fdb88da355fc44dac1ef3b1c4e18e8ff297db9e842b219b5b0c4`, as recorded on current main in [EXP-020](../EXP-020/README.md). Formal RF-F002 effective SHA256 `f20d27e93451dcec2f823e6f7c3731c06d843050c4d2ace8b0b46ded605542e2`. Main examined at `ff4fe89ef8b1040fe8051e8cbb7a4396ce72a5a7`. Three IC variable Cs, Q50, each 0..1.5pF; GJM Q80; PCB pattern C Q40, each 0.02..0.2pF and count≤3. Chip L linear physical row, only adjacent strong k≤0.15, other k=0 nominal, SPD required. Chip area is a Pareto axis, NOT a formal hard cap.

## Observed local-search results

| Numeric checkpoint | Chip area | Worst IL dB | Min H2 dB | Min H3 dB | Status |
|---|---:|---:|---:|---:|---|
| EXP016 V, previous 4HV+3GJM baseline | 6 | 0.352300316 | ≈30.01 | ≈30.01 | prior experimental result |
| L1 parallel PCB-C `hv_v0_r0_p1` | 6 | 0.337988468 | 30.020000 | 30.020000 | independently verified |
| L1 reposition to node2–4 | 6 | 0.318916571 | 30.020000 | 30.020000 | independently verified |
| **Input bridge PCB (C-H30p02)** | **6** | **0.305720112** | **30.020000** | **30.020000** | independently verified; some rejection margin |
| **Input bridge PCB (C-H30p0002)** | **6** | **0.305481244** | **30.000200** | **30.000200** | **lowest observed IL**, very fragile |
| Input bridge PCB at 35.02dB | 6 | 0.376677758 | 35.020000 | 35.020000 | nominal35 attenuation, IL target failed |
| EXP017 W3-F4, higher-area comparison | 8⅔ | 0.298355657 | ≥30.02 | ≥30.02 | numerical target passes with higher cost |

**Conclusion: no discovered area≤6 circuit meets both IL≤0.30dB and H2/H3≥30dB** in the finite searched families. This is NOT proof of impossibility or a global performance limit. Best observed deficit to IL threshold is 0.005481244dB, and to EXP017 W3-F4 is 0.007125587dB (at different harmonic headrooms).

## New best cost-6 graph
All four chip inductors are **LQP02HV, Q25**, common physical row L0–L1–L3–L2. Inductor edges: L0(1,2), **L1(2,4)**, L2(2,5), L3(2,3). Fixed Q80 GJM edges: (1,2), (5,0), (2,3), three components. One fixed Q40 PCB-pattern capacitor bridges **(1,4)**, near 0.02557pF. Three Q50 IC tunables: (4,0), (5,0), (2,3), each 0..1.5pF; only these values vary between six settings. 4×1 + 3×(2/3) = **6 chip area units**; actual PCB/IC resource area not measured.

The C-H30p02 parameters (L nH): [3.1966263131,20.2474178040,14.6537495246,5.0822726184], physical neighboring signed k=[0.150000,0.0078526242,−0.1176114306], fixed Q80 GJM pF=[2.0886821588,0.3853462086,0.7312125162] and PCB pF=0.02557766881. C-H30p0002 is separately optimized and has different exact values; **do not reuse C-H30p02 values for the lower-IL claim**. Checkpoint files contain per-band 3×6 C vectors.

## Verification and caveats
Both best candidates independently evaluated using **7,001 points per independent UL/DL/H2/H3 frequency interval**, and 9×9 branch-current MNA checked against 5×5 reduced-nodal admittance, passivity/power budget and full K SPD. For C-H30p02: maximum voltage difference 2.22e−15 V, max power residual 4.77e−18 W, K minimum eigenvalue 0.84947; for C-H30p0002: 2.23e−15 V, 5.20e−18 W, K min 0.84945. Worst IL is at B28 DL 803MHz. Full by-setting critical frequencies available in separate conversation's `selected_verified.json`.

**Sensitivity:** at fixed tunable C, individual ±1% L or fixed-C and ±0.005 neighboring-k variations led to **21/22 violations** of H2/H3≥30dB for *both* finalists. This is a diagnostic sensitivity test, not a manufacturer-approved tolerance model; no retuning attempted. Tiny ~0.0256pF PCB C, near-limit k=0.15, finite 30dB rejection margin, and constant-Q assumptions make physical feasibility and yield unverified. SRF, Q(f), EM, layout, PCB physical area, IC routing, mathematically certified continuous-band extrema, and global optimality are NOT verified.

## Exploration and reproducibility
A local finite multi-start SLSQP/minimax study explored earlier W3-to-6 reductions, 5HV splits, LQP01 shunts with **hypothetical** 0.4..27nH range (not approved product range), PCB patterned fixed Cs, multiple simultaneous L-branch rewires, internal resonator changes, CV position changes, LQP02HQ-Q20 alternatives, and nominal 30/35dB variants. Candidate structure/parameter optimization used coarse screen→31-point refinement→7,001-point independent MNA checks. The local HQ study timed out after nine completed sets; two configured sets remained unexecuted. Some earlier `screen_*.json` were previously saved partial runs. These are **non-exhaustive finite local searches**; do not treat failures as optimality bounds.

Reproduction source scripts, original input datasets, per-trial JSON/logs and verification script are preserved in the separately delivered `EXP021_RFT004_area6_research.zip`, SHA256 `8d4f9a5ff83212532bb05b6b4348f64193127841036e44dd63060b7686b921a2`. The archive was extraction-tested: `OPENBLAS_NUM_THREADS=1 python verify_selected.py` reproduced the two checkpoints. The full zip is not committed in GitHub; the GitHub checkpoint files and this README preserve the key exact numeric results.

**Do not label this as successful cost-6 performance preservation.** Continue Phase 2, not Phase 3.
