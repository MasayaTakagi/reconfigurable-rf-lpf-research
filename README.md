# Reconfigurable RF LPF Research

**Phase 2（回路トポロジーと性能探索）進行中。Phase 3は明示承認まで停止。**

**初めてこのリポジトリで研究する場合は、[Phase 2研究・フォルダ運用ガイド](docs/research_workflow_ja.md)を最初に参照してください。** ChatGPT探索の作業場所、共通解析コード、自動探索の棲み分けと候補登録のルールを簡潔にまとめています。

## いまの最優先目標

**先行するChatGPT主導探索より優れた、現行RF制約内のfull-LPF回路を発見する。**

比較基準は、現在の仕様に適合する保存済み候補のうち最大ILが最小の[LPF-007](candidates/LPF-007.json)：6設定UL/DL最悪 **0.513168414dB**、UL高調波最小H2/H3 **35.069970/35.069996dB**（面積6、有限グリッド計算値、SLSQP未収束）。先に**35dB以上の減衰を維持してILを下げる**ことを目指し、長期的な公称目標は**IL≤0.30dB**。必須高調波減衰は30dB以上で、35dBは公称探索目標である。

6設定：B71 / B12 / B28 / B13+B14（共通設定）/ B26 / B8。入力50Ω、負荷60−j40Ω、面積≤6などの承認済み物理制約は維持する。最良数値解は大域最適性や実装性を証明しない。

## 2つの探索トラック

| 方式 | 役割 | 検証 |
|---|---|---|
| **ChatGPT主導の仮説探索** | RF回路理論からブリッジ、共振・反共振、低損失結合等の新構成を提案し、専用高速最適化器で探索 | 共通MNA・独立解析器で再評価。良好候補を体系探索へ供給 |
| **スクリプト主導の体系探索** | 宣言したノード・枝・素子・レイアウト・可変C接続範囲を生成し、コスト別に数値最適化・未探索部分を定量化 | 同じ評価指標・物理制約でAI案と公平に比較。良好構成は専用解析で深掘り |

**未解決の統合課題**：現行P4-Aは可変Cの接続先がIN/OUTに限定され、LPF-007/008が用いる内部トラップ節点の可変Cを汎用生成できない。これを共通モデルの優先改善項目とする。

**ChatGPTが新しく回路トポロジーを考案・最適化する際の作業先は、[`experiments/chatgpt_topology_search/`](experiments/chatgpt_topology_search/) に統一する。** 個別作業はその下の `runs/EXP-NNN/`。自動P4-Aは従来どおり `experiments/matching_limit/`。リポジトリ全体の役割は[フォルダ構成ガイド](docs/repository_layout.md)を参照。

探索方法の責務分担は[コード構成](docs/architecture.md)、具体的な実施順序は[Phase 2ロードマップ](docs/roadmap.md)、比較時の合否は[現行ベースライン](docs/baselines.md)を参照。

## 開発状況

- **G1 — GitHub Actions計算基盤：完了**。決定的シャーディング、チェックポイント、別runのArtifact復元、1/2シャードsmokeを実機で確認。[G1検証ログ](docs/g1_p4_sharding_validation_20261011.md) / [1シャード完了](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128578799) / [2シャード完了](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128871403)。
- **R0/R1 — 共通回路モデルへの統合：未完了**。[コード移行計画](docs/refactor_plan.md)。設計制約の変更ではない。
- **G2 — 数値解析／最適化高速化：未完了**。実測benchmarkから開始。
- **P4-A — 内部ノード最大4・固定枝最大8の探索：本格解析前**。既存smokeは最適化未収束であり、性能限界ではない。
- **Phase 3 — 停止中**。

## 仕様・コード・研究記録

| 場所 | 役割 |
|---|---|
| [`data/design_constraints.json`](data/design_constraints.json) / [`data/bands.csv`](data/bands.csv) | 物理制約の機械可読正本／周波数帯域 |
| [`docs/specification.md`](docs/specification.md), [`docs/evaluation.md`](docs/evaluation.md) | 設計条件と6設定UL/DL/H2/H3の評価 |
| [`src/lpf/`](src/lpf/) | MNA・独立解析・共通検証。最適化の共通化は移行中 |
| [`experiments/`](experiments/) | 日付付き解析、ChatGPT仮説探索結果、汎用P4-A実行コード |
| [`candidates/`](candidates/) / [`data/candidate_index.csv`](data/candidate_index.csv) | 候補定義と履歴・証拠索引 |
| [`scripts/`](scripts/) / [`tests/`](tests/) | 検証CLIと自動テスト |
| [`docs/decisions.md`](docs/decisions.md) | 設計・開発判断の履歴 |

## 実行入口

```bash
python -m pip install -r requirements.txt
python scripts/audit_results.py
python scripts/check_no_pcb_candidates_20261011.py
python scripts/verify_no_pcb_tunable_candidates.py
python -m unittest discover -s tests -v
```

P4-A実行は[手動GitHub Actions](.github/workflows/lpf-p4-a.yml)から実行する。push/PR時に大規模探索は自動起動しない。保存済み候補の再計算、有限メッシュでの確認、実際の最適化・収束、EM検証は**別の検証段階**である。

**注意**：旧CP07/CP11などは、現在の可変C枝数・結合上限等に適合しない歴史的参考値である。面積6の`matching_only`最良報告0.114837004dBは高調波条件なしの別目的であり、full-LPFの性能実績と混同しない。
