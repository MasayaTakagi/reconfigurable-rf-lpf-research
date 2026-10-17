# Phase 2 W0：監査の解釈とW1への引き継ぎ（2026-10-17）

**監査対象main:** `055b222c79c73c7fbeacb19383f21c1da0625195`。本メモは [W0報告](../phase2_cleanup_w0_current_main_audit_20261017.md) と [削除候補台帳](../../data/repository_reviews/w0_cleanup_20261017_deletion_decisions.csv) の読み方を補足する。W0は削除の許可・削除実施ではない。

- [全追跡treeの監査](w0_20261017_report.md) はGit追跡ファイル1,092件、非圧縮13,693,027B、静的参照辺6,358件を返した。過去の1,043件は整理前の別コミットであり混同しない。
- [全Markdownリンクの抽出](../../data/repository_reviews/w0_cleanup_20261017_markdown_links.csv) は133文書・925リンクを走査し、ローカルリンクの`missing`候補1件（`experiments/chatgpt_topology_search/runs/EXP-004/README.md`行54）を抽出した。元のmainには正しい`.github/workflows/lpf-target040.yml`が存在するため、W1で意図したGithub Actionsへのブラウザリンクに修正する。
- URLへのHTTP到達性、Markdownヘッディングのアンカー、複雑なネスト・動的参照は本チェックでは未検証。Code-blockは除外したがinline code由来の検出の可能性は残る。
- 同一blob37組／追加41pathはGitの重複容量削減量ではない。RF-F003の正式正本と互換コピー、runの異なるログ・taskを機械的に削除しない。
- D-001～D-007はmain由来Markdown・静的文字列から全件に参照が検出された（合計値の意味は[判定CSV](../../data/repository_reviews/w0_cleanup_20261017_deletion_decisions.csv)を参照）。basenameだけの言及は用途の証拠と断定しない。
- 旧46件保全対象はpathおよびGit blob SHAが全件一致。**46件の削除承認はない**。
- 現行`main`の読み取り専用監査であり、PR #72の新計画ファイルをmain参照に含まない。W1/W3で内容を変える場合は新しいmainのSHAと新規の参照辺を追跡しなおす。

**次工程：** W1は古い現行状況と1件のリンクを修正する。W3は文書D候補ごとの独自数値・原因・復旧方法を抽出し、必要な出典を保全した後、ユーザー承認を受けて個別に削除する。

研究はPhase 2継続、Phase 3未承認。新たなRF解析・実験実行なし。

### 旧型静的パーサの候補20件とMarkdown本体の1件の違い

[W0全テキスト監査](w0_20261017_report.md)の「未解決候補20件」は、Markdown本文以外のPythonテスト・コードサンプル・ログ等も走査する旧Step 1互換の広い抽出結果であり、**破損Markdownリンク20件ではない**。この中には存在しないパスを意図的にテストする文字列も含まれる。一方、[W0全追跡Markdown抽出](../phase2_cleanup_w0_current_main_audit_20261017.md)では133ファイル・925リンクから、ローカルの`missing`を1件に絞った。両者の抽出母集団と判定規則を混同しない。
