# Reconfigurable low-loss RF LPF — external review package

**開発状況:** Phase 2（回路トポロジー／理論性能の探索中） | **基準日:** 2026-10-10 | **Phase 3: ユーザー承認まで停止**

[English overview](README.en.md) · [設計仕様](docs/01_requirements_ja.md) · [部品・面積コストとC配置の新定義](docs/11_component_cost_topology_rules_ja.md) · [新仕様での整合専用コスト–IL探索](docs/12_matching_cost_frontier_ja.md) · [開発履歴](docs/02_history_ja.md) · [チェックポイント一覧](docs/09_design_checkpoints_ja.md) · [実装候補](docs/10_implementation_shortlist_ja.md) · [結果と証拠](docs/03_results_ja.md) · [ロードマップ](docs/05_roadmap_ja.md) · [外部レビュー依頼](docs/06_review_request_ja.md) · [再現手順](docs/07_reproduction_ja.md)

## プロジェクト目標

B71 / B12 / B28 / B13+B14 / B26 / B8 の**6設定**を1つのRFフィルタでカバーする。各設定では当該バンドの **UL・DL を低損失で通過**させ、**ULの2倍波・3倍波の全帯域**を減衰させる。共通の固定インダクタと相互結合を使い、最終的にはスイッチドキャパシタで設定を切り替える。

- **必須高調波阻止**: H2 / H3 ともに **30 dB以上**。Phase 2の主な公称探索目標は **35 dB以上**。
- **公称ILの目標**: 6設定のUL/DL全体における最大値 **0.30 dB以下**（現在の設計探索目標）。
- **基準モデル**: 入力50 Ω、出力60−j40 Ω（全周波数で一定）、LQP02HV相当のチップLは **Q=25**、内層PCB-Lは **Q=12**、Cは **Q=80**。
- **新しいチップ面積コスト（2026-10-10合意）**: LQP02=1、LQP01（Q15）=2/3、LQW04=3、GJM01固定C=2/3単位。PCB-LとIC可変Cはチップ占有面積に加算せず、数量・リソースを別管理。**面積予算4単位は新しいコスト–IL探索の固定上限にしない。** PCB-Lは原則3本以下、IC可変Cは原則2枝以下・各枝0〜4pF・対GNDのみ。GJM01は各100pF以下で全設定固定、可変Cとの並列接続を許可。IC可変Cのシリーズ配置は別途承認が必要。詳細は[仕様書](docs/11_component_cost_topology_rules_ja.md)。
- **現在の探索**: Qと理想集中定数のモデルを維持し、チップL–PCB-L結合は \(|k|\leq0.03\)、PCB-L同士は受動性条件を満たす範囲で理論上の強結合まで検討。

## 結果の要約（**数値探索値、証明値ではない**）

**重要：下表は新しいGJM01固定C／IC可変C≤4pF×2枝／PCB-L≤3本の制約で再最適化した結果ではない。** 従来条件下の研究履歴として保持し、今後のコスト–IL比較では新仕様を満たす候補のみを採用する。

| モデル／設計段階 | 6設定最大IL | H2/H3最小減衰 | 実装上の留意点 |
|---|---:|---:|---|
| 4チップL＋4C・3段直列共振器（結合制約付き） | 約 **0.3289 dB** | 約 **35.05 dB** | チップLのみ、基準候補 |
| 4チップL＋3内層PCB-L＋7C・弱チップ–PCB結合 | 約 **0.3243 dB** | 約 **35.05 dB** | Q12のPCB-L、弱結合のみ |
| 同等素子数・PCB-L同士の結合も許可 | 約 **0.3234 dB** | 約 **35.05 dB** | PCB-L間の複数結合の実現性未確認 |
| ほぼ完全結合した3個のPCB-Lを直列協調接続した理論候補 | **0.2952 dB** | **35.10 dB** | **PCB–PCB \(k=0.98\) が必要：理論候補であり実装未検証** |

最終行は従来の3本独立PCB枝とは異なるトポロジーであり、3つのPCB-L（各約0.708 nH、Q12）を同極性・直列接続することで、相互インダクタンスによる実効インダクタンスと実効Q向上を利用する。独立した7巻線節点解析との照合は実施済み。ただし0.98という結合は極めて強く、**再現性・必要面積・他導体への寄生・工差・大信号特性は未評価**。結果を採用済み実装回路として扱ってはならない。

> **重要：** ここに列挙した値は理想化したL/C/Qモデルによる数値的な成立解です。全トポロジーの大域最良、周波数の連続全域での厳密保証、物理試作性能、量産歩留まりを意味しません。また、村田の公表公称Q値は設計根拠に使用していません。

## 閲覧ガイド

| 目的 | 読むファイル |
|---|---|
| 仕様とバンド定義 | [`docs/01_requirements_ja.md`](docs/01_requirements_ja.md), [`data/bands.csv`](data/bands.csv) |
| 新しい部品の寸法・コストと可変C枝数の制約 | [`docs/11_component_cost_topology_rules_ja.md`](docs/11_component_cost_topology_rules_ja.md), [`data/design_constraints_20261010.json`](data/design_constraints_20261010.json) |
| 途中で残した設計チェックポイント（全段階） | [`docs/09_design_checkpoints_ja.md`](docs/09_design_checkpoints_ja.md), [`data/design_checkpoints.csv`](data/design_checkpoints.csv) |\n| 実装に残す構成と試作前のゲート | [`docs/10_implementation_shortlist_ja.md`](docs/10_implementation_shortlist_ja.md), [`data/implementation_shortlist.csv`](data/implementation_shortlist.csv) |\n| 何を試したか／判断履歴 | [`docs/02_history_ja.md`](docs/02_history_ja.md), [`docs/08_decisions_ja.md`](docs/08_decisions_ja.md) |
| 各数値の根拠と信頼度 | [`docs/03_results_ja.md`](docs/03_results_ja.md), [`data/evidence_register.csv`](data/evidence_register.csv) |
| 回路・Qモデル／相互結合／IL定義 | [`docs/04_model_ja.md`](docs/04_model_ja.md) |
| 未解決課題とマイルストーン | [`docs/05_roadmap_ja.md`](docs/05_roadmap_ja.md) |
| 外部レビュワーに検証してほしい内容 | [`docs/06_review_request_ja.md`](docs/06_review_request_ja.md), [Issue templates](.github/ISSUE_TEMPLATE/) |
| 再計算／各実験のスクリプト | [`docs/07_reproduction_ja.md`](docs/07_reproduction_ja.md), [`experiments/`](experiments/) |
| 元の計算アーカイブ一式（履歴の保全） | [`history/original-analysis/`](history/original-analysis/) |

## 簡易チェック

```bash
python scripts/audit_results.py
python -m unittest discover -s tests -v
```

追加依存（NumPy / SciPy / Numba）を使用するフル再計算は [`docs/07_reproduction_ja.md`](docs/07_reproduction_ja.md) を参照。`experiments/` には履歴中に作成したスクリプト・データのスナップショットを同梱し、再現性改善の余地もレビュー対象にしている。

## 開発フェーズ

- **Phase 1–2:** 相互結合・トポロジー・内層PCB-Lの理論探索が進行中。候補解の独立検証と比較条件の整理を継続。
- **Phase 3:** スイッチドCのbit数・容量コード・寄生モデル。**承認があるまで着手しない。**
- **Phase 4–7:** 公差ロバスト性、大信号、EM／実装、試作、確証付き最適性検証。

## レビューと利用上の注意

[CONTRIBUTING.md](CONTRIBUTING.md) に従い、仮定・モデル・テストを添えてIssueまたはPRを作成してください。**外部レビュワーからの意見は、性能達成の断定ではなく反証可能な検証事項として扱います。** コード・図表のライセンスは所有者の決定待ちです（[`LICENSE-STATUS.md`](LICENSE-STATUS.md)）。
