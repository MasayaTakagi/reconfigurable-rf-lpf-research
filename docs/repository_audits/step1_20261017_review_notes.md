# Step 1補足レビュー：参照候補とCIゲート（2026-10-17）

> **状態：実行済み監査データへの事後ソース照合。** 現行main `bdb39904379637aeca5cf56ec3096e9e1b15f62a` に対する [自動監査](step1_20261017_report.md) と [JSON集計](../../data/repository_audits/step1_20261017_summary.json) を補足する。元run／元manifest／制約／候補／コードは変更していない。Phase 2継続。

## 1. 未解決Markdownリンク2件の原因確認

監査により [一覧CSV](../../data/repository_audits/step1_20261017_unresolved_markdown_links_001.csv) に抽出された2件を、mainの元ソースと照合した。

| source | 参照内容 | 判定 | 次の処置 |
|---|---|---|---|
| `experiments/chatgpt_topology_search/runs/EXP-004/README.md` | `../../../../actions/workflows/lpf-target040.yml` | **文書リンク誤り候補**。解決先`actions/workflows/...`は追跡treeに存在しない。一方、同READMEには`../../../../.github/workflows/lpf-target040.yml`への正しいソースリンクが別に存在する | Step 2でGitHub ActionsのブラウザURLにするか正しいrepo相対パスに修正。元README修正は別PRで差分確認 |
| `tests/test_triage_unlinked_evidence.py` | `../data/validation/a.json` | **テストフィクスチャ**。元ソースは`tracked = {"docs/source.md", "data/validation/a.json"}`という架空データを使用する単体テストであり、実リポジトリのファイル参照ではない | リンク破損件数に含めない。次回監査ではテスト文字列を誤検知扱いに区別 |

したがって、**自動検出2件の内訳は、実文書リンクの要修正候補1件と正常なテストフィクスチャ1件**。ユーザー向けの「破損リンク2件」と表現しない。これは静的抽出によって検出できた範囲であり、全リンクが正しい保証ではない。

## 2. 既存のPhase 2回帰CIにおける異常（整理計画とは別件）

PR #67の [Phase 2 regression run 39015048662](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39015048662) のaudit jobは `python scripts/audit_results.py` で**失敗**し、後続の回帰処理はスキップされた。ログの主要エラーは次の通り。

```text
FAILED:
Cases: 6 band segments: 28 active candidates: 3
- Invalid EXP-047 manifest: Missing manifest fields:
  ['code', 'constraints', 'environment', 'evidence', 'limitations',
   'objective', 'purpose', 'random_seed', 'search_scope']
```

`experiments/chatgpt_topology_search/runs/EXP-047/manifest.json` はmainに存在し、現行RF-F003・EXP-047の実験記録だが、監査が要求する共通manifest構造と一致しない。Step 1がこれを修正したり、未実施の検証を実施済みに変更したりしてはならない。

- **原因の範囲**：CIログからは必須フィールド欠落が直接原因と確認できた。必要な対処が元manifestの変更か、適切な別検証overlay／スキーマ拡張かは要設計であり未確定。
- **研究への影響**：既存のPhase 2 regression全体は**PASSしていない**。Step 1専用監査が実行・保存できたことを全回帰PASSと混同しない。
- **提案する修復ゲート**：元manifestの出典・実行状態（in-chat局所探索、Actions探索の未実行）を保持し、必要なメタデータの証明可能性を調べたうえで、後続PRで監査の互換性を回復する。元の値を推測で埋めず、実行済み／未実行を変えない。修復後に全CI PASSを確認する。

## 3. Step 1監査の保存状況と未完了範囲

- **実行済み**：GitHub Actionsで`origin/main`の再帰Git treeから **1,043 path / 12,859,345 B** を取得。938テキストを解析して静的依存辺2,943件、同一blob34グループ、46件の旧要レビュー台帳照合を記録。
- **出典整合PASS**：RF-F003正式制約の互換コピー一致、固定入力・出力S2P双方の指定SHA-256一致、RF-T005 6件＋RF-F003 4件の完全候補checkpoint現存・Git SHA一致（10/10）。
- **保存先**：専用PR #67の `docs/repository_audits/` と `data/repository_audits/`。結果コミット `8532ab058ef3dcb32a82838e9c1bb2bdfae43a29`。
- **未実施**：全Git履歴到達性・全ブランチ、コード実行時の動的依存、全Markdown意味レビュー、GitHub外のチャット添付、移動可否の最終判定、RF回路数値再計算。
- **移動・削除0件**。A/B/C/Dの機械的区分は保存・索引の判断材料であり、削除承認ではない。

**次の推奨作業**：Step 2（README・文書目次の整理）。ただしStep 2の完了判定を全CI PASSとする場合、上記EXP-047 manifestの監査互換問題を別の作業ゲートとして解消する必要がある。
