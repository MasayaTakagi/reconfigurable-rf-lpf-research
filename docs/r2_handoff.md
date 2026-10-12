# R2 共通MNA・可変C対応：実装状況とCodex引き継ぎ

## 今回の実装範囲（このR2部分PR）

- \`src/lpf/configuration.py\`: 6設定のトポロジー不変性を確認し、resolved RF policyから可変Cの枝数、端点、Q、0–4pFを検証。既定はRF-F001（2対GND）で、RF-T001/T002は明示的なpolicy引数が必要。
- \`src/lpf/topology.py\`: RF-T002の非GND可変Cが単独の入力–出力直列経路にならないよう、**可変Cを除いた固定素子の非GNDグラフ**に迂回経路があるか判定。これは必要な構造条件であり、EM、周波数依存、実部品実装の検証ではない。
- \`experiments/matching_limit/instantiate_graph.py\`: 内部ノード対GND容量、3個容量、明示的な非GNDブリッジ、LQP02HV（Q25・0.4～27nH）/LQP02HQ（Q20・0.2～56nH）をモデル化。新規候補は \`require_explicit_series=True\` でlegacy \`LQP02\` ラベルを拒否可能。旧P4-AのラベルはあくまでHVの探索部分範囲として残す。
- 旧P4-Aモデルの変更には計算ソース指紋更新を伴うため、計算アルゴリズム版を \`v5-r2-core\` に更新。過去のCheckpointを誤って新モデルへ再開しない。
- R2検証テストはシリーズ境界・設定不変性・3種の可変C接続・不許可直列C・主/独立nodal計算比較・LPF-007/008の履歴数値再現を対象とする。旧候補JSON・正式RF-F001・試験RF-T001/T002の定義は変更しない。

## 今回未実施・未完成の機能（Codex引き継ぎ優先順）

1. **PR-B2b/R2-2探索アルファベット**：\`coverage_sampler.py\`、\`enumerate_grounded.py\`、\`p4_batch.py\`はまだ旧 \`LQP02\` HV限定、IN/OUTの2対GND C、0.4～12nHを使っている。共通モデルに対応する探索器側の候補生成、位置列挙、可変Cの最適化変数形状、各seriesの明示、面積セル範囲、実験パラメータ/マニフェスト連携が未実装。旧P4-Aの既定を勝手に3枝へ変更しない。
2. **PR-B3/R2-3追加検証**：\`src/lpf/independent.py\`は主MNAと枝接続行列を共有しない別のノードアドミタンス組立方式へ変更済み。さらに、別の枝電流拡張MNA、縮約の条件判定、検証周波数密度、磁気結合の物理妥当性の独立監査を強化する。候補の全密グリッド保証や測定精度は別工程。
3. **PR-B3/R2-4 EXP-015移植**：保存済みEXP-015回路の旧表現を共通モデルへ変換し、独立MNA・電力収支と比較。元の数値/モデル条件を保持し、RF-T002適合は解析・接続・H2/H3基準を個別に再判定する。LPF-007/008は旧条件の回帰であり、新正式条件への適合を自動認定しない。
4. **PR-B4/R2-5 Actions スモーク**：新モデルのジョブ固有CLIとcheckpoint互換ハッシュ、元のコードSHA、RF-ID、resolved policy hash、variable layout、数値環境、H2/H3閾値、網羅率を記録。失敗時Artifact収集/復元実機試験を行う。
5. **物理性**：結合配置、部品値、全L行列SPD、Q(f)、SRF、PCB/ICの実装資源は個別確認。新回路の性能改善・大規模探索は未実行。

## Codexに要求する検証

\`\`\`bash
python -m pip install -r requirements.txt
python scripts/audit_results.py
python scripts/experiment_manifests.py audit
python -m unittest discover -s tests -v
python scripts/verify_no_pcb_tunable_candidates.py
\`\`\`

完了はPRごとに最新HEADでのGitHub Actions成功、共通モデルと独立手法の一致、および証拠の保存により判断。研究はPhase 2を維持し、正式制約RF-F001、研究仮条件RF-T001/T002と全歴史的データは不変。有限探索を理論最適と呼ばない。
