# Phase 2 Git保管構造の非破壊監査（2026-10-14）

**監査対象:** main commit `73c4f19b3b1264beeb5e8cbb2764ae3f82fb4f57`（PR #49統合後）。GitHubの再帰Git tree（truncated=false）からblob path・Git blob SHA・ファイルサイズを収集。以下のサイズは**追跡ファイルのサイズ合計**であり、圧縮済みGitリポジトリ容量でも、履歴全体のディスク占有量でもない。

## 保存量の観測

| 位置 | tracked blobs | サイズ（合計・概数） |
|---|---:|---:|
| 全リポジトリ | 707 | 8.30 MB |
| `data/validation/` | 262 | 4.38 MB |
| `experiments/chatgpt_topology_search/runs/` | 249 | 2.62 MB |
| `scripts/` | 32 | 0.306 MB |
| `tests/` | 68 | 0.225 MB |

- 一致するGit blob SHAの重複グループは**34組**、各グループの1件目以外の追加参照数は**38件**（同一コンテンツが異なるpathに存在）。Gitは同一blobを物理的に共通化するため、これらを削除してもtracked path数の減少と同量のストレージ回収が保証されるわけではない。
- `data/validation`内には、locks、logs、tasks、worker results、manager.log等の実行状態・証拠に該当するファイルが**144件／約2.35MB**存在する（path名に基づく分類であり、不要ファイル144件と判定したものではない）。
- リポジトリ全体の`.lock`拡張子は39件で、**uv.lock 1件を含む**。実行時lockは38件。ログ拡張子`.log`は42件、`/tasks/`ファイル29件、`/results/`ファイル35件。
- `data/constraints/formal/RF-F002.json`と`data/design_constraints.json`は同一blob。これは承認済み正式正本と互換コピーの**意図的な重複であり、削除対象外**。
- `data/validation/rf_f002_convergence_20261014/code_snapshot/`や`EXP-020/source_pr38/`のソース・資料コピーは旧runの正確な再現や独立したブランチ証拠を保つ意味がある。ファイル名やSHAの一致だけで削除しない。

## 整理の推奨階層（現状のディレクトリ移動は行わない）

1. **A / 不変正本:** 承認済み正式制約・帯域・Git履歴・原checkpoint。改変や削除は禁止。
2. **B / 研究候補のキュレーション:** 再利用する完全な回路グラフ、全設定可変C、出典、検証状態。新設した候補台帳から元ファイルへ参照する。
3. **C / 再現証拠:** run config、source hash、環境、最適化結果、独立MNAレポート、aggregate、必要なサマリー。出典ハッシュを保持する。
4. **D / 実行時診断:** lock、managerのprocess log、task試行、再開の端点情報。停止・復元試験で重要なものは保持するが、一般的な探索runから無条件に長期保存しない運用ルールを導入する。
5. **E / 一時結果:** 未選別の大量のrun出力は`results/`に置く。Gitへ無差別コミットしない。

## 安全な構造最適化の条件

- **即時の削除・移動は0件。** 既存39manifestのevidenceに保存pathとSHA-256が含まれ、移動は参照破壊・履歴の追試阻害を引き起こし得る。
- 将来の移動はまずmanifest→個別証拠pathの有向参照一覧、blob SHA、run目的、CI参照を逆引きし、**正本の位置を定めたうえで**別PRで実施。移動後に旧SHA/内容比較と元run検証を行う。
- C/Dの分類はファイル名だけで確定しない。例：EXP-034～036のstop/resumeテストではlock、manager.log、tasksが**検証の一次証拠**になり得る。
- Git物理容量を減らすための履歴書き換え（`filter-repo`・force push）は行わない。古いコミットからの証拠再現と参照を優先する。
- 新規runの原則は`results/`内に全raw情報、Gitには候補JSON／manifest／検証サマリー／必須のチェックポイントやロック証拠に絞ってキュレーション。runごとの採否理由を記録する。

## 次のゲート

1. Git管理ファイルに対するmanifest参照逆引きと「保持必須」「要レビュー」「新規runからGit対象外」を自動分類し、差分だけを提案する。
2. EXP-016など古いrunを当時の実行環境と独立解析で再検証して、新しい証拠manifestへ紐付ける。過去のsource-only manifestは無断書き換えしない。
3. 研究候補を選別したパレートレポートをRF制約ごと・要求閾値ごとに出し、旧レガシーと数値許容差内候補を正式実証と混同しない。

以上は**保管経路の棚卸し**であり、回路設計制約を変更したりPhase 3に移行したりするものではない。
