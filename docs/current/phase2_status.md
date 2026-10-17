# Phase 2：現行ステータス（2026-10-17）

> **基準：** mainコミット `bdb39904379637aeca5cf56ec3096e9e1b15f62a` までに記録された研究。閲覧用要約であり数値正本ではない。以後の変更は [roadmap](../roadmap.md) と [制約レジストリ](../../data/constraints/registry.json) を確認する。
>
> **フェーズ：Phase 2継続。Phase 3への移行は所有者の明示的承認まで禁止。**

## 現行条件と評価方法

| 区分 | 内容 |
|---|---|
| 正式条件 | **RF-F003**。正本は [registry.json](../../data/constraints/registry.json) の active ID が指定する [RF-F003.json](../../data/constraints/formal/RF-F003.json) |
| 試験条件 | **RF-T005**。RF-F003基準で可変Cの最大独立枝数だけ2→3に緩和。正式成果と混同禁止 |
| 信号経路 | 入力の固定S2P → LPF本体 → 出力の固定S2P、外部50Ω源・60−j40Ω負荷 |
| 周波数 | [6設定・不連続28区間](../../data/bands.csv)、外部端子間のIL／UL H2・H3を評価 |
| 可変C | RF-F003最大2枝、RF-T005最大3枝。各0～3pF、Q35 |
| 結合上限 | chip隣接強結合・PCB-Lペアとも`|k|≤0.10`。他の物理条件は正式JSON |
| 必須／公称 | **H2/H3≥30dBが必須**、35dBが公称目標。最悪IL目標≤0.30dB。chip面積はILとの二目的比較軸 |
| S2P出典 | 固定された入力／出力モデル由来のS2Pであり、実測ではない |

[正式仕様の概要](../specification.md) ／ [運用指示正本](../chatgpt_project_instructions.md)

## 2026-10-17に保存されたbest-foundパレート

| 条件 | 区分 | 非支配候補 | 代表的面積・IL範囲（保存済み候補内） | 元証拠 |
|---|---|---:|---|---|
| RF-F003 | **正式**・最大2Cv | **4件** | chip面積4⅔～6⅔、worst IL 0.882647～0.833188 dB（4L） | EXP-047 |
| RF-T005 | **試験**・最大3Cv | **6件** | chip面積3～6、worst IL 0.944268～0.805149 dB（3L・4L） | EXP-042/043/045 |

**判定：** 既存に保存された局所・有限探索候補集合の中で、H2/H3必須30dBに有限格子適合する**観測済み非支配点**。全設計空間のパレート最適性の証明ではない。**両条件ともIL≤0.30dB、公称H2/H3≥35dBは未達**。数学的極値・実装物理性能・全公差の成立は未保証。

詳細値、各候補の完全L/C/k・全6設定Cvと元checkpoint、独立検証の範囲は [結果の入口](../results/README.md) → [パレート元レポート](../pareto_rf_t005_rf_f003_20261017.md) → [不変JSON](../../data/pareto_snapshots/rf_t005_rf_f003_20261017.json) を参照する。

**EXP-047の記録訂正：** 4GJM候補について原独立検証JSON中の`chip_area=6`は記録誤り。正しい面積は**6⅔**。元証拠を改変せず、訂正根拠を明記して閲覧用表示に使用する。

## 実行済み・未完了の境界

- **実行済み：** EXP-042～047等の既存局所数値探索と、候補ごとに保存された有限格子／独立MNA検証。条件別の2026-10-17パレートスナップショットを記録。検証格子・深度は実験ごとに異なるため、全候補の同一深度検証を保証しない。
- **未実行・未保証：** RF-F003対応の共通`full_lpf`ソルバー／ローカルrunnerによる網羅的な探索を完了した実績はない。連続帯域極値、Q(f)、SRF、EM、組立・温度・公差、実測、物理面積は未保証。S2Pは手書き回路のモデル由来。
- **過去の数値：** RF-F002/ RF-T004のILや旧Q・可変C条件を、現行正式RF-F003の達成値として使わない。[履歴索引](../historical_results.md)。
- **実験番号：** [番号予約レジストリ](../../data/experiment_number_registry.csv)ではEXP-042～047が予約済み、EXP-018/019は永久欠番。新規実験は必ずmainへ事前予約して照合する。今回の文書整理は新規EXPではない。
- **既存CIの注意：** 2026-10-17の [Phase 2 regression](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39015048662) では、`audit_results.py`がEXP-047のmanifest共通必須フィールド不足を検出し失敗。全回帰PASSとは扱わない。対応状況は [未解決課題](open_research_questions.md) を参照する。

## 次に確認する場所

[現在の研究・実装課題](open_research_questions.md) ／ [ロードマップ（履歴併記）](../roadmap.md) ／ [RF-F003再ベースライン計画（2026-10-16当時の未実行表示を含む）](../rf_f003_phase2_rebaseline_plan_20261016.md) ／ [データ正本の案内](../../data/README.md)
