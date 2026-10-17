# 現行の未解決事項・実行ゲート（2026-10-17、Phase 2）

> このページは**調査・修正の入口**。最終的な課題の追跡元は [research_review_issues.csv](../../data/research_review_issues.csv)、現行RF仕様は [制約レジストリ](../../data/constraints/registry.json) と [設計仕様](../specification.md)。旧RG課題の記述はRF-F002時点に作成された部分を含むため、必要なら現行RF-F003に基づき別途更新する。

## 優先して扱う課題

| 順位 | 論点 | 観測済みの状態 | 完了判定 |
|---|---|---|---|
| **P1（残件）** | **EXP-047原実行の完全な出典復元** | 旧manifestは9必須項目を欠く非標準記録のまま。出典blobを固定した[索引専用アダプター](../../src/lpf/legacy_manifest_adapter.py)で[PR #71の回帰CI](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39028160775)は**マージ前PASS**。原実行SHA・seed・環境は未確認 | 元の出典を捏造せずに取得できた事実だけを追加。新規runの厳格manifest検証は維持し、完全再現を主張しない |
| **P0** | **正式／試験結果の混同防止** | RF-F003は最大2Cv、RF-T005は最大3Cv。旧RF-F002の値は新正式条件に適用不可 | 候補一覧・可視化・レポートが条件IDと実効制約SHA・最低要求値を明示し、異条件で非支配計算しない |
| **P1** | **正式RF-F003共通探索runnerと評価器の統合** | [2026-10-16計画](../rf_f003_phase2_rebaseline_plan_20261016.md)は作成当時の未実装状態を記す。その後EXP-047で局所数値探索と独立MNAの証拠を保存したが、共通探索pipeline全体の完成を意味しない | 最新main実装に対する独立外部S2P縦続評価と6設定回帰を整備、条件適用を確認 |
| **P1（残件）** | **候補のトポロジー検索属性** | 旧14件＋最新10件の[統合24候補CSV](../../data/catalog/phase2_candidate_catalog_20261017.csv)は出典・制約区分を保持して再生成可能。接続・配置・結合符号の専用検索列は未整備 | [固定2026-10-17カタログ](../../data/catalog/README.md)を保全したまま、未知値を捏造せず構造的な索引を拡充（整理W2） |
| **P1** | **検証深度の均一化と連続域評価** | 候補ごとに28×1,001／28×7,001格子など検証深度が異なる。全域極値・公差での厳密成立を示さない | 同一条件の候補について共通格子・独立MNAで再照合した検証overlayを保存 |
| **P1** | **履歴メタデータ欠損（RG-008/009）** | 旧39実験のメタデータ欠落は[RG-009](../../data/research_review_issues.csv)に記録される。EXP-042～047の追加によって旧集計を新しい全体数へ機械的に読み替えない | 証明可能なコードSHA・環境・seed・実行状態のみ追記し、推測補完しない |
| **P1** | **長期保全・整理（RG-005/007）** | GitHub-only保存。旧要レビュー46件は削除未承認。整理Step 1～5は[統合PR #71](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/71)で実装済み。追加の文書削除は[整理計画PR #72](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/72)で審査中 | path・blob・参照と復旧方法を照合し、原証拠は保持。過去文書削除は個別審査・承認後に実施 |
| **P2** | **物理実現性・モデルの不確かさ** | S2Pは回路モデル。Q(f)、SRF、EM、寄生の基準面、温度・公差・実装面積を未実証 | 候補別に前提、実測・EM・設計余裕・リスクを明示し、結果を別検証記録へ保存 |

## 旧課題との関係

- [RG-003](../../data/research_review_issues.csv)：warm-startの端子remap問題。旧runの不具合を現行候補性能へ流用しない。
- [RG-004/010](../../data/research_review_issues.csv)：旧RF-F002候補のカタログ網羅性・共通格子検証。現行RF-F003の10点についても別スコープで同様の証拠を必要とする。
- [RG-005/007/008/009](../../data/research_review_issues.csv)：GitHub-only保全、ブランチ、補足証拠、元manifestの欠損。実行済みと未実行を厳密に区別する。

## 手続上の制限

新たなRF探索・実験はmainの [実験番号中央予約台帳](../../data/experiment_number_registry.csv) で事前予約、照合を実施する。**Phase 3はユーザーの明示承認まで停止**。このページの優先順位は調査・整理上の案内であり、実験実行の承認ではない。

[現行ステータスへ戻る](phase2_status.md) ／ [研究ロードマップ](../roadmap.md) ／ [文書総合入口](../README.md)
