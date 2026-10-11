# ChatGPT探索の実験ディレクトリ

**新規のChatGPT主導トポロジー探索を開始する際は、この`runs/`直下に`EXP-NNN/`を作成します。**

例: `experiments/chatgpt_topology_search/runs/EXP-001/`

1実験＝1つの回路仮説または明示的に定義されたトポロジー群。以下を原則として管理します。

- `config.json`: 実験ID、`origin=ai_hypothesis`、目的（`matching_only`か`full_lpf`）、ソースSHA、seed、最適化条件、計算予算
- `circuit.json`: 暫定回路のグラフ接続と固定・可変素子、配置・結合係数
- `optimize.py`: 特定構造に必要な専用解析／最適化器（不要なら作らない）
- `results.json`: **実際の実行結果だけ**。未実行・未収束・検証失敗の区別が必要
- `summary.md`: 仮説、図やトポロジー、LPF-007との同条件比較、検証範囲、今後の課題

`../templates/`の雛形を利用してください。`circuit.json`等のスキーマは共通モデル整備（R0/R1）の進行に合わせて確定するため、未実装の共通読込APIがあるとは主張しないでください。

正式に昇格した候補は`../../../../candidates/`に新IDで保存し、候補索引も更新します。旧実験ファイルは移動せず保存します。
