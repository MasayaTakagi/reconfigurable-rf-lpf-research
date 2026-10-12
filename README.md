# Reconfigurable RF LPF Research — Phase 2

**2026-10-12 承認済み新方針（RF-F001）：** [制約版管理](data/constraints/README.md) を導入。**チップ面積はハード制約ではなく、6設定全帯域最悪ILと並ぶパレート評価軸**。P4-Aの面積最大6などは計算上の有限探索範囲に限定する。過去の「hard cap6」等の記載は当時の実験条件であり、現行正式RF制約ではない。実験ごとのRF制約ID、実効制約ハッシュ、数値モデル、検証状態を追跡する。Phase 2継続、Phase 3停止。

**ChatGPTプロジェクトの運用指示の正本：** [docs/chatgpt_project_instructions.md](docs/chatgpt_project_instructions.md)。ChatGPTアプリの指示欄はこの正本への短い参照とし、**現行RF制約の変更不可の正式版は [RF-F001](data/constraints/formal/RF-F001.json)、[data/design_constraints.json](data/design_constraints.json) は互換コピー**とする。研究結果は実験記録と検証状態を参照する。

**2026-10-12 LQP02シリーズ別新ルール（Phase 2）:** インダクタは **LQP02HV：Q25・0.4～27nH（優先）**、**LQP02HQ：Q20・0.2～56nH（必要時のみ、可能な限り低いL）**。旧「56nHでQ25」を含むEXP011等の結果は履歴値であり、新ルール下の性能実証値ではない。新Q条件で再最適化・独立MNA検証した[EXP-015](experiments/chatgpt_topology_search/runs/EXP-015/README.md)と[仕様更新](docs/inductor_series_policy.md)を参照。実際のSRF/Q(f)/寄生は未検証、Phase 3は停止継続。

**目標**：現行RF制約の範囲で、ChatGPT主導探索の最良候補 **LPF-007** を超える `full_lpf` を発見する。先行候補は6設定UL/DL最大IL **0.513168414 dB**、UL H2/H3最小 **35.070 / 35.070 dB**（有限グリッド・最適化未収束）。当面はH2/H3≥35 dBを維持してIL改善、最終公称目標はIL≤0.30 dB。必須減衰は30 dB。有限探索結果を理論限界や実装証明と呼ばない。

**2026-10-11制約更新:** [設計仕様](docs/specification.md)にPCBパターン固定容量を追加（**0.02～0.2pF**、Q40、チップ面積コスト0、最大3個）。GJM01やIC可変Cとは別種別。容量の上限は0.2pFで、実基板の面積と寄生は未評価。従来LPF-007/008の定数や公称性能を自動的に変更したものではない。

**コスト7探索（Phase 2・面積予算を実験的に拡張）:** [EXP-002](experiments/chatgpt_topology_search/runs/EXP-002/README.md) に、コスト6のLPF-007（0.513168dB）を上回った最大IL **0.508389dB** の [A7-01](experiments/chatgpt_topology_search/runs/EXP-002/A7-01.json) と、隣接結合を2組に限定した **0.511964dB** の [A7-02](experiments/chatgpt_topology_search/runs/EXP-002/A7-02.json) を保存。使用チップ面積は両方6⅔。既存の正式hard cap6は変更せず、この比較では7を実験予算として使用。独立MNAで数値を確認したが、最適化器未収束、EM未検証、コスト7の数学的限界は未証明。

**旧0.32dB対現行0.51dBの制約比較:** [EXP-003の独立レビュー](experiments/chatgpt_topology_search/runs/EXP-003/README.md)で、旧4可変C回路CP07（0.328924dB）と現行A7-01（0.508389dB）を同じL/C Qで比較。旧回路でチップ結合だけ一列隣接へ変えても、4可変Cを保持した再最適化解は0.337660dBだった。**現在の2枝・対GND・各4pFという可変C機能制約が主要なボトルネック候補**。旧解は現行の正式候補ではない。

**新しい中間目標：最大IL 0.40dB（公称H2/H3≥35dB、6設定UL/DL全帯域）**。まず [EXP-004](experiments/chatgpt_topology_search/runs/EXP-004/README.md) で現行コスト7基準A7-01（0.508389dB）の更新を狙う。局所探索98件では未達、42条件は未完了。再現可能な[ベクトル化探索器](experiments/chatgpt_topology_search/runs/EXP-004/sweep_040.py)、[手動分割Actions](.github/workflows/lpf-target040.yml)、[進捗集計器](experiments/chatgpt_topology_search/runs/EXP-004/summarize.py)を準備済み。**大規模Actions探索はまだ起動していない**。最終0.30dB目標とPhase 3停止は維持。

**Phase 2・コスト7の更新基準（EXP-005、2026-10-12）:** [A7-03](experiments/chatgpt_topology_search/runs/EXP-005/A7-03.json) で、6設定最大IL **0.507331dB**、H2/H3最小約35.02dBを発見。既存A7-01の0.508389dBを0.001058dB改善（SLSQP未収束、7,001点／周波数区間の数値検証、代表点の独立MNA確認）。[EXP-005レポート](experiments/chatgpt_topology_search/runs/EXP-005/README.md) に追加132局所探索の実施範囲と不成立を記録。**0.40dB目標は未達、hard cap6は変更せず、Phase 3も停止。**

**Phase 2追加探索（EXP-006、2026-10-12）:** コスト7以内の最良数値チェックポイントを [A7-04](experiments/chatgpt_topology_search/runs/EXP-006/A7-04.json) の**最大IL 0.506951dB、最小H2/H3約35.002dB**へ更新。ただし公称35dBへの余裕が約0.002dBしかないため、[A7-03](experiments/chatgpt_topology_search/runs/EXP-005/A7-03.json) を減衰余裕比較用に保持。追加した**PCBパターンC×2/×3と5L構成の合計98局所探索**は[EXP-006レポート](experiments/chatgpt_topology_search/runs/EXP-006/README.md)に記録。大域最適性は未証明、0.40dB未達、hard cap6とPhase 3停止を維持。

**Phase 2・EXP-007追加探索（2026-10-12）:** [固定C再配置・チップL再配置・PCB-L追加の103件の局所探索と2可変C感度解析](experiments/chatgpt_topology_search/runs/EXP-007/README.md)。各群から35dB条件を満たす粗い数値解は合計44件。最良の追加候補は0.524581dBで、**保存済みA7-04（0.506951dB）は未更新**。B71のH2/H3最小減衰に対する2制御変数の局所感度行列は条件数約9.36で、制御感度の偏りが見られた。0.40dB目標未達、正式hard cap6とPhase 3停止は維持。

**2方式を並行**：ChatGPTはRF理論から回路を発案して専用高速最適化、自動探索は有限のグラフ・素子・配置クラスを生成して比較。良好な構造と初期値を相互に利用し、共通MNAと同一の6設定評価で検証する。現在のP4-Aは可変CがIN/OUT接続に固定されており、LPF-007/008の内部トラップCを探索できないため、一般化が最優先。

## フォルダ構成と作業先

| フォルダ | 用途 |
|---|---|
| [`experiments/chatgpt_topology_search/`](experiments/chatgpt_topology_search/) | **ChatGPT探索の作業場所**。新規実験はその下の`runs/EXP-NNN/`を実験開始時に作成 |
| [`experiments/matching_limit/`](experiments/matching_limit/) | 自動グラフ探索、P4-A最適化、シャード・再開処理 |
| [`src/lpf/`](src/lpf/) | 両探索で共用するMNA、独立解析、評価、制約検証 |
| [`candidates/`](candidates/) | 現行比較候補LPF-007/008の正式な記録 |
| [`data/`](data/) | **現行RF制約の互換コピー**`design_constraints.json`（正本は`constraints/formal/RF-F001.json`）、帯域`bands.csv`、候補索引 |
| [`docs/`](docs/) | [設計仕様](docs/specification.md)、[Phase 2ロードマップ](docs/roadmap.md)、[歴史的結果の出典索引](docs/historical_results.md) |
| [`scripts/`](scripts/)・[`tests/`](tests/) | 監査、候補検証、Artifacts、回帰テスト |
| [`.github/workflows/`](.github/workflows/) | 短いCIと手動のP4-A計算 |

## 基本ルール

- AI探索の専用スクリプト・未検証解は実験フォルダへ。広く使える解析・最適化処理は`src/lpf/`へ移す。
- 有望解は独立MNA、SPD、電力収支、6設定のUL/DLとH2/H3を確認してから`candidates/`へ登録する。最適化未収束とジョブ失敗を区別する。
- `matching_only`はH2/H3制約を含まず、`full_lpf`候補との性能比較に混ぜない。
- **過去の実験・旧ロードマップ・旧候補はGit履歴に保管**し、[歴史的結果の索引](docs/historical_results.md)から元コミット・検証状態を追跡する。削除は研究結果が無効になったことを意味しない。
- Phase 2継続。**Phase 3は明示承認まで停止**。旧Phase 4以降の計画は破棄する。

## 検証・実行

```bash
python -m pip install -r requirements.txt
python scripts/audit_results.py
python -m unittest discover -s tests -v
python scripts/verify_no_pcb_tunable_candidates.py
```

自動CIでは、基準値を固定したLPF-007/008の有限グリッド回帰と、matching-onlyの解析的既知回路の回帰も検証する。新しい候補は `data/candidate_index.csv` へ追加でき、LPF-007/008を削除することはできない。

大規模P4-Aは[手動Actions](.github/workflows/lpf-p4-a.yml)で実行し、限定的なArtifact保存・再開・集計の再検証には[手動スモーク](.github/workflows/lpf-p4-a-smoke.yml)を利用する。

旧G1の[1シャード実行](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128578799)・[2シャード実行](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128871403)に加え、PR #10変更後の計算構成でも[実機スモーク](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38139630751)が **PASS**。新構成では1シャードの3グラフをArtifact越しに2回再開し、G1集計が完了した。これはソフトウェア動作確認であり、P4-A網羅探索やIL改善の完了ではない。
