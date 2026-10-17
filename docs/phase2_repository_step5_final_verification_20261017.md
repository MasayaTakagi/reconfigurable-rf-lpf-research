# Phase 2 Step 5：リポジトリ整理の統合整合性検証（2026-10-17）

> **状態：検証実行済み／全4ワークフローPASS。** この文書はPR #67～70の統合検証ブランチの結果であり、元4 PRのmainへのマージ完了を意味しない。Phase 2を維持、Phase 3は所有者の明示承認まで停止。
>
> **基準main：** `bdb39904379637aeca5cf56ec3096e9e1b15f62a`。  
> **検証基準の統合ブランチHEAD：** `d1e8111f32d5762266faaa92e3968566ef829d2c`（後続の本報告追加コミットとは別）。  
> **検証ブランチ／Draft PR：** [PR #71](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/71)。  
> **参照元：** [Step 1：PR #67](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/67)、[Step 2：PR #68](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/68)、[Step 3：PR #69](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/69)、[Step 4：PR #70](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/70)。すべてDraft・main未マージ。

## 1. CI実行結果（統合ブランチに対する実行済み証拠）

| ゲート | GitHub Actions | 結果 | 実行範囲 |
|---|---|---|---|
| **Phase 2 regression** | [run 39024824321](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39024824321) | **SUCCESS** | 325 unittest全件PASS、RF正式制約、実験45件、旧検証パイプライン、候補24件・10比較群、元ZIP・元ブランチ・予約・Git保存監査 |
| **Step 3派生候補の検証** | [run 39024824317](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39024824317) | **SUCCESS** | 旧14候補とRF-F003 4／RF-T005 6候補の派生台帳・出典blob・条件別非支配点 |
| **Step 4歴史文書・保全監査** | [run 39024824319](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39024824319) | **SUCCESS** | mainの56文書、同一blob34組／追加38path、従来の46要レビュー件 |
| **Step 5統合保全・リンク監査** | [run 39024824311](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/39024824311) | **SUCCESS** | 全旧Git treeの変更許可監査、S2P/制約、パレート出典、387ローカルMarkdownリンク、限定EXP-047アダプター |

**注意：** 上記runは報告文書の作成**前**のコミットに対するPASS。文書追記後の再実行で最終HEADも確認する。全回帰PASSはソフトウェア再現性・既存モデル内の検査を示すだけで、物理性能保証や全設計空間の探索完了ではない。

## 2. 元1,043ファイルの保全結果

[読み取り専用統合監査スクリプト](../scripts/verify_repository_step5_integration.py)により、Git blobをmainの固定コミットと比較。

| 監査項目 | 結果 |
|---|---:|
| main基準trackedファイル | **1,043** |
| 元blobをバイト単位で不変保持 | **1,032** |
| 意図した11個の既存ファイル変更 | **11** |
| main由来のファイル削除 | **0** |
| 明示許可リスト外の既存path変更 | **0** |
| 新規ファイル（上記テストHEAD時点） | **44** |
| 統合ブランチtrackedファイル（同時点） | **1,087** |
| ローカルMarkdownリンク（16追加ページ＋既存3ページ） | **387件、未解決0件** |

既存11ファイルの変更は文書入口・ロードマップ・条件別レポート生成・実験証拠インベントリ・旧EXP-047互換検査・対応テストとCIに限定。元研究checkpoint、旧run、S2P、bands、制約JSON、元manifest、Git履歴・branchesの移動・削除・上書きは行っていない。新規ファイル数は本報告・追加台帳のコミットで変わるため、常に監査時HEADと一緒に扱う。

## 3. RF-F003、RF-T005、パレートの照合

- 正式制約 [RF-F003](../data/constraints/formal/RF-F003.json) は [レジストリ](../data/constraints/registry.json) のactiveであり、[互換用design_constraints.json](../data/design_constraints.json)とバイト一致。
- 外部固定S2P：入力 `ad266111ba1dc2b92f235d39f4a647ff271050bc11941c217661dd299ee59945`、出力 `b3cfc861bc0c8221f49328598c9d7d0766a6e94e42e990b6a50f6c90bf9a84da` が正式RF条件の指定SHA-256と一致。
- [不変スナップショット](../data/pareto_snapshots/rf_t005_rf_f003_20261017.json)のRF-T005試験6候補／RF-F003正式4候補に対し、[派生24候補CSV](../data/catalog/phase2_candidate_catalog_20261017.csv)の条件区分とILが一致。元完全ベクトルのGit blob SHAも10/10一致。
- [報告器](../scripts/report_research_pareto.py)は**24候補・比較条件10グループ**を再生成。RF-T005と正式RF-F003は混ぜない。**RF-F003のIL≤0.30dBを達成した候補はない**。公称H2/H3≥35dBも未達。
- 保存済みRF-F003 4GJM候補のchip面積原記録誤記は、原ファイルを変更せず派生スナップショット・カタログの**6⅔**を参照。
- 既存RF-F002 EXP-017の28×7,001点独立MNA回帰もPhase 2 regressionで通過。ただしこれは**旧RF-F002**の保存結果であり、最新RF-F003候補を新たに全格子MNAで再計算したものではない。

## 4. EXP-047の旧manifestを非破壊的に整合

mainに保存された [EXP-047元manifest](../experiments/chatgpt_topology_search/runs/EXP-047/manifest.json)（Git blob `94973b5e5a9e9b0fcd3a3ad9ffd39ea4197475e0`）は、旧形式の**局所in-chat実行記録**であり、現在の標準事前予約・完全実行manifestの9必須項目を欠く。これがStep 1～4の全回帰CIを停止させた既存問題。

- [出典固定の互換overlay](../data/validation/exp047_legacy_manifest_adapter_20261017.json)と[限定アダプター](../src/lpf/legacy_manifest_adapter.py)を新設し、元Git blob SHA・RF-F003実効SHA・bands・固定S2P・記録済み局所探索・元候補JSONの存在を点検した。
- 索引用には`formal RF-F003 / full_lpf / partial / numerical screened / independent passed`を、旧[実験索引](../data/experiment_index.csv)の当時の状態として再現。 [実験証拠インベントリ](../data/experiment_evidence_inventory.csv)は**45件**に更新し、EXP-047の独自形式を`legacy_partial_noncanonical_manifest`で明記。
- **元manifestは不変。** 元コード実行SHA、乱数seed、環境、全候補の収束状態はnull・未確認とし、架空の値を記録しない。`validate_manifest`の一般的な厳格なスキーマ要求は緩和せず、原本は依然として標準manifestの完全条件を満たさない。
- 他のEXPにこの例外を自動適用しない。出典SHAが変われば検査は明示的に失敗する。

## 5. 歴史資料とGitHub-only保全

- mainに存在した56文書は [歴史目次](archive/README.md)、[手法目次](methods/README.md)、[運用目次](governance/README.md)から閲覧可能。実際の元文書パスは維持。
- 同一blob 34組・38追加pathは条件／run出典の役割が異なり、Git packの削減見込みに読み替えない。正式RF-F003互換コピーは特に保持。
- 旧46要レビュー資料は元blobが一致し、**46件すべて保全継続**。削除・移動の承認を得た資料は0件。
- GitHub Actionsの期限付きartifactは検証の補助に過ぎず、重要な監査記録はPRのGit追跡ファイルとして保存する。

## 6. 残る確認とマージ判断

**Step 5実行上の検証：完了。** ただし以下を「終わった」とはしない。

1. mainへの実際のPR #67～71の反映：**未承認・未マージ**。内容の重複したPRを無条件に5本ともマージせず、統合PR #71か順次マージかをレビューして選択する必要がある。
2. 古い46件の意味を踏まえた削除可否・ブランチ削除：**別の所有者承認が必要**。今回の処置は保全のみ。
3. 現行RF-F003の全候補に対する同一高密度格子・独立MNA、連続帯域の厳密極値、SRF/Q(f)、公差、EM/物理実測：**未実施・未保証**。
4. EXP-047の厳格な形式への移行は、実行当時のSHA・seedなど不明な情報を埋めない限り事実上の完全復旧ではない。今回の処置は明示的な旧形式互換である。
5. 数値の全域パレート最適性、正式のIL≤0.30dB、公称35dB、物理的な同時結合実現性：**未達・未証明**。

**研究Phase 2のまま。Phase 3移行を実施・許可していない。**
