# experiments/：実験記録・完全回路ベクトルの案内（Phase 2）

**更新基準：2026-10-17。** このREADMEは実験の数値正本ではない。状態・制約・出典は [実験索引](../data/experiment_index.csv)、[中央EXP番号予約台帳](../data/experiment_number_registry.csv)、各runの元manifestとcheckpoint、必要に応じて別検証overlayを参照する。

## 元データの入口

- [chatgpt_topology_search/runs/](chatgpt_topology_search/runs/)：EXP-NNNごとの原manifest、候補の回路ベクトル、実行記録。
- [matching_limit/](matching_limit/)：自動グラフ探索、RF-F002などの旧`full_lpf`／`matching_only`実行基盤。実行器の対象条件を確認せずRF-F003成果だと判断しない。
- [データの案内](../data/README.md)：S2P、正式・試験RF制約、候補、独立検証の所在。

## 最新パレートと関係する実験

| EXP | 制約 | 記録上の目的・役割 | 2026-10-17保存パレート |
|---|---|---|---|
| [EXP-042](chatgpt_topology_search/runs/EXP-042/manifest.json) | RF-T005（試験） | 4L橋形とGJM削除・PCB置換の面積–IL比較 | 4L 3点の出典 |
| [EXP-043](chatgpt_topology_search/runs/EXP-043/manifest.json) | RF-T005（試験） | 3L単一シャント多モードと面積–IL比較 | 3L 2点の出典 |
| [EXP-044](chatgpt_topology_search/runs/EXP-044/manifest.json) | RF-T005（試験） | 3L結合π型の検討 | 今回のパレート一覧には非掲載 |
| [EXP-045](chatgpt_topology_search/runs/EXP-045/manifest.json) | RF-T005（試験） | 3L T型の低損失再最適化とPCB-C評価 | 3L 1点の出典 |
| [EXP-046](chatgpt_topology_search/runs/EXP-046/manifest.json) | RF-T005（試験） | 4L外側シャント・内側直列の検討 | 今回のパレート一覧には非掲載 |
| [EXP-047](chatgpt_topology_search/runs/EXP-047/manifest.json) | **RF-F003（正式）** | 4L／2可変Cの局所探索・Q80修正・独立MNA確認 | 正式4L 4点の出典 |

**注：** この表は実験の目的と出典を示し、全iterationの再現済み・最適化収束・物理実証を意味しない。**EXP-047だけは原manifestが非標準の局所in-chat記録**であり、[索引専用アダプター](../src/lpf/legacy_manifest_adapter.py)が固定SHAと実験証拠を照合する。PR #71の[回帰CI](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39028160775)はマージ前にPASSしたが、元optimizerの実行SHA／seed／環境は不明のまま。詳しくは[現行の未解決事項](../docs/current/open_research_questions.md)。

## 原本、overlay、報告値の区別

1. **元実験原本：** `runs/EXP-NNN/manifest.json` およびチェックポイント。実行条件、収束・中断、格子、失敗を当時の状態で保全する。
2. **選別候補：** [不変パレートJSON](../data/pareto_snapshots/rf_t005_rf_f003_20261017.json)の原ベクトルパス・Git SHAを起点に追跡する。
3. **独立再検証：** [validation/](../data/validation/)の別評価ログ・サマリー。後日成功した解析を元実験の成功や収束へ書換えない。

**新規EXP開始前にmainの番号予約・照合が必須**。EXP-018/019は永久欠番。整理作業で新しいEXPは発行しない。

[成果比較](../docs/results/README.md) ／ [研究Phase 2現行状況](../docs/current/phase2_status.md) ／ [文書総合入口](../docs/README.md)
