# RF-F002 Phase 2：P4-A ベンチマークと Full-LPF 再合成の中間報告

**状態：Phase 2 継続。正式条件 RF-F002 を維持。Phase 3 移行・`main` へのマージ・制約変更はしていない。**

- 作業ブランチ：`feat/rf-f002-full-lpf-large-search`
- 基準 `main`：`cf990d3eba625affb8e65da95b7c4f5ac4ec4be4`
- 実装コミット：`fc9d424bcaa9960b900d75df279757c153a2c98c`
- RF-F002 effective SHA-256：`f20d27e93451dcec2f823e6f7c3731c06d843050c4d2ace8b0b46ded605542e2`
- 数値実験時の worktree は clean。Python 3.12.15 / NumPy 2.5.4 / SciPy 1.18.1 / scipy-openblas、WSL2、AMD Ryzen 7 PRO 4750G（8 physical / 16 logical CPU、RAM 7.45 GiB）。BLAS/OMP/MKL thread は各1。

## 1. RF-F002 監査と修正

### 維持した正式条件

すべての新しい full-LPF 実験は正式 ID `RF-F002` とその上記 fingerprint を記録する。RF-T003/RF-T004 と PR #38 由来の回路は**初期値・接続候補としてだけ**利用し、過去の試験性能は RF-F002 成果に移し替えない。P4-A matching-only の合格を full-LPF 合格と呼ばない。

RF-F002 の設定値/Q/範囲・6設定で共通の固定部品・6設定別の2枝可変C・B13+B14 の単一設定・結合SPD・停止帯域30 dB必須/35 dB公称目標を変えていない。チップ面積コストは Pareto 評価軸で、hard cap ではない。IC可変Cは Q50、各枝0–1.5 pF。物理結合上限は現行 RF-F002 の強隣接チップペア |k|≤0.15、PCB-PCB |k|≤0.15、チップ-PCB k=0 とし、旧条件の|k|≤0.4を引き継いでいない。

### 発見した実装上の問題

`experiments/matching_limit/p4_batch.py` の `settings_for()` は固定 `GJM01` だけを pF→F 変換し、`PCB_PATTERN_C` は nH→H と誤解釈していた。また `bounds_for()` に PCB_PATTERN_C の明示範囲がなかった。既存の P4-A sampler はこの部品を生成していなかったため、今回の matching-only 数値結果には影響しないが、正式に許可された PCB-C を含む full graph で誤計算を招く。

修正：GJM01 と PCB_PATTERN_C の双方を pF→F 変換し、PCB-C を formal bounds 0.02–0.2 pF に設定。`tests/test_full_lpf.py::test_fixed_pcb_pattern_c_uses_pf_units_and_formal_bounds` で回帰検証した。直列C=0 pF は開放枝のままという試験も通過。

### 検索範囲の監査結論

現 P4-A sampler は正式に許される全グラフ・全部品集合を網羅しない有限 sampler であり、面積/ノード/部品種/配置の上限は実験上の計算範囲であって RF-F002 の正式 hard limit ではない。PCB_PATTERN_C と LQW04 を含むトポロジー生成の拡張、isomorphism を跨いだ全生成段階での重複排除、全cost帯を維持する汎用Pareto探索は今回完了していない。

## 2. P4-A 小規模ベンチマーク（`matching_only` のみ）

### 12 topology / 80 optimizer candidate の再開可能ベンチ

生の manager manifest・各 shard checkpoint は無視対象のローカル `results/` に保存。Run ID：`20261013T160125Z-6d7d7841`、`results/rf-f002-p4-benchmark/20261013T160125Z-6d7d7841/`。

| 指標 | 実測 |
|---|---:|
| 選択グラフ / planned candidate | 12 / 80 |
| 完了 / 収束 / 非収束 / 失敗 / 未実行 | 80 / 73 / 7 / 0 / 0 |
| 中断前 wall / resume 後 wall / 合計 wall | 902.260 / 583.586 / **1,485.846 s** |
| shard累積 worker秒 / candidate | 約2,767 s / **34.6 s** |
| objective評価 | 66,773、candidate当たり中央値638 |
| peak worker RSS / 2-worker合計 RSS | 83.8 MB / **167.4 MB** |
| minimum available RAM / peak host CPU | 6.37 GB / 19.6% |

条件は RF-F002、HV、seed `20261014`、1 topologyあたり初期値2・coupling layouts 2・可変C layouts 最大2、SLSQP最大120 iteration、9 sample/各segment、独立確認21 sample/各segment。中断後は同じrunでresumeし80候補すべてを完了した。

この run の最良 matching-only IL は0.212330 dB、面積cost 4⅔だったが、同じ候補の最小H2=0.469 dB/H3=1.768 dBである。**停止帯域制約を最適化していない matching-only の測定であり、RF-F002 full-LPF 成果ではない。** P4-Aは既存互換の `matching_only` のままである。

### worker 1対2の小さな比較

同一seed・同一4グラフ/4候補、9点、60 iteration、single start、同一 source/BLAS条件。Run IDs：

- 1 worker：`20261013T170321Z-147811fe`、57.960 s、peak total worker RSS 83.5 MB、CPU peak 11.8%。
- 2 workers：`20261013T170428Z-5f59268c`、40.608 s、peak total worker RSS 166.5 MB、CPU peak 17.2%。
- 全候補のグラフID・結果数値は一致。小規模測定の実効 speedup は **1.43×**。

4候補では起動/manager overhead が大きいため、この倍率を大規模・full-LPFに直線外挿しない。両runとも RAM 余裕は約6.3 GB。full-LPF の並列スループットは未測定。

## 3. Full-LPF optimizer と統合試験

`experiments/matching_limit/full_lpf.py` に、既存MNA/正式ポリシー/band読込/独立検証を共有する**固定トポロジー単位の**RF-F002 full-LPF optimizerを追加した。

- 6設定のUL/DL全sampleについて epigraph `min t`, `IL(case,f)≤t` を用いたSLSQP minimax。
- H2/H3 の停止帯域要件を30→35 dBの継続で最適化。全6設定・H2とH3双方を制約に含む。
- 全固定L/C、6設定×2枝の可変C、物理列上の強隣接chip k、PCB-PCB kを同時更新。旧|k|≤0.4候補は初期値もしくは投影後seedにとどめる。
- K行列SPDを制約し、正式部品範囲・明示シリーズ・可変C接続を各設定に適用。
- 各継続stage候補を21点/区間で比較し、H2/H3の30dB必須・35dB目標・IL≤0.30目標を別々に報告。独立validationで全6設定の利得差、電力残差、最小L固有値を保存。
- 出力に実際の部品値・edge/type/unit、設定別可変C、K、面積cost、continuation stages、optimizer状態、資源・入力hashを記録する standalone converter を追加。

`tests/test_full_lpf.py` 9件を含め、**全 unit/integration tests 234件 PASS**。`uv lock --check`、`uv sync --frozen`、`uv pip check`、`git diff --check` もPASS。再現可能な `maxiter=1` integration smoke をLPF-007/T003-5L/T004 seedに対して実行済み。

なお、出力の35dB判定は数値許容差1e-5 dBを含む。密gridは21点/CSV segmentであって連続帯域証明ではない。反復収束、SRF/Q(f)、実部品、公差、寄生、EM、物理結合実現性も保証しない。

## 4. RF-F002条件での実測再合成

PR #38のRF-T004 seed、RF-T003 seed、LPF-007は**条件を固定して再最適化した実行結果だけ**を次表に示す。各raw JSONは `.gitignore` 対象のローカル `results/full-lpf/` にある。共通source commitは実装コミット `fc9d424...`、worktree clean、solver SHA-256 `21dc598203f0d720cd56dbeb9547d8565aa82f93f0978af82855331823c879f9`。9点/segmentで最適化し、独立三方式validationは21点/segment。各runはsingle start・逐次実行。

| RF-F002で再実行した候補 | cost | wall | IL最悪（setting/region） | min H2 / H3 | 30dB必須 | 35dB公称 | IL≤0.30 | optimizer収束 |
|---|---:|---:|---:|---:|---|---|---|---|
| LPF-007 / 120 iter | 6 | 302.0 s | 4.72700 dB (B8/DL) | 34.95895 / 34.78654 dB | PASS | FAIL | FAIL | 未収束 |
| RF-T003 historical 5L `LOW_IL_30p01` seed | 6⅓ | 158.0 s | 3.74501 dB (B26/DL) | 12.28709 / 16.82567 dB | FAIL | FAIL | FAIL | 未収束 |
| RF-T003 historical 5L `MARGIN_30p100` seed | 6⅓ | 276.8 s | 0.639754 dB (B28/DL) | 34.99999999 / 34.99999999 dB | PASS | 1e-5 dB tolerance内 | FAIL | 未収束 |
| RF-T004 `T004-B35`, 第3可変Cを固定化 | 6 | 202.2 s | 9.38691 dB (B28/DL) | 35.00000 / 34.99995 dB | PASS | FAIL（H3不足） | FAIL | 未収束 |
| RF-T004 `T004-D35`, 第3可変Cを固定化 | 6 | 203.9 s | 5.90845 dB (B28/DL) | 34.99730 / 34.99720 dB | PASS | FAIL | FAIL | 未収束 |

RF-T003 5Lの元seedは旧試験の±0.4隣接kおよび一部1.5 pF超のCを含むため、RF-F002開始値に使う際、隣接kは0.15上限にscaleし、超過Cは1.5 pFへclipした。全固定L/Cと設定別2枝CはRF-F002の範囲内で再最適化。旧数値をRF-F002へ流用していない。5L `MARGIN_30p100` runは30dBを満たすbest-foundで、35dBはfloat差9e-9 dB程度のため1e-5許容差内扱い。**ただし最適化は未収束でIL目標0.30 dBから0.340 dB不足**し、正式目標達成とはしない。

共通して三方式間最大gain差は約2.8e-15–4.7e-15、最大電力残差は約8.8e-18–1.0e-17 W。run別最小L固有値は正。これは数値実装間の整合であって連続帯域・物理実装の証明ではない。

Full-LPF solver上で今回測定したwall範囲は**158–302秒/seed**（中央値204秒）、process peak RSSは約82 MB/逐次worker。観測runの中に `converged=True` かつIL≤0.30 dBを同時に満たすものはない。最良harmonic-feasible（30 dB、35 dBは数値許容差内）もIL 0.639754 dBで未達。LPF-007/T004も大幅にIL未達。area/performance frontierはこの限定された5 startの観測に限り、大域最適性を示さない。

## 5. S1/S2/S3 実測ベース概算と安全な次段階

以下は**full-LPFの1 topology × 1 layout × 1 seed start**だけを行う場合の概算。実測5 runの158–302秒を使用し、systematic topology generation、複数layout/start、失敗・resume overhead、frequency refinement、runner overheadを含めない。2-worker理想欄は完全に線形分割できる仮定であり、full-LPF 2-workerをまだ実測していない。

| 規模 | 1 worker（実測158–302 s/seed） | 2 worker・理想半減 | 実行状態 |
|---|---:|---:|---|
| S1 100 candidate seed | 4.4–8.4 h（中央値約5.7 h） | 2.2–4.2 h | **未起動** |
| S2 1,000 seed | 43.9–83.9 h（中央値約56.7 h） | 22.0–42.0 h | **未起動** |
| S3 10,000 seed | 18.3–35.0 日（中央値約23.6日） | 9.2–17.5 日 | **未起動** |

別測定の小規模 P4 matching-only では2-worker speedup 1.43×だった。これを仮に当てはめると2-workerの見積もりは理想欄より約40%長くなるが、問題設定が異なるため参考値にとどめる。現状は8 physical core・16 logical・約6.4 GB空きRAM。P4 2-worker runのRSSは167 MB、full-LPF single workerは82 MB。最初の実full-LPF 並列試験は**2 workers・BLAS各1 thread**、常時1.5 GiB以上の空きRAMをmanagerでゲートする設計が妥当。4 workerへ増やす実測根拠はない。

### 大規模S1をまだ起動しない理由

Full-LPF 数値solverと候補個別の変換器はあるが、**full-LPF用の複数トポロジー生成・費用層を保つ重複排除・multi-start orchestration・shard/checkpoint/resume manager・全結果Pareto aggregatorは未統合**である。現行 `scripts/local_p4.py` は matching-only を実行するためのmanagerであり、そのままfull-LPFへ読み替えていない。従って上表はS1/S2/S3の測定ベース予算であって、実行可能なfull-LPF run plan/完了runではない。無制限バッチは起動していない。

次の安全な工程： (1) full-LPF managerに計算条件hash/source hash・小batch・RAM gate・atomic checkpoint/resumeを統合、(2) PCB_PATTERN_C/LQW04を含む明示的expanded component alphabetとcost-bin coverage・isomorphism dedupeを実装、(3) multi-startと21点→高密度gridの失敗帯域adaptive refinementを試験、(4) unit+manager integration testsと独立MNA、(5) 2 workerの短いfull-LPF benchmark、(6) 計画値とresource headroomを確認後に承認された有限S1だけ実行。全トポロジー網羅性・global optimum・連続周波数保証は別に証明しない限り主張しない。

## 6. 保存証跡

`.gitignore`対象の`results/`にある実行時raw filesを、監査可能なチェックポイントとして次の追跡対象にも保存した：

- [`data/validation/rf_f002_phase2_20261013/summary.json`](../data/validation/rf_f002_phase2_20261013/summary.json)：条件hash、実行commit、ベンチマーク/Full-LPF主要指標と限界。
- [`p4-benchmark/`](../data/validation/rf_f002_phase2_20261013/p4-benchmark/)：matching-only 80候補のmanager manifest・aggregate・status。
- [`worker-compare/`](../data/validation/rf_f002_phase2_20261013/worker-compare/)：1/2 worker比較の両manifest・statusと、同一4候補の保存値をbyte-for-byte比較した`candidate-comparison.json`。
- [`full-lpf/`](../data/validation/rf_f002_phase2_20261013/full-lpf/)：LPF-007、RF-T003 5Lの2 seed、RF-T004 B35/D35の5回分の完全JSON（設定、stage候補、独立MNA結果、resource metadataを含む）。
- 最新mainとの統合時、先行するmainのEXP IDを上書きしないよう、このローカル系列のmanifestはEXP-025～EXP-031へ再採番した（対応表は本書末尾）。`data/experiment_index.csv`には再採番後のIDのみ登録。これらのmanifestは実行後にraw recorderから作成したことをlimitationsに残し、事前manifest生成済みとは主張しない。

元のローカル実行ディレクトリも保存してある：P4-A 80候補は`results/rf-f002-p4-benchmark/20261013T160125Z-6d7d7841/`、worker比較は`results/rf-f002-worker-compare/20261013T170321Z-147811fe/`と`.../20261013T170428Z-5f59268c/`、Full-LPFは`results/full-lpf/rf-f002-*-current.json`。追跡されたJSONはそのraw fileの内容をSHA付きで保存したコピーである。

これらはRF-F002の有限局所探索記録であり、RF-F002目標IL≤0.30 dBの達成解ではない。

## 7. 最新main統合・保存チェックポイントの数値再現（2026-10-14）

成果保全後、最新GitHub main `5dbd83217f7c8bb9acd0c9fefd9f4f1ea07d4f89` から作業ブランチを作成し、先行するP4-A由来EXP-020～024の回路記録・manifest・索引行を一切上書きせず、ローカル成果を統合した。RF-F002 effective SHA-256は引き続き`f20d27e93451dcec2f823e6f7c3731c06d843050c4d2ace8b0b46ded605542e2`で不変。再採番は実験分類や条件を変更せず、既存raw結果・チェックポイント・元run ID・制約ハッシュ・検証履歴も変更しない。

| 統合前ローカルID | main上の保存ID | 内容 |
|---|---|---|
| EXP-020 | EXP-025 | P4-A `matching_only` 12 topology / 80 candidates |
| EXP-021 | EXP-026 | P4-A `matching_only` 1/2 worker microbenchmark |
| EXP-022 | EXP-027 | LPF-007 seedのRF-F002再最適化 |
| EXP-023 | EXP-028 | RF-T003 LOW_IL seedのRF-F002再最適化 |
| EXP-024 | EXP-029 | RF-T003 MARGIN seedのRF-F002再最適化 |
| EXP-025 | EXP-030 | RF-T004 B35 seedのRF-F002再最適化 |
| EXP-026 | EXP-031 | RF-T004 D35 seedのRF-F002再最適化 |

mainの既存EXP-020（RF-T004 PR #38 archive）、EXP-021（4L bridge）、EXP-022（area-six trial）、EXP-023（RF-F002 2-variable-C）、EXP-024（branch archive）はそのまま保持した。新IDは実験索引で未使用であることを確認し、索引はmanifestから再生成・監査する。最適化器を後続改良するため、旧runで実際に使った`full_lpf.py`とT003再最適化scriptは [`code_snapshot/`](../data/validation/rf_f002_phase2_20261013/code_snapshot/) にSHA一致のまま保存し、新しいcurrent sourceを過去runの実行コードとして読み替えない。

保存回路を7001点/各CSV区間で再評価した結果（metric差は保存checkpointとの差）：

| 候補 | 保存IL / 再評価IL [dB] | 保存min H2 / 再評価 [dB] | 保存min H3 / 再評価 [dB] | 最大絶対差 |
|---|---:|---:|---:|---:|
| EXP-023 30dB | 0.381014384960942 / 0.381014384960938 | 30.009999998420 / 30.009999998420 | 30.009999997441 / 30.009999997441 | 2.2×10⁻¹⁴ dB |
| EXP-023 35dB | 0.460180295393763 / 0.460180295393757 | 35.019999999861 / 35.019999999861 | 35.019999999736 / 35.019999999736 | 1.2×10⁻¹³ dB |
| EXP-017 `EXP017-LQW2-H35` | 0.378797914107362 / 0.378797914107364 | 35.029999999610 / 35.029999999610 | 35.029999998751 / 35.029999998751 | 1.3×10⁻¹³ dB |

上記3回路は保存したチェックポイントと1e-5 dB以内で再現した。これは有限周波数格子上の数値再現であり連続帯域証明ではない。IL≤0.30 dBはいずれも未達。再計算出力、checkpoint/script SHA-256、期待値との差分は[`data/validation/rf_f002_checkpoint_reproduction_20261014/`](../data/validation/rf_f002_checkpoint_reproduction_20261014/)に保存。

EXP-017 READMEに記載の近接30dB候補（最悪IL 0.301248245 dB）については、最新mainのtracked historyにも利用可能な回路定数JSON/6設定可変Cベクトルがなく、**数値再現できなかった**。`data/validation/exp017_20261012/checkpoints.json`にある別の過去候補は旧/非canonical条件で異なる回路であり代用していない。値を推定・再構築してRF-F002チェックポイントと呼ぶことはしない。回路ベクトルを保存する追加が必要。

## 8. 維持する判定境界

- 現時点でRF-F002 IL≤0.30 dBを満たす収束・独立検証済み候補は確認できていない。
- `matching_only`、RF-T003/RF-T004の元性能、再最適化後のRF-F002性能は別々に保持する。
- 有限グリッドの数値/MNA再現は、連続周波数保証・大域最適・SRF/Q(f)/寄生/EM/公差/実装の証明ではない。
- 本変更・検証をもってPhase 3には進まず、制約正本は変更しない。mainへのmergeは実施していない。
