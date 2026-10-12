# ローカルP4-A実行手順（WSL2 / uv）

## 目的・適用範囲

`scripts/local_p4.py` は既存の `experiments/matching_limit/p4_batch.py` をシャード別の独立プロセスとして起動・監視する実行マネージャーです。回路解析、最適化、グラフ生成の数値実装は複製せず、既存の決定的シャード割当て、原子的チェックポイント、再開検査、`aggregate_p4_a_shards.py` の集計を利用します。

**P4-Aは `matching_only` 探索です。H2/H3制約は最適化目的に含まず、`full_lpf` の合格やRF性能達成を意味しません。** 正式条件RF-F001と試験条件RF-T001/T002は、別々の制約ID・実効SHA-256を持つ別ジョブです。RF-T001/T002を使う場合はCLIでIDを明示してください。既存P4-AはRF-T003を受け付けません。Phase 2を維持し、Phase 3は停止します。

## uv環境

WSL2でuvが未導入の場合は公式インストーラーを使います（Actionsではuv `0.12.23`を固定）。

```bash
curl -LsSf https://astral.sh/uv/0.12.23/install.sh | sh
source "$HOME/.local/bin/env"  # PATHがまだ反映されていないシェルの場合
uv --version
```

Python 3.12環境を用意し、追跡済みlockから同期します。

```bash
cd ~/src/reconfigurable-rf-lpf-research
uv python install 3.12
uv sync --frozen
uv run --frozen python --version
uv run --frozen python -m unittest discover -s tests -v
```

`pyproject.toml` が依存条件の正本、`uv.lock` がPython 3.12の解決済みバージョン正本です。`requirements.txt` は既存ツール・後方互換用の条件ミラーで、GitHub Actionsの科学計算ジョブも `uv sync --frozen` を使います。lock更新時は `uv lock` を使い、依存条件の変更をレビューしてから `uv.lock` をコミットしてください。

## 計画確認（計算しない）

`plan` は出力ディレクトリや計算結果を作らず、選択グラフ・決定的なシャード割当て・候補数・制約ハッシュ・P4互換性ハッシュをJSONで表示します。

```bash
uv run --frozen python scripts/local_p4.py plan \
  --root results/local-runs \
  --constraint-id RF-F001 --series-mode HV \
  --attempts 1 --per-bin 1 --starts 1 --layouts 1 --iterations 1 \
  --coarse-points 2 --validation-points 3 \
  --max-variable-layouts 2 --max-topology-graphs 4 \
  --seed 20261013 --shard-count 4 --workers 2
```

デフォルトも最大4トポロジーグラフ・1反復の短いスモーク設定です。大きな探索へ拡張する前に、計画に表示されるグラフ数・候補数・制約IDを確認してください。`plan` は実行を開始しません。

## 新規実行

次は上記と同じ小規模条件で新規ジョブを作る例です。`run` は計算を開始します。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
uv run --frozen python scripts/local_p4.py run \
  --root results/local-runs \
  --constraint-id RF-F001 --series-mode HV \
  --attempts 1 --per-bin 1 --starts 1 --layouts 1 --iterations 1 \
  --coarse-points 2 --validation-points 3 \
  --max-variable-layouts 2 --max-topology-graphs 4 \
  --seed 20261013 --shard-count 4 --workers 2 \
  --max-graphs-per-batch 1 --max-batch-seconds 600 \
  --memory-min-free-mib 1536 --monitor-interval 5 \
  --memory-stall-timeout 300 --max-runtime 0
```

各workerプロセスの `OPENBLAS_NUM_THREADS` / `OMP_NUM_THREADS` / `MKL_NUM_THREADS` はマネージャーが `1` に固定します。初期同時実行数は2、許容最大は4です。`workers` は `shard-count` 以下にしてください。シャード数とseedを維持したままworker数だけ変えても、グラフ→シャード割当ては変わりません。

P4-Aで指定できる探索設定は制約ID、系列モード、試行サンプル数、ノード／面積ビンごとの候補数、開始値数、結合レイアウト数、可変Cレイアウト上限、SLSQP反復数、粗・検証周波数点数、seed、最大グラフ数、シャード数です。最大グラフバッチ数・バッチ時間はチェックポイントを確定する実行単位です。チェックポイントは既存実装により候補・グラフ単位で原子的に更新されます。

`--max-runtime` は1回のmanager起動あたりの秒数で、`0` は無制限です。利用可能RAMが `--memory-min-free-mib` 未満なら新しいworkerの起動を止め、稼働中workerの終了後に再評価します。低メモリ状態が `--memory-stall-timeout` 続いた場合は新規起動をやめ、稼働中workerへSIGTERMを送り安全停止します。既定の強制終了はSIGTERM後120秒まで待ってからの最終手段です。`--force-kill-after 0` で強制終了を無効化できます。swapを前提にworker数を増やす運用はしないでください。

## 状態・停止・再開

run出力は一意なUTC時刻＋乱数IDのディレクトリに作られ、既存runを上書きしません。

```text
results/local-runs/<run-id>/
  manifest.json
  status.json
  aggregate.json
  manager.lock
  logs/manager.jsonl
  logs/monitor.jsonl
  shards/shard-N/
    checkpoint.json
    result.json
    worker.log
    failure.json                 # worker異常時のみ
    failure-history/             # 再開時の旧failure.jsonを保管
```

進捗確認：

```bash
uv run --frozen python scripts/local_p4.py status <run-id> --root results/local-runs
```

Ctrl-CまたはSIGTERMでmanagerは稼働workerへSIGTERMを送り、P4-A側の割込み処理でチェックポイントを保存してから停止します。停止後の再開：

```bash
uv run --frozen python scripts/local_p4.py resume <run-id> \
  --root results/local-runs --workers 2
```

互換性が確認できる限り、再開時にworker数を変えられます。`uv.lock`、Python/NumPy/SciPy/BLAS構成、CPUモデル、RF制約、周波数帯域、ソースファイル指紋、P4設定・シャード割当てを照合します。不一致、壊れたJSON、設定違いの場合は初期化せずエラー終了します。完了シャードはスキップし、部分・中断チェックポイントは既存 `--resume` 経路で復元します。1 runへの複数manager同時書込みはOSファイルロックで拒否します。

## 集計

```bash
uv run --frozen python scripts/local_p4.py aggregate <run-id> --root results/local-runs
```

集計は既存のシャード検査器を使用し、重複グラフ、欠落シャード、設定混在、破損、失敗を隠しません。状態は `completed` / `in_progress` / `interrupted` / `failed` / `incompatible` / `corrupt` / `not_run` のいずれかです。未完了ジョブを `overall_complete=true` にはしません。`aggregate.json` には計画・完了・収束・非収束・失敗・未実行の最適化候補数を別々に記録し、最適化非収束はジョブ失敗と区別します。

## 監視・ログ・再現情報

`manifest.json` はrun/終了時刻、Git SHAと作業ツリー状態、計算コード指紋、RF制約IDと実効SHA、P4設定、`uv.lock` SHA、uv/Python/NumPy/SciPy/BLAS、CPU、開始時利用可能RAM、seed、シャード数・worker数、終了コード、経過時間、ピークworker RSS、CPU・メモリ監視値、最適化結果件数を保存します。`logs/monitor.jsonl` は約5秒間隔（設定可能）でホストメモリ・CPU・各worker RSS/CPU・プロセス数を記録します。

`status.json` は原子的な更新で状態とシャード進捗を表示します。`manager.lock` はrunの排他ロック用です。異常・設定不一致のときは元チェックポイントを保持し、削除・別条件への転用をしません。

## 結果の保管・GitHubへの登録方針

`results/` は `.gitignore` 対象です。大きな一時チェックポイント、ログ、未レビュー探索出力をそのままコミットしないでください。候補を研究記録へ昇格する場合は、制約IDと実効ハッシュ、コードSHA、探索範囲、seed、最適化収束状態、独立MNA・高密度グリッド検証、未検証の物理項目を整理し、選別した証拠を専用実験ディレクトリへキュレーションします。raw結果・チェックポイントの長期保存が必要な場合は、ローカルバックアップまたは承認済みArtifact保管先を用い、Git履歴を無用に肥大化させないでください。

GitHub Actionsの監査・回帰CIはuv lock環境で維持します。P4-Aおよび既存の手動探索workflowも削除しておらず、比較・互換検証のため引き続き利用可能です。CI/スモークの成功は大規模探索やRF性能達成を意味しません。
