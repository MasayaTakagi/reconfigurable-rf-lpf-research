# RF LPF研究成果・パレート解の入口（2026-10-17、Phase 2）

**利用範囲：保存済み・有限格子で確認された局所探索のbest-found。** 研究段階はPhase 2であり、以下の数値を数学的な大域最適値、RF-F003達成目標値、物理的な実装保証とは呼ばない。

**詳細出典：** [RF-T005 / RF-F003 パレート説明](../pareto_rf_t005_rf_f003_20261017.md) ／ [機械可読不変スナップショット](../../data/pareto_snapshots/rf_t005_rf_f003_20261017.json)。

## 条件ごとの整理（絶対に混合しない）

| 区分 | 正式／試験 | IC可変C | 保存された非支配点 | H2/H3評価 |
|---|---|---:|---:|---|
| **RF-F003** | 正式 | 最大2枝 | 4Lのみ4点 | 30dB必須の有限格子適合 |
| **RF-T005** | 試験 | 最大3枝 | 3Lが3点、4Lが3点 | 30dB必須の有限格子適合 |

どちらも外部固定S2P → LPF → 固定S2P、50Ω源、60−j40Ω負荷、6設定28不連続周波数区間を基準にする。35dB公称減衰とIL≤0.30dBは全候補で**未達**。

## RF-T005：3可変Cの試験条件（6点）

| Chip面積 | 構成 | GJM固定C | PCB-C | 最悪IL [dB] | 原実験 |
|---:|---|---:|---:|---:|---|
| 3 | 3L | 0 | 3 | 0.944268363 | [EXP-043](../../experiments/chatgpt_topology_search/runs/EXP-043/README.md) |
| 3⅔ | 3L | 1 | 3 | 0.895180009 | [EXP-045](../../experiments/chatgpt_topology_search/runs/EXP-045/README.md) |
| 4⅓ | 3L | 2 | 1 | 0.879244690 | [EXP-043](../../experiments/chatgpt_topology_search/runs/EXP-043/README.md) |
| 4⅔ | 4L | 1 | 3 | 0.819564515 | [EXP-042](../../experiments/chatgpt_topology_search/runs/EXP-042/README.md) |
| 5⅓ | 4L | 2 | 2 | 0.811306586 | [EXP-042](../../experiments/chatgpt_topology_search/runs/EXP-042/README.md) |
| 6 | 4L | 3 | 1 | 0.805148668 | [EXP-042](../../experiments/chatgpt_topology_search/runs/EXP-042/README.md) |

## RF-F003：2可変Cの正式条件（4点）

| Chip面積 | 構成 | GJM固定C | 最悪IL [dB] | 原実験 |
|---:|---|---:|---:|---|
| 4⅔ | 4L | 1 | 0.882646928 | [EXP-047](../../experiments/chatgpt_topology_search/runs/EXP-047/manifest.json) |
| 5⅓ | 4L | 2 | 0.843652332 | [EXP-047](../../experiments/chatgpt_topology_search/runs/EXP-047/manifest.json) |
| 6 | 4L | 3 | 0.836867952 | [EXP-047](../../experiments/chatgpt_topology_search/runs/EXP-047/manifest.json) |
| 6⅔ | 4L | 4 | 0.833188234 | [EXP-047](../../experiments/chatgpt_topology_search/runs/EXP-047/manifest.json) |

**4GJM候補の面積訂正：** 元独立検証JSONには `chip_area=6` との誤記がある。部品数ベースの正しい値は**6⅔**であり、元JSON自体は保存・不変とする。詳細は[元レポート](../pareto_rf_t005_rf_f003_20261017.md)。

## 読み方と限界

- **面積軸：** チップL／GJMの規約に基づく相対面積コスト。PCBパターンCおよび可変Cのchip面積コスト0は、実装物理面積ゼロを意味しない。
- **IL軸：** 外部端子間6設定の最悪値。min H2/H3、全6設定のCv、完全L/C/k、独立MNAの格子数は[元レポート](../pareto_rf_t005_rf_f003_20261017.md)の各checkpoint参照で確認する。
- **検証深度：** 有限格子値は候補により検証点数・独立MNA照合範囲が異なる。連続帯域極値、Q(f)、SRF、EM、公差、実測は未保証。
- **過去との区別：** 旧 [選別候補台帳](../../data/research_candidate_register.csv) の14件と、この保存パレート10件は[2026-10-17固定の統合24候補CSV](../../data/catalog/phase2_candidate_catalog_20261017.csv)で**索引として統合済み**。[カタログの出典・ハッシュ](../../data/catalog/README.md)を確認し、RF-F002の旧正式成果・RF-T004試験・RF-T005試験・RF-F003正式を同一条件でパレート比較しない。

[現行ステータス](../current/phase2_status.md) ／ [実験フォルダの案内](../../experiments/README.md) ／ [文書総合入口](../README.md)
