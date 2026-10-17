# data/：RF制約・候補・証拠台帳の案内（2026-10-17）

> **ファイルの所在案内。** このREADMEはRF数値仕様ではない。規約と数値正本は [constraints/registry.json](constraints/registry.json)、[bands.csv](bands.csv)、固定外部S2PとそのSHA-256によって規定される。Phase 2継続。

## 正本と役割

| ファイル／フォルダ | 用途・取扱い |
|---|---|
| [constraints/registry.json](constraints/registry.json) | 有効な**正式RF制約ID**の唯一の選択台帳（2026-10-17時点でRF-F003） |
| [constraints/formal/RF-F003.json](constraints/formal/RF-F003.json) | 現行正式RF設計制約の機械可読正本 |
| [design_constraints.json](design_constraints.json) | 現行正式条件の互換コピー。正式JSONと一致させる。独立の仕様源にしない |
| [constraints/trial/RF-T005.json](constraints/trial/RF-T005.json) | RF-F003を基準に可変Cの上限だけ最大3独立枝とする**試験条件** |
| [bands.csv](bands.csv) | 6設定のUL/DL/H2/H3対象周波数帯の正本 |
| [parasitics/](parasitics/) | RF-F003がSHA-256で固定する入力S2P・出力S2P。実測ではなく回路モデル由来 |
| [pareto_snapshots/rf_t005_rf_f003_20261017.json](pareto_snapshots/rf_t005_rf_f003_20261017.json) | 2026-10-17の**保存済みbest-foundパレート**（RF-T005 6点、RF-F003 4点）。新しい値で上書きしない |
| [experiment_number_registry.csv](experiment_number_registry.csv) | 新規EXP番号のmain事前予約正本。欠番EXP-018/019再利用禁止 |
| [experiment_index.csv](experiment_index.csv) | 実験ID別の制約・実行状態・原manifestの検索入口 |
| [research_candidate_register.csv](research_candidate_register.csv) | **現行の旧条件選別台帳**（2026-10-17時点14件）。[固定14件入力](catalog/research_candidate_register_20261017.csv)と最新10件を合成した[24候補CSV](catalog/phase2_candidate_catalog_20261017.csv)は**日付付き派生索引**であり、live台帳を置き換えない |
| [research_review_issues.csv](research_review_issues.csv) | 歴史的RG課題を含むレビュー問題台帳 |
| [validation/](validation/) | 独立MNA検証、事後再評価、数値・実行の証拠。元ファイルを改変しない |

## 2026-10-17の派生カタログと現行台帳の使い分け

2026-10-17パレートは、正式RF-F003最大2Cv／試験RF-T005最大3Cv、外部固定S2P付き、必須H2/H3≥30dBの有限格子における保存候補を分離している。どちらもIL≤0.30dB・35dB公称は未達。実行や検証の詳細は [結果の閲覧入口](../docs/results/README.md) と [原レポート](../docs/pareto_rf_t005_rf_f003_20261017.md) に記載する。

旧 [research_candidate_register.csv](research_candidate_register.csv) の2026-10-17固定14件とRF-F003/RF-T005の新規10件は、[統合24件索引](catalog/phase2_candidate_catalog_20261017.csv)に出典別・比較群別に整理済み。**旧RF-F002と現行RF-F003、正式／試験を混ぜた非支配計算は禁止**。今後のlive候補の追加は、この不変2026-10-17索引の自動更新を意味しない。

## 証拠保全上の注意

- 元実験の完全ベクトルは [experimentsの案内](../experiments/README.md) → `runs/EXP-NNN/` を参照する。元checkpointと検証overlayを区別する。
- 別の格子幅・別の独立MNAで確認したことは、条件を揃えた再検証と同じではない。
- 未リンク、同一Git blob、古いログ・lockだけでは削除可否を決めない。[統合PR #71](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/71)では46件が元SHA一致・削除未承認で保全。[W0削除候補再監査](../docs/phase2_cleanup_w0_current_main_audit_20261017.md)に別件の旧文書7候補を記録。
- GitHubを長期保全先とし、期限付きActions artifactを唯一の根拠としない。

[プロジェクトREADME](../README.md) ／ [文書一覧](../docs/README.md)
