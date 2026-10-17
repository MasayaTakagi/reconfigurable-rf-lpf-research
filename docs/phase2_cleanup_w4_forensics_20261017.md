# Phase 2 W4追加精査：225件のrun別保全と39 workflowの利用履歴（2026-10-17）

> **位置づけ：** 本書はW4の[初回非破壊監査](phase2_cleanup_w4_evidence_workflow_review_20261017.md)の追加調査。研究原本・workflowの移動・削除は0件。旧W3の文書削除承認を実験証拠・workflowに適用しない。**Phase 2継続、Phase 3未承認。**

## 基準と方法

- 基準main：`26cacd179146bda5f5ca1cdcf0096dd61eb4faae`（前回W4のPR #81統合後）。Git履歴・元ファイルは変更しない。
- [225件の個別解析](../scripts/review_phase2_w4_unindexed.py)では元[機械参照索引](../scripts/build_reference_inventory.py)の`review_only_no_deletion`に該当するE-001/E-002ファイルを抽出。本文での元path一致／解決可能なMarkdownリンク／workflowからの元path一致／basenameのみの弱い言及を別カラムにする。JSONのキー構造、文書、ソースコード、checkpoint、run/検証群を分類。**元path文字列が存在しないことと実際の未使用を同義にしない**。
- [GitHub Actionsの利用履歴解析](../scripts/review_phase2_w4_action_runs.py)ではmainで追跡されていた39 workflowそれぞれのGitHub Actions REST API登録状態、API可視の実行件数、最新3runのID・日時・event・conclusion・source SHAを、CIに渡された読取権限のtokenで取得する。**API可視の件数は保存期間とGitHub表示に依存し、永久の実行履歴ではない**。0件でも未使用とは決定しない。
- 最新ブランチでの非破壊性は前回の[W4保全検証](../scripts/audit_phase2_cleanup_w4.py)（46ファイルGit blob一致と削除0件）を再実行し、RF制約・S2P・実験出典が変更されていないことを別ゲートで検査。
- 実行証拠は[専用CI](../.github/workflows/phase2_cleanup_w4_run_forensics.yml)のCSV/JSON artifactsとrun URLに保存し、重要な固定結果を`data/repository_reviews/`に移記する。**実測CI以前の結果を推測で記入しない**。

## 事前の保全判定

1. EXP-042/043のworkflow直接参照ソース、検証checkpoint、元PRのREADME／旧manifest、`data/validation/exp047_legacy_manifest_adapter_20261017.json`は**保持**。読取専用機械索引がない場合でも再現・訂正・数値の出典になり得る。
2. トレースを持つrunの中断・失敗・再開に必要な`.lock`／`tasks`／`manager.log`、元sourceコピーは無条件削除禁止。元の探索が数値的に再生できても、失敗原因の証拠は別用途。
3. workflowの`workflow_dispatch`は実機再実行の入口。`contents:write`、Git push、固定研究ブランチ参照は副作用と復旧手順を伴い、削除または置換の前に個別run・権限・出典保存のレビューが必要。
4. GitHub Actions APIのrun計数、workflowファイル名の一致、またはGit blobの内容重複**だけでは削除承認にならない**。削除提案は後続の明示owner承認・独立PRで行う。

## 最新の実施結果・未実施事項

初回W4の固定数値：対象747ファイル、うち機械索引未参照225件、workflow39件。[固定JSON](../data/repository_reviews/w4_read_only_audit_20261017_snapshot.json)。

**この追加PRの実行値とCI URLはPRチェック完了時に追記する。** 実行後に225件のグループ別分布、ソース参照区分、GitHub ActionsでのAPI可視利用状況を記録する。外部アーカイブにしかない元run・失効したActions Artifact・動的path／ログ全文の再現確認は依然として別作業。元研究証拠の削除は未承認。
