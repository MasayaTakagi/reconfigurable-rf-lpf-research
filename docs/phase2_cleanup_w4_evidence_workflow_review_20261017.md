# Phase 2 W4：実験出力・旧workflowの意味監査（2026-10-17）

> **状態：W4の非破壊監査を実装しPR CIで検証する段階。削除・移動0件、所有者の個別承認0件。** [W3で承認された旧二次文書4件の削除](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/80)は**今回のE/W区分の自動削除承認ではない**。原研究の[46件保全審査](../data/repository_reviews/step4_retention_46_20261017.csv)は継続。

## 1. 正本とW4の境界

- 作業起点：main `a11e9edc06b1238558cfeff1efb005faf668692b`（2026-10-17、PR #80統合後）。研究Phase 2。Phase 3はユーザー明示承認まで着手しない。
- [運用正本](chatgpt_project_instructions.md)、[追加整理計画](phase2_repository_cleanup_and_deletion_plan_20261017.md)、[W0監査](phase2_cleanup_w0_current_main_audit_20261017.md)、[W3個別審査](phase2_cleanup_w3_document_review_20261017.md)を参照。
- E-001 `data/validation/`、E-002 `experiments/chatgpt_topology_search/runs/`、W-001 `.github/workflows/exp042_*.yml`、その他EXP専用workflowを対象。正式RF-F003/試験RF-T005の正本や候補・実験結果には変更しない。
- [W4審査ゲートCSV](../data/repository_reviews/w4_cleanup_decision_gates_20261017.csv)は判断区分、個別承認状態を記録。**ファイル個票はCI runのArtifactsとして生成**し、現時点ではGitに全個票を直接追加しない。

## 2. 新しい実行済み監査との区別

既存の[証拠逆引きツール](../scripts/build_reference_inventory.py)はmanifestにハッシュ登録された証拠、候補台帳checkpoint/verification、補助索引とvalidation overlayを追跡する。**索引未参照は不要の証明にならない。** 中断・再開のlocks／tasks／manager.log、ソースコピー、独立回路検証、旧PRの履歴などに別の役割がある。

W4では[読み取り専用監査スクリプト](../scripts/audit_phase2_cleanup_w4.py)を追加し、最新checkout上の：
- 全tracked E-001/E-002ファイルをGit blob SHA／bytes／実験・validation群／既存機械参照／旧46件保護の有無で区分する。
- `.github/workflows/`を列挙して`workflow_dispatch`の再実行性、contents書込／git push、研究ブランチ固定参照、ソースliteral pathを検出する。
- [W3マージ後main](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/commit/a11e9edc06b1238558cfeff1efb005faf668692b)との差分で**削除0件**を保証し、旧46件の追跡Git blob SHAを照合する。
- 現時点で新たなRF数値計算を行わず、`artifacts/phase2_reports/w4/`に候補ファイルCSV／workflow CSV／要約JSONを作成する。

**注意：** workflowのテキスト解析だけではGitHub Actionsの過去全run数・実際の最終利用日・artifact期限・パラメータ・実行経路・動的な生成pathを網羅できない。`run_id`、source SHA、元PR、再実行と停止再開の依存は**候補ごとの追加レビュー**が必要。履歴の再生手段を消さないため、現在のworkflow存在／未使用を別検査しても即削除しない。

## 3. 監査前の実装上の重要事項（mainの実ファイル本文を確認）

- [EXP-042 RF-T005全系最適化](../.github/workflows/exp042_rf_t005.yml)はmainのEXP番号予約と試験制約を検査し、ユーザー手動`workflow_dispatch`で30/35dB目標を選ぶ。高密度検証jobとArtifacts作成も含む。**機能用途のあるworkflow**であり、「EXP終了＝不要」ではない。
- [EXP-042 manifest再生成workflow](../.github/workflows/exp042_manifest.yml)は特定研究ブランチをcheckoutし、manifest・experiment indexを更新する`contents:write`とpushを持つ。**歴史的な書込副作用、固定参照元の保全と適切な廃止ゲート**を分ける。
- [EXP-042 passband-Q](../.github/workflows/exp042_passband_q.yml)は実行ログ、stdout/stderr、終了コードをArtifactsに集める。欠損・途中中断を含む実行出典の破壊を避ける。
- [EXP-043独立3L MNA](../.github/workflows/exp043_verify_3l.yml)はcheckpointから独立枝電流解析を起動し、再検証可能なコードパスを提供する。
- [EXP番号事前予約workflow](../.github/workflows/reserve_experiment_number.yml)は新規実験着手の中央ゲート。**削除候補に含めない**。

## 4. W4実削除を検討する前の必須ゲート

1. file/runごとに実験ID・制約ID・主source SHA・Git blob SHA・manifest/checkpoint・後日検証の出典を示す。
2. static/dynamic参照、README、元manifest、追試コード、Actions job、再実行可能性・stop/resumeの依存を調査する。利用履歴はGitHubでrun情報を別取得。
3. **旧46件は無許可削除禁止**。類似blobや参照0だけで候補昇格しない。新規E/W削除はファイル/ワークフロー別の所有者承認と別PRが必要。
4. 保存場所・参照更新・`git show`の復元、同条件数値再現（必要時）を実証し、Phase 2回帰とW1リンク監査をPASSしてからマージ。
5. 今回の終了条件は**監査結果と未解決依存がGitHubに残ること**。削除0件を「W4削除の完了」とは扱わない。

## 5. 結果の記録状態

- GitHubのmainファイル本文に基づく上記workflowの機能確認：**実施済み**。
- W4新スクリプトのGitHub Actionsでの実走査、群別件数、全ファイル個票：**PR CIで実行・検査**（CI完了後に追記）。
- GitHub Actions全履歴の時系列実測調査、物理RF独立検証、新規RF実験：**未実施**。
