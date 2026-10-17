# Phase 2 W1：現行案内・歴史資料との境界・Markdown導線の更新（2026-10-17）

> **W1実施済み、PRレビュー中。** 原RF条件・元実験・元checkpoint・元manifestの削除・移動・内容改変は0件。Phase 2を維持、Phase 3には移行しない。

## 基準と差分

- 基準main：`055b222c79c73c7fbeacb19383f21c1da0625195`（[統合PR #71](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/71)後）。
- [W0再監査](phase2_cleanup_w0_current_main_audit_20261017.md)（[PR #73](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/73)）では全追跡Markdown 133件、リンク925件、実在しない相対リンク候補1件を確認。W0の計数は**当時のmain**に固定する。
- [整理・不要文書削除計画](phase2_repository_cleanup_and_deletion_plan_20261017.md)（[PR #72](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/72)）に対するW1レビューPRは[PR #74](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/74)。PR #74はPR #73をbaseとする積み上げPRであり、main未マージ。

## 実行済み文書修正

| 区分 | 実施内容 |
|---|---|
| `README.md` | PR #67「レビュー中」→ #71統合済み／新整理計画へ訂正。EXP-047による旧回帰失敗から、マージ前の最終回帰SUCCESSへの遷移を明記 |
| `docs/roadmap.md`・`docs/current/open_research_questions.md` | 旧EXP-047 manifest **監査エラーは索引専用アダプターで解決**。ただし実行当時のcommit/seed/環境は未確認。旧14＋最新10の統合済み24件へ修正 |
| `docs/current/phase2_status.md`・`docs/results/README.md` | 実際の固定24件CSVを案内し、正式RF-F003と試験RF-T005を別条件として維持 |
| `data/README.md`・`scripts/README.md`・`experiments/README.md`・`docs/README.md` | 24件不変索引とlive台帳、`--catalog`報告、元manifestの旧形式処理、#71統合・W0／新整理計画を反映 |
| 元Step 1～5の計画・最終検証報告 | 「未実施」「Draft／未マージ」は作成時点の履歴と明記し、冒頭に#71マージ済みの後日追補を追加 |

[24候補の固定CSV](../data/catalog/phase2_candidate_catalog_20261017.csv)は過去14件とRF-T005 6件／RF-F003 4件の**出典索引の統合**であり、すべて同条件で最適化を再実行したとの意味ではない。RF-F003のIL≤0.30dB・公称35dBは未達、連続域極値・Q(f)/SRF/EM・実測も未保証。

## W0で発見したEXP-004リンクの扱い — 保全を優先

旧[EXP-004 README](../experiments/chatgpt_topology_search/runs/EXP-004/README.md)の54行付近に、既に無効な`../../../../actions/workflows/lpf-target040.yml`への相対リンクがある。しかし同READMEは[EXP-004 manifest](../experiments/chatgpt_topology_search/runs/EXP-004/manifest.json)の`evidence`がSHA-256で固定する**実験原証拠**である。

W1最初の修正で原READMEを変更すると[Phase 2 regression](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39034186181)が`Historical evidence changed or missing`としてFAILしたため、**原文を完全復元**し、元manifestも不変とした。

修正後は[現行experiments案内](../experiments/README.md)で、[実在するGitHub Actions「Phase 2 target 0.40dB topology sweep」](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/workflows/lpf-target040.yml)への正しいブラウザURLを提供する。対応するワークフローソースは`.github/workflows/lpf-target040.yml`に存在確認済み。これは**原文中のリンク自体の修正ではない**。

したがって、全リンク不備0件と主張しない。**旧原証拠に残る既知の無効リンク1件**を公開済みの保全例外として扱い、その他の新規・予期しない不正リンクを0件にする。

## W1の検証

- [W1専用CI初回SUCCESS](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39034379812) （修正HEAD `16878050a83831f3796d7a2f1f656282936d44cb`）：追跡1,119件、Markdown137件、抽出リンク999件、既知の原文由来不正リンク1件、**予期しない不正リンク0件**、保全46件全SHA一致。
- [Step 5元証拠保全検査SUCCESS](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39034379820)。EXP-004原READMEを元Git blobへ復元した後に実行。
- 既知の原文不備を許容する範囲は**唯一のパス・唯一のリンク先**に限定し、他の相対リンク不備は[W1検証スクリプト](../scripts/verify_phase2_cleanup_w1.py)が失敗扱いにする。
- [Phase 2 regression](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39034379808)は上記修正HEADを対象に別途実行。最終CI状態はGitHub run自体を正とし、この文書の保存だけでSUCCESSに昇格させない。

## 残件・次工程

1. **履歴資料の内側の不正リンク1件は残存**。原証拠SHAを優先し、現行案内側に正しいリンクを用意。元資料の移設・削除やmanifest証拠の改変を含む解消は、個別の出典・オーナーレビュー無しに行わない。
2. W0監査のregexはネストURL・見出しアンカー・外部URLの完全な到達性を保証しない。W1の999件は当該時点のworktreeに限定した静的結果。
3. W2では構造・結合符号等による**候補検索属性**を追加し、元checkpointに存在しない値は`unknown`とする。
4. W3では旧二次文書7件を個別評価し、元ソースへの参照と固有数値・事故記録の復元手順を確立したうえで削除候補を判断する。

**W1は現行入口の整理と安全な導線補正。旧runの結果・実験回数・数値性能は変更していない。**
