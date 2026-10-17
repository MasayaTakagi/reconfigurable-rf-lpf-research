# Step 1：最新main全追跡ファイル棚卸しと参照監査（2026-10-17）

> **実行済みの読み取り専用監査。** この文書は自動抽出結果であり、移動・削除・無参照証明・回路最適化・物理検証ではない。

- 対象main SHA：`bdb39904379637aeca5cf56ec3096e9e1b15f62a`
- 再帰Git tree：**1043 entries**（Git ls-tree -r、全追跡entry）
- 追跡ファイルの非圧縮size合計：**12,859,345 bytes**
- 静的参照として検出：**2943 edges**（text 938 filesを解析）
- 同一Git blob複数path：**34 groups**（余分なpath 38件）
- 旧46要レビュー台帳に記録：**46 paths**（現mainに存在：46）
- 未解決候補のMarkdownローカルリンク：**2**（手動精査が必要）

## 1. ルート領域の個数・非圧縮サイズ

| area | entries | bytes |
|---|---:|---:|
| `data` | 293 | 6,404,008 |
| `experiments` | 493 | 4,915,681 |
| `docs` | 56 | 504,270 |
| `scripts` | 52 | 425,965 |
| `tests` | 94 | 306,331 |
| `candidates` | 5 | 93,761 |
| `.github` | 30 | 83,808 |
| `src` | 14 | 74,797 |
| `uv.lock` | 1 | 34,153 |
| `README.md` | 1 | 15,274 |
| `LICENSE-STATUS.md` | 1 | 556 |
| `pyproject.toml` | 1 | 301 |
| `.gitignore` | 1 | 236 |
| `requirements.txt` | 1 | 204 |

## 2. 分類と処置（削除の自動承認なし）

| 保全分類 | 件数 | 処置 |
|---|---:|---|
| A：正本・原manifest | 66 | 元pathを維持 |
| B：成果・検証／稼働文書 | 717 | 索引化し元を保全 |
| C：履歴 | 214 | 出典を保全し目次で分離 |
| D：個別要レビュー | 46 | 削除・移動は保留 |

※自動分類はパス・過去台帳に基づく**一次分類**。B/C分類にも重要な原証拠が存在する。
※inbound参照0は不要の証明でない。動的パス、Git履歴、外部チャット、実行時依存は静的解析では網羅できない。

## 3. 重要な正本・最新パレートの照合

- 制約台帳 active正式ID：`RF-F003`
- `data/design_constraints.json`と正式RF-F003のバイト一致：**True**
- 2026-10-17パレート保存点：**{'RF-T005': 6, 'RF-F003': 4}**
- 完全checkpoint参照：**10/10 SHA一致かつ現存**
- S2P原本：`data/parasitics/circuit1_ant_coupler_0_6ghz.s2p` SHA256合致：**True**
- S2P原本：`data/parasitics/circuit2_poc_through_0_6ghz.s2p` SHA256合致：**True**

## 4. 優先して手動確認する事項

1. 未解決Markdownリンク：ファイル移動の前に意図した相対パスかを調査する（検出＝自動破損判定ではない）。
2. A区分の正本・元manifest、D区分の旧46証拠に対する移動を禁止したまま、B/Cの閲覧用索引のみ先行整備する。
3. 動的に組み立てるコードのパス、JSON内フィールド参照、CIの相互依存は別途意味解析を行う。
4. 同一blobはrun由来やsource_prの意味が異なる可能性があるため、削除しない。
5. 現行10候補の出典・面積・独立検証と、旧14件候補台帳の統合方法はStep 3で定義する。

## 5. 機械可読データ

- 全ファイル台帳（path、size、Git blob SHA、区分、静的参照数、移動リスク）：[step1_20261017_files_001.csv](../../data/repository_audits/step1_20261017_files_001.csv), [step1_20261017_files_002.csv](../../data/repository_audits/step1_20261017_files_002.csv)
- 検出参照辺：[step1_20261017_references_001.csv](../../data/repository_audits/step1_20261017_references_001.csv), [step1_20261017_references_002.csv](../../data/repository_audits/step1_20261017_references_002.csv), [step1_20261017_references_003.csv](../../data/repository_audits/step1_20261017_references_003.csv), [step1_20261017_references_004.csv](../../data/repository_audits/step1_20261017_references_004.csv)
- 未解決Markdownリンク候補：[step1_20261017_unresolved_markdown_links_001.csv](../../data/repository_audits/step1_20261017_unresolved_markdown_links_001.csv)
- 同一blobの別path：[step1_20261017_same_blob_groups_001.csv](../../data/repository_audits/step1_20261017_same_blob_groups_001.csv)
- [集計JSON](../../data/repository_audits/step1_20261017_summary.json)

## 6. 適用範囲の限界

本監査はorigin/mainのtracked Git treeと読み取れる小容量テキストを検査した。Git履歴全体・未追跡ローカル結果・外部添付・Actions期限付きartifact、実行時に生成される依存関係は調べていない。リンク抽出は保守的な静的ヒューリスティックであり未検出参照を根拠に消去してはならない。全tracked bytesはpack容量を表さない。

**現在の作業はStep 1の棚卸しのみ。研究Phase 2を維持し、Phase 3は開始しない。**
