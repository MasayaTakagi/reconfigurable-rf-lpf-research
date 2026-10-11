# Phase 2 研究・フォルダ運用ガイド

> **この文書を最初に読む**：ChatGPTによる回路考案と、自動トポロジー探索を並行して進めるための保存先・手順・判断基準。2026-10-11制定。  
> **研究はPhase 2を継続**。Phase 3はユーザーの明示承認まで停止。旧Phase 4以降の計画は使用しない。

## まず結論：どこで作業するか

- **ChatGPTが新しい回路を発案する場合** → [`experiments/chatgpt_topology_search/runs/EXP-NNN/`](../experiments/chatgpt_topology_search/runs/) に**実験単位**で保存。
- **プログラムがトポロジーを体系的に生成する場合** → 当面は [`experiments/matching_limit/`](../experiments/matching_limit/) のP4-A探索基盤を使う。
- **どちらも使う解析・最適化の共通機能** → [`src/lpf/`](../src/lpf/) に集約する（汎用最適化APIなどは**移行中**）。
- **独立検証した有望な回路の正式記録** → [`candidates/`](../candidates/) に候補IDを付け、[候補索引](../data/candidate_index.csv)も更新。
- **設計条件** → [`data/design_constraints.json`](../data/design_constraints.json)、[帯域表](../data/bands.csv)が正本。実験ごとに勝手に変えない。

## フォルダの役割一覧

| 場所 | 置くもの | 置かないもの |
|---|---|---|
| [`experiments/chatgpt_topology_search/`](../experiments/chatgpt_topology_search/) | ChatGPTの回路仮説、実験別の専用最適化コード、途中・確定結果 | 全トポロジー共通の解析器 |
| [`experiments/matching_limit/`](../experiments/matching_limit/) | 自動グラフ生成、P4-A実験、分割計算・再開の現行コード | ChatGPTの独立した新規実験 |
| [`src/lpf/`](../src/lpf/) | MNA、独立解析、6設定評価、制約チェック、今後の共通最適化API | 一度しか使わない実験固有の仮説 |
| [`candidates/`](../candidates/) | 有望候補の回路定義、素子値、検証状況 | 未実行の仮説や根拠のない性能値 |
| [`data/`](../data/) | RF仕様の正本、帯域、候補索引、保存すべき計算データ | 実験ごとの一時スクリプト |
| [`docs/`](./) | 仕様、ロードマップ、設計判断、解析方法、比較ルール | 使い捨ての計算出力 |
| [`scripts/`](../scripts/)・[`tests/`](../tests/) | 共通CLI・再計算・監査、単体/回帰テスト | 特定実験だけの最適化ロジック |
| [`.github/workflows/`](../.github/workflows/) | GitHub Actionsの自動CI・手動の計算ジョブ | RF回路の候補データそのもの |

これまでの実験フォルダ（`no_pcb_policy_update_20261011/`、`no_pcb_tunable_shunt_20261011/`など）は**履歴としてそのまま保存**する。既存パスの移動・削除によって検証資料への参照を壊さない。

## ChatGPT探索の始め方（標準手順）

新しい回路仮説を一つ調べるときは、`experiments/chatgpt_topology_search/runs/EXP-001/`のように**新しい実験ID**を割り当てる。次の実験は`EXP-002`というように進め、番号を再利用しない。[設定・報告の雛形](../experiments/chatgpt_topology_search/templates/)を使用する。

```text
experiments/chatgpt_topology_search/
├── README.md                 作業ルール
├── templates/                実験設定と報告書の雛形
└── runs/
    └── EXP-NNN/              新しい実験ごとに作成するフォルダ（例）
        ├── config.json       制約、探索目的、seed、計算予算
        ├── circuit.json      仮の回路接続・素子値・結合・6設定の可変C
        ├── optimize.py       このトポロジー専用の最適化（必要な場合）
        ├── results.json      実際に実行した計算結果だけ
        └── summary.md        狙い、検証、比較、次の改善案
```

`EXP-NNN/`は**作成時の例**であり、全ファイルが既に存在することを意味しない。専用最適化器を使わない場合、`optimize.py`は必須ではない。

**実験の流れ**：① 回路仮説を記録 → ② `full_lpf`または`matching_only`と制約・計算条件を明記 → ③ 専用または共通ソルバで数値探索 → ④ 共通MNAと独立した方程式で6設定を再評価 → ⑤ LPF-007と同条件で比較 → ⑥ 再現可能な結果を保存し、必要なら正式候補へ昇格。

GitHub上のこのパスは**研究成果物の保存場所**であり、ChatGPTの一時Python実行環境に自動的にマウントされる作業ディレクトリではない。計算に用いたコミットSHA・実行run IDを記録し、必要な成果をGitHubのブランチ／PRへ保存する。

## ChatGPT探索と自動探索の協力関係

| ChatGPT主導の探索 | スクリプト主導の体系探索 |
|---|---|
| RF理論から新しい回路を発案する | 宣言したノード・枝・素子・可変C位置・磁気結合の範囲から回路を生成する |
| 構造に特化した高速ソルバで深く最適化する | 多数の回路を同条件の予算で選別・最適化する |
| 得た良好解・初期値を自動探索へ渡す | 有望な構造をChatGPT側の専用最適化へ渡す |

両方式の共通点は、**同じRF物理制約・同じ最悪IL/H2/H3評価・同じ独立検証を受けること**。片方で見つからない回路を「性能が悪い」とみなしてはいけない。自動探索では、生成した候補だけでなく、未生成・未実行・失敗した範囲も記録する。

**現在の未解決課題**：P4-Aの既定の可変C接続点はIN/OUTに固定されているが、先行するLPF-007/008では内部LCトラップ節点に可変Cがある。R0/R1でモデルを一般化し、両方式で同一候補を再現できるようにする。[リファクタ計画](refactor_plan.md)。

## 成果として認める条件

当面の比較基準は、ChatGPT発案の[LPF-007](../candidates/LPF-007.json)：現行制約の`full_lpf`、**最大IL 0.513168414 dB**、H2/H3最小約35.07 dB（保存済み有限周波数グリッド、最適化未収束）。

最初の目標は、**H2/H3ともに35 dB以上を維持し、6設定UL/DL全域での最悪ILをLPF-007より改善すること**。最終的な公称数値目標は最大IL≤0.30 dB、必須高調波減衰は30 dB以上。

結果を評価・候補登録する際は、少なくとも以下を残す。

- 回路グラフ、物理チップ列、符号付き結合、6設定で共通の固定素子、各設定の2枝以内の可変C
- 評価モード（`matching_only` / `full_lpf`）、最大IL、H2/H3の最小減衰、最悪周波数、周波数グリッド
- 計算条件・seed・コードSHA・依存バージョン・実行時間・評価回数・最適化収束状態
- SPD・受動性・電力収支・独立MNA照合・物理的実装可能性の確認状況と未確認点

`matching_only`の低ILはH2/H3を満たしたLPF実績ではない。**有限グリッドでの数値的最良候補は、大域最適値や連続帯域・EM・実装可能性の保証ではない**。候補登録は製作承認を意味しない。

## 次に参照する文書

- [Phase 2ロードマップ](roadmap.md)：今後の開発順序と完了条件
- [フォルダ構成の詳細](repository_layout.md)：各保存先の細かなルール
- [共通コードと探索方式の責務](architecture.md)：ライブラリ化の方針
- [ChatGPT探索フォルダの詳細規約](../experiments/chatgpt_topology_search/README.md)：実験ファイル別の保存内容
- [比較基準](baselines.md)：LPF-007を超えたと判定する条件

**現在の状態**：G1（計算・再開基盤）は実機確認済み。R0/R1（候補と共通回路モデルの相互運用）、G2（高速化）、P4-A本格探索は今後の作業。Phase 2を継続する。
