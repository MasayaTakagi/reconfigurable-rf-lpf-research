# Phase 2 リポジトリ保管最適化レビュー（2026-10-15、非破壊）

本レビューは、PR #53 が Draft / main 未マージの間に追加した監査である。現行正式RF-F002・試験RF-T004・研究Phase 2を変更しない。EXP-017の **RF-F002・30dB・IL=0.301248245dB** 報告点（RG-001）は原回路ベクトル未回収のまま保留する。保管監査はそれを解決済みと扱わない。

## 実施済みの保管管理

- PR #51で研究対象535ファイルを **immutable 60 / referenced 429 / review-only 46** に分類。
- PR #52で要レビュー46件の出所を調査し、**文書/コード参照32、同内容別パスのみ9、元PR説明README5**に区分。45件、46件などへ恣意的に削減しない。
- 正本の証拠保管は `data/research_storage_triage.csv`、`data/supplemental_experiment_evidence_index.csv`、`data/experiment_evidence_inventory.csv` と実際のrunディレクトリで追跡する。外部資料の回収は、GitHub保存物の照合とは別工程とする。
- EXP-034～041のlock、manager/workerログ、実行結果JSON、config、checkpointは役割が異なるため、テキスト重複やSHA一致だけで相互代替しない。アーカイブ後であっても元のrun相対パスと再現用manifestの復元性が必要。
- PR #38元資料のSHA256SUMSは**17件のみ**をカバーし、同フォルダのroot READMEは対象外。PR #52で元17件の一致とREADMEの別SHAおよびR1 ZIP CRCを報告・CIで確認。現時点では元アーカイブを変更しない。

## 現存のGitHubブランチに対する個別監査

**比較方法（実行済み）:** 現行main `ad1cda8c47054fbe97edc5b8bb97261804281285` と各ブランチheadのGitHub再帰treeを取得し、全tracked blob SHAを照合した。旧PRのmerged時刻・head SHAをGitHub APIで確認。比較はbranch **HEADのファイル内容**であり、Gitコミットの全履歴に対する完全性証明ではない。squash merge済みブランチはmainとGitグラフ上でdivergeしていても直ちに未統合としない。

| 旧ブランチ（省略名） | マージ済みPR | 先端blobのうちmainにバイト同一blobがない数 | うち研究証拠領域 |
|---|---:|---:|---:|
| `chore/phase2-experiment-inventory-evidence-20261014` | #50 | 2 | **0** |
| `chore/phase2-reference-retention-pareto-20261015` | #51 | 3 | **0** |
| `chore/phase2-result-catalog-governance-20261014` | #49 | 6 | **0** |
| `chore/phase2-triage-unlinked-evidence-20261015` | #52 | 0 | **0** |
| `feat/rf-f002-full-lpf-integration-20261014` | #47 | 11 | **0** |
| `test/rf-f002-full-lpf-recovery-20261014` | #48 | 2 | **0** |

研究証拠領域の判定範囲は `data/validation/`、`experiments/`、`candidates/`。**全6本のheadで新しい研究証拠blobがmainに欠けている事実は検出されなかった。** 一方、コード・文書の旧改訂が2～11blobあり、意味やGit履歴の代替性、元の外部bundle保管は追加確認を要する。PR #53の作業ブランチは**レビュー中のため削除対象外**。

判定した元先端SHA・PR・禁止処置は `data/branch_retention_review_20261015.csv` に記録。 `scripts/audit_branch_retention.py` がmainと全6本を読み取り専用で再照合し、GitHub Actionsのbranch_retention_summary.jsonへ出力する。実行前にoriginの全branch refを **fetchのみ** 行う。PR #53など新設/未審査のbranchは別途一覧化して自動削除しない。新しい研究証拠blobが旧ブランチにだけ現れたらCIを失敗させる。

**削除・ref変更実績：0本。** 将来の整理で不要なブランチを減らす場合にも、(1) ownerの明示承認、(2) 元head ref/SHA、元PR、全履歴・本体ファイルに対する確認、(3) 復旧可能な検証済みGit bundleを保管、(4) ブランチheadが変化していないことの再照合を必須とする。既存 `docs/maintenance/branch_cleanup_20261014.md` にある当時のbundleは**現行6ブランチの完全バックアップであるとは未確認**なので、そのまま流用しない。

## 39実験のメタデータ不足（出典のみ・再実行なし）

`scripts/report_experiment_metadata_gaps.py` が `data/experiment_evidence_inventory.csv` の39行から、実験ごとにrecorded/unrecordedを機械的に区分する。正式19／trial5／historical15を分離し、ソルバ実行や新しい数値達成を主張しない。

| 元manifestからの不足 | 実験数 |
|---|---:|
| execution unknown | 16 |
| random seed 未記録 | 25 |
| execution commit SHA 未記録 | 15 |
| environment 未記録 | 16 |
| manifest evidence 0件 | 6 |

実行状態のunknownとメタデータの欠落は重複計上され得る。属性の値が存在しても、元実験の再現成功を示さない。生成ファイル `artifacts/phase2_reports/experiment_metadata_gaps.csv` と `experiment_metadata_summary.json` をCIで保存する。元manifestは書き換えない。回収不能な値を推測で埋めたり、履歴のunknownを無根拠でcompletedに変えたりしない。**RG-009は一覧化が進むだけで、実験の再現性未達は残る。**

## 別チャットから回収したRF-T004試験ZIP

チャット添付 `RF-T004-EXP017-bundle.zip` は**原本 SHA-256 `48175d3579d3814e5d3740858ee3959b88e9731b835cb2cd306ce6b0093ae640`**。35エントリ、CRC PASS、バイト数118,646。既存mainと完全同一のGit blobは `data/bands.csv` のみ。候補 `EXP017-35P008` の回路値は既存PR #38から保存された拡張表現と一致し、重複保存する前に出所を照合する。生試行ログ・コードにはmainに無いバイト列が存在する。

**現状:** 原ZIPはチャットで受領したが、GitHubにZIP原本は未保管。上記SHA文字列とPR #53内の調査記録は原バイトの代替バックアップではない。GitHub APIのUTF-8文書作成でZIPをbase64本文として登録することはリポジトリの不要な肥大化と改ざん検出の混乱を招くため、本レビューでは行わない。将来の研究用ZIPの保管先・ライフサイクルを決定し、適切なバイナリ方式（検証済みのGit LFSまたは独立した原本archiveとSHA台帳）を採用するまで**保管ポリシーは未完了**とする。EXP-017 RF-F002の欠落ベクトルとは別データでありRG-001はopen。

## CI実行効率の改善（提案PR内、主系統への適用待ち）

従来のPhase 2 regressionは `push` と `pull_request` の双方を無条件に監視し、同一PRコミットで重複したフル監査を起動していた。今回のPR差分では `.github/workflows/audit.yml` を変更し、**pushはmainのみ、PRはpull_requestのみ、必要に応じてworkflow_dispatch**とする。PR側の古い実行に限りconcurrencyで自動キャンセルし、mainへのpush時の検証実行はキャンセルさせない。元RF評価検証・候補台帳監査・全ユニットテスト・出典監査・ブランチ監査は継続する。**これはPR #53のCI動作設定でありmainにはまだ反映されていない。** 計算費用の実測削減は本PRマージ後のイベント比較を要する。

## 保管ポリシーの移行ゲート（将来提案、未実施）

| 資料 | 望ましい保管先・方針 | 必須確認 |
|---|---|---|
| manifest、候補JSON、制約版、条件別Pareto | 現在のGit追跡を原則維持 | constraint_id/有効SHA、元run、実行/検証状態 |
| 元コード、再現可能なrun結果、チェックポイント | 原パスとGit履歴を維持 | 参照元、再現手順、保存時環境 |
| lock、workerログ、managerログ | 実行診断として別クラスの保全を検討 | 障害解析用の意味・参照関係・重複の役割 |
| 外部添付ZIP、生全試行ログ | バイナリ保管方式を決定し原SHAと結合 | 元ZipのCRC/SHA、個別ファイル索引、権限・保管期限 |
| 認証済み不要ブランチ | 所有者承認後に初めて削除可否判断 | 新規完全bundle、SHA固定、read-onlyレポート |

**リポジトリ最適化を完全終了とは判定しない。** 旧ブランチの全履歴・バックアップ確認、外部ZIP原本の保管、診断ログの階層設計、EXP-017欠落記録の運用上の終結条件が未決である。PR #53はユーザー承認までDraft/未マージ。Phase 3は開始しない。
