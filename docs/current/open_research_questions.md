# 現行の未解決事項・実行ゲート（2026-10-17、Phase 2）

> このページは**調査・修正の入口**。最終的な課題の追跡元は [research_review_issues.csv](../../data/research_review_issues.csv)、現行RF仕様は [制約レジストリ](../../data/constraints/registry.json) と [設計仕様](../specification.md)。旧RG課題の記述はRF-F002時点に作成された部分を含むため、必要なら現行RF-F003に基づき別途更新する。

## 優先して扱う課題

| 順位 | 論点 | 観測済みの状態 | 完了判定 |
|---|---|---|---|
| **P1** | **EXP-047の元実行再現情報の欠損** | [旧CI失敗](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39015048662)は原manifestの標準9フィールド不足。原本を維持した[旧形式索引アダプター](../../src/lpf/legacy_manifest_adapter.py)導入後、[PR #71最終回帰](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39028160775)はSUCCESS（325テスト） | 元のoptimizer SHA・乱数seed・環境は依然不明。推測で埋めず、完全な厳格manifest／計算再実行と索引互換を区別 |
| **P0** | **正式／試験結果の混同防止** | RF-F003は最大2Cv、RF-T005は最大3Cv。旧RF-F002の値は新正式条件に適用不可 | 候補一覧・可視化・レポートが条件IDと実効制約SHA・最低要求値を明示し、異条件で非支配計算しない |
| **P1** | **正式RF-F003共通探索runnerと評価器の統合** | [2026-10-16計画](../rf_f003_phase2_rebaseline_plan_20261016.md)は作成当時の未実装状態を記す。その後EXP-047で局所数値探索と独立MNAの証拠を保存したが、共通探索pipeline全体の完成を意味しない | 最新main実装に対する独立外部S2P縦続評価と6設定回帰を整備、条件適用を確認 |
| **P1** | **統合候補の構造検索と増分管理** | [固定24候補CSV](../../data/catalog/phase2_candidate_catalog_20261017.csv)に旧14件・最新10件を統合済み。[元の不変パレート](../../data/pareto_snapshots/rf_t005_rf_f003_20261017.json)と別物。接続／物理列順／結合符号の検索用属性は十分でない | 元checkpointの記述がある場合だけ構造属性を追加し、欠損はunknownとして保持。将来live台帳との用途を区別 |
| **P1** | **検証深度の均一化と連続域評価** | 候補ごとに28×1,001／28×7,001格子など検証深度が異なる。全域極値・公差での厳密成立を示さない | 同一条件の候補について共通格子・独立MNAで再照合した検証overlayを保存 |
| **P1** | **履歴メタデータ欠損（RG-008/009）** | 旧39実験のメタデータ欠落は[RG-009](../../data/research_review_issues.csv)に記録される。EXP-042～047の追加によって旧集計を新しい全体数へ機械的に読み替えない | 証明可能なコードSHA・環境・seed・実行状態のみ追記し、推測補完しない |
| **P1** | **長期保全・整理（RG-005/007）** | GitHub-only保存、旧要レビュー46件は削除未承認。旧ブランチ整理も別承認制 | path・blob・参照を追跡可能に保ち、整理後も重要証拠をGitで保全 |
| **P2** | **物理実現性・モデルの不確かさ** | S2Pは回路モデル。Q(f)、SRF、EM、寄生の基準面、温度・公差・実装面積を未実証 | 候補別に前提、実測・EM・設計余裕・リスクを明示し、結果を別検証記録へ保存 |

## 旧課題との関係

- [RG-003](../../data/research_review_issues.csv)：warm-startの端子remap問題。旧runの不具合を現行候補性能へ流用しない。
- [RG-004/010](../../data/research_review_issues.csv)：旧RF-F002候補のカタログ網羅性・共通格子検証。現行RF-F003の10点についても別スコープで同様の証拠を必要とする。
- [RG-005/007/008/009](../../data/research_review_issues.csv)：GitHub-only保全、ブランチ、補足証拠、元manifestの欠損。実行済みと未実行を厳密に区別する。

## 手続上の制限

新たなRF探索・実験はmainの [実験番号中央予約台帳](../../data/experiment_number_registry.csv) で事前予約、照合を実施する。**Phase 3はユーザーの明示承認まで停止**。このページの優先順位は調査・整理上の案内であり、実験実行の承認ではない。

[現行ステータスへ戻る](phase2_status.md) ／ [研究ロードマップ](../roadmap.md) ／ [文書総合入口](../README.md)
