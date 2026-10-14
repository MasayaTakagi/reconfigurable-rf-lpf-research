# Full-LPF専用ローカル探索マネージャー（Phase 2 / RF-F002）

## 目的と境界

`scripts/local_full_lpf.py` は、既存の `scripts/local_p4.py` と `experiments/matching_limit/p4_batch.py` を置き換えず、独立した `full_lpf` 目的専用のbounded batch runnerです。P4-Aの `matching_only` 出力・チェックポイント形式・最適化目的を変更しません。

このrunnerは**正式RF-F002だけ**を受け付けます。RF-T003/RF-T004 seedを使う場合も初期値に限り、実行条件はRF-F002です。`matching_only`、trial条件、3本以上の独立可変C、RF制約の変更は拒否します。Phase 2の局所最適化用であり、連続帯域証明・global optimum・物理実装検証ではありません。

## 1. Config形式

`plan`へ渡すJSONに、最適化条件と独立した初期値taskを明示します。`graph[1]`の枝順と`initial_base_values`の固定部品値の順は一致させます。その後ろに6設定×可変C枝数のC値を設定順で連結します。インダクタ行列は固定枝のうちL枝だけの順序、`physical_order`も同じL枝インデックスを使います。

以下は機能スモーク用の**小さな例**です。性能探索の推奨トポロジーや有望回路を意味しません。

```json
{
  "constraint_id": "RF-F002",
  "objective": "full_lpf",
  "optimization": {
    "harmonic_targets_db": [30.0, 35.0],
    "maxiter_per_stage": 120,
    "ftol": 1e-8,
    "scale_design_variables": true,
    "passband_points": 9,
    "stopband_points": 9,
    "max_attempts": 2
  },
  "tasks": [
    {
      "seed_label": "smoke-start-1",
      "graph": [3, [[1, 2, "LQP02HV"]]],
      "variable_layout": {
        "edges": [[1, 0], [2, 0]],
        "roles": ["shunt_to_ground", "shunt_to_ground"]
      },
      "physical_order": [0],
      "initial_coupling": [[1.0]],
      "initial_base_values": [2.0, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4,
                               0.4, 0.4, 0.4, 0.4, 0.4, 0.4]
    }
  ]
}
```

`plan`時にグラフ・枝数・部品/可変C/結合の範囲、初期値、RF-F002 fingerprintを検査します。タスクの素子値は **L nH / 固定C pF / 6設定の可変C pF** です。config内で`effective_constraint_sha256`を指定する場合は、台帳から解決したRF-F002 SHA-256と完全一致させます。`scale_design_variables`はJSON booleanで、省略時は`true`です。`false`は物理設計単位をそのままSLSQPへ渡す**比較用ablation**であり、推奨設定ではありません。結果の`solver_parameterization`に実際の条件を記録します。

manager/`FullLPFProblem`が使うgrounded graphの端子規約は **ground=0, source=1, load=2** です。過去の保存候補は別のnode番号（例: output=3）を使うことがあるため、保存edge番号をそのままtaskへコピーしてはいけません。`scripts/full_lpf_checkpoint_import.py`は端子を正規化してwarm-start taskを生成します。import後は21点/segmentで保存チェックポイントのIL/H2/H3を再現する回帰テストを通し、枝順・固定部品・可変C・結合行列を照合してからoptimizerを実行します。seedは初期値に限り、全出力を現在のRF-F002で再評価します。

### Topology / start重複排除

runnerは順序に依存しないトポロジーフィンガープリントを計算します。同じトポロジーの別初期値はmulti-startとして許可し、同一トポロジー・同一初期値（物理列/結合/設定別Cを含む）の重複は`plan`時に拒否します。結果にはtask IDとtopology SHAを残し、集計時にもtask ID重複・欠落を検査します。トポロジー列挙器そのものはこのmanagerの範囲外であり、入力configが宣言した有限集合を超える網羅は主張しません。

## 2. Plan / bounded run / status / resume / aggregate

`uv sync --frozen`後、`results/full-lpf/`のようなGit管理外の専用run rootを使います。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
uv run --frozen python scripts/local_full_lpf.py plan \
  --config results/configs/full-lpf-smoke.json \
  --run-dir results/full-lpf/<run-id>

# 最初は2worker以下、合計最大2 start、最大実行時間300秒で短く試す
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
uv run --frozen python scripts/local_full_lpf.py run \
  --run-dir results/full-lpf/<run-id> --workers 2 \
  --max-runtime-seconds 300 --max-tasks 2 \
  --task-timeout-seconds 600 --min-free-mib 1536

uv run --frozen python scripts/local_full_lpf.py status \
  --run-dir results/full-lpf/<run-id>

# 中断後の再開は同じrun directoryに明示resumeする
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
uv run --frozen python scripts/local_full_lpf.py run \
  --run-dir results/full-lpf/<run-id> --workers 2 --resume \
  --max-runtime-seconds 300 --max-tasks 2 \
  --task-timeout-seconds 600 --min-free-mib 1536

uv run --frozen python scripts/local_full_lpf.py aggregate \
  --run-dir results/full-lpf/<run-id>
```

上限は同時worker 2、1回あたり20 start、manager wall-time 3600秒、worker timeout 1800秒、最適化最大1000 iteration/stageです。既定RAM gateは1.5 GiBで、これ未満では新しいworkerを開始しません。workerのOpenBLAS/OMP/MKL/NumExpr threadはすべて1です。低メモリ時にswapを前提として並列数を上げないでください。時間制限で停止した現在のtaskは途中のSLSQP状態ではなく**記録済み初期値から再実行**し、完了済みtaskはatomic resultを再利用します。各taskは`max_attempts`で再試行回数を制限します。

## 3. Checkpoint互換性・異常停止・ロック

`manifest.json`はconfig SHA、実効RF-F002 SHA、bands SHA、source file hashes、uv.lock SHA、Python/NumPy/SciPy、CPU/RAM、task/topology数、worker thread設定を記録します。`status.json`はatomic replaceで更新し、taskごとのpending/running/completed/failed、attempt数、worker PID、結果hashを保存します。途中でconfig/solver/MNA/RF/帯域/環境固定ファイルのSHAが変わったら再開を拒否します。実行後作成のmanifestに変換して既存RF制約・実験台帳を書き換えません。

`results/<task-id>.json`はworkerが一時ファイルへ書いてfsync後にatomic renameします。`logs/`、`tasks/`、`results/`、`locks/`をrun単位で分離します。aggregateは、全planned task IDs、実結果ID、欠落/重複、30dB必須および35dB公称条件を別々に報告します。Pareto表は**この有限task setで観測した**area–ILだけを示し、収束状態とH2/H3適格状態を列として残します。

Managerはpersistentな`.manager.lock`にOS `flock`を使い、worker起動前にtask別の`locks/<task-id>.lock`を取得してfile descriptorを子プロセスへ継承させます。子workerが終了するまでOS lockが保持されるため、managerをSIGKILLした後にworkerが残っていてもresume/aggregateを拒否します。SIGINT/SIGTERM時はworkerにSIGTERMを送り、結果が不完全なtaskはpendingとしてatomic statusへ記録します。**ロックファイルを削除・置換して解除してはいけません。** statusとPID/logを確認し、該当worker終了・ロック解放を確認してから同じrunをresumeしてください。runへ複数managerを同時に接続しないでください。

## 4. 判定・物理検証の境界

各最適化は6設定・各CSV帯域の有限サンプルに対するepigraph SLSQPです。出力の追加21点/segment validationと独立MNA/power/SPD報告は数値検証であり、連続周波数極値保証ではありません。`solver_converged`、`mandatory_30db_met_on_dense_grid`、`nominal_35db_met_on_dense_grid`、`il_0p30_target_met_on_dense_grid`は別フィールドで判定します。`converged=False`を性能限界と呼ばず、粗グリッド合格を高密度/独立検証合格と呼びません。

SRF、実Q(f)、Sパラメータ、実装寄生、EM、製造公差、IC/PCB面積、磁気結合係数の物理実現性はmanager外の後続ゲートです。`results/`の一時raw出力を無差別にGit管理せず、再現性・候補価値・検証水準をレビューした証拠のみ実験IDへキュレーションしてください。
