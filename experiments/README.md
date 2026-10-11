# 実験管理（Phase 2）

**新規実験の始め方と保存場所**は[研究・フォルダ運用ガイド](../docs/research_workflow_ja.md)を参照してください。

`experiments/`は**実験の再現設定・結果・議論を保存する場所**であり、複数の研究に共通する解析器や最適化ロジックを増殖させる場所ではない。共通ロジックはテストを付けて`src/lpf/`へ移し、CLIは`scripts/`で薄く保つ（[移行計画](../docs/refactor_plan.md)）。

## 新しい探索の公式作業場所

- **ChatGPT主導の回路仮説・専用高速最適化**： [`chatgpt_topology_search/`](chatgpt_topology_search/) を新規作業の正規ディレクトリとする。各実験は `chatgpt_topology_search/runs/EXP-NNN/` に条件、暫定回路、専用コード、実測結果、summaryを保存。
- **スクリプト主導のP4-A体系探索**：当面は[`matching_limit/`](matching_limit/) で既存G1計算・復旧スクリプトを運用する。AI側から良好解を受け取る共通インターフェースはR0/R1以降に整備する。
- **共通の解析・検証ロジック**は[`src/lpf/`](../src/lpf/) に置き、[`candidates/`](../candidates/)は昇格済み候補のみ。詳細は[フォルダ構成](../docs/repository_layout.md)。

## 既存記録の扱い

- `matching_limit/`：現在のP4-Aグラフ探索・選別・最適化スクリプトとP4関連の過去チェックポイント。**移行中の実行コード**であり、全クラスの網羅・連続最適化の大域性を主張しない。
- `matching_cost_20261010/`：整合専用・面積別の数値参考値。full-LPFと混ぜない。
- `no_pcb_policy_update_20261011/`：LPF-005/006の現行仕様対応・検証記録。
- `no_pcb_tunable_shunt_20261011/`：ChatGPT主導トラップ回路LPF-007/008の探索・有限グリッド検証記録。

既存ファイルの移動・削除で候補索引や証拠パスを壊さない。実験コードの元の依存バージョンが記録されていない場合は、その事実を明記する。

## 今後の実験の保存単位

新規のChatGPT主導実験は`experiments/chatgpt_topology_search/runs/EXP-NNN/`に、その他の研究実験は必要に応じて`experiments/EXP-NNN/`に`config.json`、`results.json`、`summary.md`を作り、必要なコードSHA・seed・仕様ID・探索起源・モード（`matching_only`/`full_lpf`）・実行run ID・計算資源・収束状態・独立検証状態を含める。大きい探索のチェックポイントはGitHub Actions Artifactsから追跡し、重要な結果・マニフェストだけをGitへ昇格する。

日付付き既存実験を無理に`EXP-NNN`へ改名せず、新規命名規則と過去研究の両方を文書で扱う。
