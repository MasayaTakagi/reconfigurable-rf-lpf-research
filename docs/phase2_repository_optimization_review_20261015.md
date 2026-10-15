# Phase 2：リポジトリ保存最適化レビュー（GitHub-only、2026-10-15）

> **現行ユーザー方針：外部アーカイブを使用しない。** GitHubに実験再現のための必要最小限のデータを保存する。過去に検討した外部オブジェクトストレージや期限付きActions artifactを最終保存先とする案は**不採用**。詳細は [実験結果Git保存方針](experiment_result_storage_policy_proposal_20261015.md)。本書は監査記録/提案であり、主系統へのマージ・元証拠の移動削除は未実施。Phase 2継続。

## 1. mainの追跡ファイル数・容量（実測）

基準main SHA `ad1cda8c47054fbe97edc5b8bb97261804281285` のGitHub再帰tree（truncated=false）で次を確認した。

| 領域 | 個数 | tracked file bytes |
|---|---:|---:|
| `data/validation/` | 264 | 4,395,071 |
| `experiments/chatgpt_topology_search/runs/` | 249 | 2,621,302 |
| 上記以外 | 218 | 1,432,781 |
| **合計** | **731** | **8,449,154 B（約8.45 MB）** |

これは各pathの**非圧縮サイズ合計**であり、Git pack/履歴全体の実容量ではない。blob SHAが同じ別pathはGit内部で同一オブジェクトになり得る。`docs/repository_storage_audit_20261014.md`の旧時点監査では34同内容グループ・追加path38件、実行診断らしき144ファイル/約2.35MBを観測（**削除可能なファイル数ではない**）。差分レビューの単位はpathでなく、実験役割と参照/回路復元の可否とする。

`data/phase2_git_storage_budget.json`に基準と内部レビュー閾値を登録：新規run curated集合目安**512KiB**、新規1ファイル目安**128KiB**、新規1ファイルが**1MiB超なら監査失敗**、main全tracked bytes **25MiBでサイズ増加要審査**。これらはGitHubの公式上限ではなく**プロジェクト固有の運用閾値**。`scripts/audit_git_storage_budget.py`はPR/CIで新規blobサイズと全tracked容量を監査し、**ファイルを削除・移動しない**。

## 2. 実施済みの非破壊的監査

- **全39実験**（formal19、trial5、historical15）の証拠・run statusと候補IDを索引化。39中seed未記録25、実行SHA未記録15、実行環境未記録16、実行状態unknown16、6つの旧manifestが`evidence=[]`。元manifestと誤った報告値を事後的に改竄しない。
- **候補13件・比較条件8グループ**を暫定登録。RF-F002（正式）/RF-T004（trial）/旧仕様、30/35dB、strict/toleranceを分離。未登録・未保存ベクトルを数値候補へ昇格しない。
- PR #51で535研究対象を `immutable60/referenced429/review_only46` に分類。PR #52で46要レビュー項目を**参照あり32、同一blobの別pathのみ9、元PR説明README5**に保全分類。現行台帳では46件全て`retain_pending_source_context_review`、削除・移動**0件**。
- 元PR #38の17ファイルSHA256SUMS一致、別root README SHA、R1 ZIP CRCをCIで監査。確認された証拠を単純にZIP一本へ置換しない。
- 旧PR #47〜52の**6ブランチ**の先端SHAを現在mainと個別blob比較。研究証拠領域（`data/validation/`, `experiments/`, `candidates/`）のmain欠落blob **0件**。監査台帳`data/branch_retention_review_20261015.csv`、read-only `scripts/audit_branch_retention.py`、CIで再照合。Git履歴全体がmainへ祖先として統合済みという意味ではない。

## 3. GitHub-only運用での履歴保持

過去のPR #53 CI実行では完全履歴bundleを生成して別空repoへrestore、8 refs SHA・`git fsck --full`でPASS済み（例 [run #38681002625](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38681002625)）。**ただしActions artifactは期限付きであり、永久の証拠保管先として使用しない。** `scripts/backup_complete_git_history.py`は検査/復旧用の任意ツールとして保持するが、各PRの全履歴bundle自動生成は省容量運用のため停止する。

古いbranchを整理するときは、**GitHubの別ref（固定tagまたは保護archive ref）から旧tip commitに到達できることを検証**してから、所有者の明示承認を得て行う。ブランチやtagの削除、Git履歴rewrite/force pushは禁止（別途owner承認なし）。ref追加やbranch削除はこのPRでは未実施。GitHub自体の障害/アカウント喪失へ備える外部コピーは作らないため、**単一サービス依存のリスクは受容する**と明記する。

## 4. 回収済みChatGPT RF-T004 ZIPの保存方針

- ユーザー添付`RF-T004-EXP017-bundle.zip`：**118,646 bytes、35エントリ、SHA-256 `48175d3579d3814e5d3740858ee3959b88e9731b835cb2cd306ce6b0093ae640`**。ZIP CRC PASS、各memberのSHA-256/CRC32/sizeを `data/external_trial_zip_manifest_20261015.json` に登録。既存Git mainとバイト一致したmemberは`data/bands.csv`のみ、他34件は異なるGit blob。ただし違うバイト列と独自研究成果は同義ではない。
- 保存候補`EXP017-35P008`は既存PR #38保存候補と全回路値・6設定Cvが一致。RF-T004・3可変C trialであり正式RF-F002の欠落0.301248245dB点ではない。
- **GitHubの1ファイル128KiB目安を満たす**ため、原ZIPを**1個のGit blobとして保管する選択肢を推奨**。その場合、同梱スクリプト/JSONの別pathへの重複全展開は避ける。元ZIPだけで再現性に不十分なら、重要checkpointと検証コードなど**必要な最小ファイルのみ**Gitの読める形で抽出・登録する。元ZIPと抽出ファイルの双方が根拠になる場合は重複理由を明記。
- **現時点で元ZIPバイナリはGit未収録、ハッシュ目録のみ存在**。`scripts/verify_external_trial_zip.py`は本ファイルをGitに追加して取得できた場合、ZIP全体・35memberのSHA/CRCを検査するためのもの。Git未収録の段階ではCIがソース原本を確認したと主張しない。元ZIPを保存する前にチャット添付だけを削除しない。

## 5. 保存対象の優先度

| 優先 | Git保管するもの | 基本処理 |
|---|---|---|
| A 必須 | 元RF制約/bands SHA、run manifest、コードcommit/seed/env、探索範囲と集計、**完全なL/C/k+6設定Cv**、独立検証サマリー | 元run/候補IDと証拠hashを固定 |
| B 条件付き | 重要なwarm-start/失敗診断、再開根拠、Pareto多様性/閾値近傍の完全候補、元Gitにない固有コード、小さい回収ZIP | 意味/役割を決めて最小化し保持 |
| C 通常不要 | 毎iterationダンプ、大量全グリッド波形、全workerログ、キャッシュ、完了後の空lock、Gitで再取得できるコード丸ごとコピー | **新規runからGitへ無差別コミットしない**。rawなしでは全探索経緯を正確再現できない旨をmanifestへ記載 |

**新しい必須ゲート：** ソース・条件・完全ベクトル・数値集計の必要証拠が**Gitで追跡/読み戻し検査できたこと**。結果の`completed`と保存済み、独立MNA/物理検証済みは別軸。実行中の`results/`を保全済みと誤認しない。新規runのschema v2、検証ゲート、容量監査は段階導入する。

## 6. 残課題

1. **RG-001は保留**：EXP-017 RF-F002・30dB報告値0.301248245dBの全回路ベクトルと6設定Cvは未回収。RF-T004の3可変C ZIPで代用しない。
2. **RF-T004小容量原ZIPのGit取り込みは未実施**：必要原バイトを実際のGitで保全した状態まで保管完了とはしない。
3. **新規runのmanifest v2と完全ベクトル監査**は提案・部分的容量監査段階。元39実験へ遡及変更しない。
4. **旧6ブランチの整理**は保留：不要branchを保持していてもGit-only保管要件を満たす。ref再配置と削除は別承認。
5. **重要候補の共通格子・独立MNA再検証、物理Q(f)/SRF/EM**は未実行。本PRは保存管理の改善でありRF成果ではない。

**PR #53はDraft・未マージ、証拠削除・移動0件、Phase 2継続。**
