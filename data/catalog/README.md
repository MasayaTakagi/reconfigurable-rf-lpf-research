# Phase 2 研究候補カタログ（2026-10-17）

**位置付け：派生ビュー。** 現行の検索用CSVは、以下の2つの**原本を変更せず**再生成したものです。

| データ系列 | 原本 | 件数 | 条件 |
|---|---|---:|---|
| 従来の選別候補 | [research_candidate_register.csv](../research_candidate_register.csv) | 14 | RF-F002／RF-T004等、条件・閾値別 |
| 2026-10-17保存済み非支配候補 | [rf_t005_rf_f003_20261017.json](../pareto_snapshots/rf_t005_rf_f003_20261017.json) | 10 | RF-T005（trial）6件とRF-F003（formal）4件 |

**統合24件**は[CSV](phase2_candidate_catalog_20261017.csv)でフィルタ可能です。原checkpointの相対パス／Git blob SHA、実行状態、記録済みの独立MNAプローブ点数、収束状態、パレートの条件別キーを含みます。[集計JSON](phase2_candidate_catalog_20261017_summary.json)と[人間向けレポート](../../docs/results/phase2_candidate_catalog_20261017.md)も参照してください。

## 条件を混合しないための規則

- `comparison_key`単独だけではなく、`constraint_class`、`constraint_id`、`effective_constraint_sha256`、`objective`、`requirement_db`、`threshold_classification`を照合する。
- RF-F003は**正式・最大2可変C**、RF-T005は**試験・最大3可変C**。同一パレート集合で優劣を評価しない。
- `strict_finite_grid`、`tolerance_only`、`reported_finite_grid`は原値と数値的証拠の深度が異なる。格子やMNAの照合深度も候補別である。
- 旧14件で記録がないチップ部品内訳・検証格子は空欄とし、過去の数値を新条件で達成済みとみなさない。
- RF-F003の4GJM候補の`chip_area=6`は原検証JSONの誤記であり、統合ビューでは部品数から計算した**6⅔**を採用する。原証拠を改変しない。
- 重要な値は[不変スナップショット](../pareto_snapshots/rf_t005_rf_f003_20261017.json)、元checkpoint、独立検証、必要なSHAを辿って確認する。SHA一致は再解析済みの意味ではない。

## 再生成

```bash
python scripts/build_phase2_candidate_catalog.py
python scripts/build_phase2_candidate_catalog.py --check
python scripts/report_research_pareto.py --catalog data/catalog/phase2_candidate_catalog_20261017.csv \
  --csv artifacts/pareto_step3.csv \
  --summary artifacts/pareto_step3.json \
  --markdown artifacts/pareto_step3.md
```

`build_phase2_candidate_catalog.py`は元sourceを読み取り、元のGit blob SHAや制約・実験ID・面積・閾値を照合して派生ファイルだけを生成します。**新規最適化・回路再計算は行わず、EXP番号も採番しません。**

本作業はPhase 2に限定し、Phase 3は所有者が明示承認するまで停止します。
