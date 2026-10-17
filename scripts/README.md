# scripts/：探索・検証・監査の用途別案内（Phase 2）

> 実行前に制約ID・コード・データ・実行状態を確認すること。以下の説明は**閲覧用索引**であり、個々のrunnerが正式RF-F003を実装済みとの主張ではない。新規実験の計算にはmainでの事前EXP番号予約・照合が必要。

## 主要スクリプトの案内

| 系統 | スクリプト | 主な役割 |
|---|---|---|
| RF候補の台帳監査 | [audit_research_catalog.py](audit_research_catalog.py) | 登録候補・元証拠と条件IDの健全性を監査 |
| 候補・RF数値監査 | [audit_results.py](audit_results.py) | 実験manifest／候補などの監査。2026-10-17時点でEXP-047の必須manifest項目不足により回帰CI失敗（解決済みとは扱わない） |
| 条件別パレート報告 | [report_research_pareto.py](report_research_pareto.py) | **旧候補台帳**`data/research_candidate_register.csv`から条件別グループを生成。2026-10-17の新パレート10点は未統合 |
| 研究証拠の参照棚卸し | [build_reference_inventory.py](build_reference_inventory.py) | Git追跡ファイル・manifest・候補台帳から証拠逆引きを構築 |
| 未登録証拠のレビュー | [triage_unlinked_evidence.py](triage_unlinked_evidence.py) | 自動削除せず保全／個別レビューを分ける |
| 実験inventory | [audit_experiment_inventory.py](audit_experiment_inventory.py) | EXPごとの登録・実行状態・証拠整合を確認 |
| 事後検証overlay | [audit_validation_overlays.py](audit_validation_overlays.py) | 元実験と後日の独立検証を区別・点検 |
| 候補のPCB可変Cルール | [verify_no_pcb_tunable_candidates.py](verify_no_pcb_tunable_candidates.py) | 対象条件の候補種別制限を検証 |
| 既存ローカル探索 | [local_p4.py](local_p4.py) | 旧P4-Aのplan/run/status/resume。matching_only成果はfull_lpf性能ではない |
| 既存full_lpf runner | [local_full_lpf.py](local_full_lpf.py) | 既存経路の条件を実行前に検証。2026-10-16の計画では旧RF-F002向けで、RF-F003対応を保証しない |

## プログラム実行の前提

通常のリポジトリ環境は `uv.lock` に固定されたuvで管理される。たとえば既存回帰を実行する場合はルートで次の操作を行う。

```bash
uv sync --frozen
uv run --frozen python scripts/audit_results.py
uv run --frozen python -m unittest discover -s tests -v
```

ただし、**2026-10-17の既存回帰CIではEXP-047 manifestスキーマ不整合によって`audit_results.py`が失敗**している。単純に全CI PASSと表現しない。CIの実行結果は [既存のRun](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39015048662)を参照する。

## 保全と変更のルール

探索・検証スクリプトの変更に伴って原checkpointや実行済み結果を改変しない。新条件の数値を算出する場合は、コードSHA・制約SHA・bandsと固定S2P・格子・独立検証を記録する。Phase 3は明示承認まで停止。

[全体README](../README.md) ／ [実験原本の案内](../experiments/README.md) ／ [結果の入口](../docs/results/README.md)
