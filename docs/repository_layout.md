# リポジトリ構成・作業フォルダ（Phase 2）

本書はGitHubリポジトリの**フォルダごとの責務**と、ChatGPT／自動探索の正規の作業場所を定める。実際のプログラム実行結果と未実装の計画は区別する。

## フォルダ構成

```text
reconfigurable-rf-lpf-research/
├── .github/
│   └── workflows/                   # CI・手動GitHub Actions・長時間計算
├── src/
│   └── lpf/                         # 共通回路モデル・MNA・独立検証（最適化API移行中）
├── experiments/                     # 個別の回路探索・数値実験
│   ├── chatgpt_topology_search/     # ★ ChatGPT主導探索の唯一の新規標準作業場所
│   │   ├── README.md                # 作業規約・保存対象・昇格条件
│   │   ├── runs/
│   │   │   └── EXP-NNN/            # 新実験ごとの config/circuit/optimize/results/summary
│   │   └── templates/              # 実験設定・報告書の雛形
│   ├── matching_limit/             # 既存P4-A体系探索、shardingとresume
│   ├── matching_cost_20261010/     # 整合専用の過去の比較記録
│   ├── no_pcb_policy_update_20261011/  # LPF-005/006の探索履歴
│   └── no_pcb_tunable_shunt_20261011/  # LPF-007/008の探索履歴
├── candidates/                      # 検証済み/候補として昇格したLPF-xxx.json
├── data/                            # 設計制約、帯域、候補索引、保存された数値的証拠
├── docs/                            # 仕様、ロードマップ、方法、決定、比較基準
├── scripts/                         # 再利用するCLI、監査・再計算・Artifact集計
├── tests/                           # コード・解析・制約・成果物の回帰テスト
├── README.md                        # 研究概要と入口
└── requirements.txt                # Python依存関係
```

`runs/EXP-NNN/`は**作成する実験の例示パス**であり、未作成の実験が実施済みであることを意味しない。

## どこに何を保存するか

| 作業・成果 | 正式な保存先 | 誤配置を避ける理由 |
|---|---|---|
| ChatGPTが発案したトポロジーの試作 | [`experiments/chatgpt_topology_search/runs/`](../experiments/chatgpt_topology_search/runs/) | 独自の初期値・専用縮約最適化を隔離し、候補とは区別 |
| 自動生成グラフのP4-A数値探索 | [`experiments/matching_limit/`](../experiments/matching_limit/) | 現行のG1 checkpoints/workflowと整合させる |
| どの探索器も使う数学的な回路解析 | [`src/lpf/`](../src/lpf/) | 重複実装・計算条件の不一致を防ぐ |
| 検証済みの正式な回路候補 | [`candidates/`](../candidates/) と [候補索引](../data/candidate_index.csv) | 実験中の粗い暫定解と区別する |
| RF制約・周波数帯域 | [`data/design_constraints.json`](../data/design_constraints.json)、[`data/bands.csv`](../data/bands.csv) | 設計仕様の正本を一元化 |
| 開発の優先順位 | [`docs/roadmap.md`](roadmap.md) | 古い研究計画との混在を防ぐ |
| 共通検証CLIやテスト | [`scripts/`](../scripts/)、[`tests/`](../tests/) | 複数の実験から再利用可能にする |
| GitHub Actionsの実行定義 | [`.github/workflows/`](../.github/workflows/) | 長時間処理と短いPR CIを分離する |

## ChatGPT探索を始めるとき

1. 実験ID `EXP-NNN`を採番し、`experiments/chatgpt_topology_search/runs/EXP-NNN/`を作る。
2. [実験設定テンプレート](../experiments/chatgpt_topology_search/templates/config.example.json)をもとに`config.json`を用意し、RF条件の参照パス・モード・seed・予算・SHAを記録する。
3. `circuit.json`に回路グラフ、可変Cの接続先、チップ物理列と結合係数を記録し、構造固有の`optimize.py`を必要に応じて追加する。
4. `results.json`と`summary.md`へ**実測済み**の結果のみ記入し、共通MNA等で独立再計算する。
5. LPF-007との35dB減衰同条件比較に価値があれば`candidates/`への候補昇格PRを作成する。

新規ChatGPT探索に`experiments/no_pcb_tunable_shunt_20261011/`等の**過去記録を上書きしない**。物理制約ファイルを変えない。共通解析器への昇格はテストと別PRを通す。

## 変更・再編が未完了の部分

現在の`src/lpf/optimize.py`はプレースホルダで、汎用最適化器は主として`experiments/matching_limit/`にある。またP4-Aの可変C接続点はIN/OUT固定のため、LPF-007/008の内部トラップCを自動探索へ直接投入できない。これは[リファクタ計画](refactor_plan.md)のR0/R1で解決する。フォルダを作っただけでモデル一般化・コード移動が完了したとは扱わない。

**G1は実機検証済み、研究全体はPhase 2継続、Phase 3は停止中。**
