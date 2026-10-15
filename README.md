# Reconfigurable RF LPF Research — Phase 2

## 現行ステータス（2026-10-15／PR #54統合後のmain）

> この節は2026-10-15時点の状況を記録する。最新の数値・実験状態は[RF制約台帳](data/constraints/registry.json)、[ロードマップ](docs/roadmap.md)、[研究候補台帳](data/research_candidate_register.csv)、[課題台帳](data/research_review_issues.csv)を確認する。下の「過去の研究記録」にある旧時点の「現行」「未導入」「hard cap 6」等は現在の承認済み仕様を示さない。

- **研究フェーズ・正本：** Phase 2継続、**Phase 3はユーザーの明示承認まで停止**。[ChatGPT運用正本](docs/chatgpt_project_instructions.md)と、正式数値制約[RF-F002](data/constraints/formal/RF-F002.json)を適用する。[design_constraints.json](data/design_constraints.json)は互換コピー、周波数区間は[bands.csv](data/bands.csv)。RF-T004は3可変Cの認可済み**試験条件**であり正式RF-F002と区別する。
- **PRとCI：** PR [#48](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/48)～[#54](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/54)はmainへ統合済み。PR #54のマージコミットは `70ef42acab4bb2388adc6366746f8ef87a0a9066`。そのmainに対する[Phase 2 regression](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38744650334)は**PASS**。CI成功は連続帯域・実機の物理性能証明ではない。
- **実験番号：** 既存39実験（EXP-001～017、EXP-020～041）をmain台帳に登録、EXP-018/019は永久欠番。PR #53で[中央予約台帳](data/experiment_number_registry.csv)と[手動予約workflow](.github/workflows/reserve_experiment_number.yml)をmain導入済み。ただし**GitHub上の手動予約の本番運用・同時申請は未検証**。EXP-042は未予約であり、mainへの予約確定と再照合PASSより前に新規実験を開始しない。[予約規則](docs/experiment_number_reservation_policy_20261015.md)を参照。
- **研究候補：** [選別候補14件・比較区分8件](data/research_candidate_register.csv)。正式RF-F002／H2・H3≥30dBのstrict有限格子における保存候補は、EXP-017の最悪IL **0.301248245dB**、H2最小 **30.005000dB**、H3最小 **30.004642dB**。**IL≤0.30dBは未達**であり、公称35dB減衰も未達。RF-T004のIL **0.297114032dB**は試験条件の結果であり正式仕様の達成には数えない。候補間の共通格子による横断再評価は未完了。
- **EXP-017原ベクトル：** PR #54で正式2可変C・23要素ベクトルを回収。元ZIP内の候補JSON（2,959B）をバイト同一でGitに保全し、[正規化候補](experiments/chatgpt_topology_search/runs/EXP-017/EXP017-LQW4-H30-NEAR.recovered.json)・[検証記録](data/validation/exp017_rf_f002_recovered_20261015/summary.json)を追加。独立9×9枝電流MNA／5×5ノード式を28周波数区間×7,001点＝196,028点で照合。**元ZIPバイナリ全体、残り25member、453最適化試行の全履歴はGit未収録／未再実行**。詳細は[出典レビュー](docs/phase2_exp017_checkpoint_provenance_review_20261015.md)。
- **証拠保存：** 外部アーカイブを使わずGitHubを長期管理先とするユーザー方針を維持。[GitHub-only保存方針文書](docs/experiment_result_storage_policy_proposal_20261015.md)は**段階導入中の提案**であり、すべての旧実験が完全再現可能になったことを意味しない。元資料は削除・改竄しない。
- **残課題：** 旧warm-start端子remap関連（RG-003）、候補横断共通格子（RG-010）、実験メタデータ欠損（RG-009）、物理Q(f)・SRF・寄生・EM・公差評価。S1の100 graph/start大規模探索は未開始。新規探索は[ロードマップ](docs/roadmap.md)のゲートを優先する。

---

## 過去の研究記録（当時の仕様・作業状態の保存）

以下は2026-10-12以降の歴史的な記述であり、旧RF-F001、旧面積hard cap、旧PRの進捗を現在の正式状態として使用しない。


**2026-10-12（当時の正式条件RF-F001に関する履歴）：** [制約版管理](data/constraints/README.md)を導入。以下のRF-F001に関する実験方針は当時の記録であり、**現行正式条件はRF-F002**。チップ面積はハード制約ではなく、6設定全帯域最悪ILと並ぶパレート評価軸。P4-Aの面積最大6などは計算上の有限探索範囲に限定。Phase 2継続、Phase 3停止。

**ChatGPTプロジェクトの運用指示の正本：** [docs/chatgpt_project_instructions.md](docs/chatgpt_project_instructions.md)。ChatGPTアプリの指示欄はこの正本への短い参照とし、**現行RF制約の変更不可の正式版は [RF-F002](data/constraints/formal/RF-F002.json)、[data/design_constraints.json](data/design_constraints.json) は互換コピー**とする。研究結果は実験記録と検証状態を参照する。

**2026-10-12 LQP02シリーズ別新ルール（Phase 2）:** インダクタは **LQP02HV：Q25・0.4～27nH（優先）**、**LQP02HQ：Q20・0.2～56nH（必要時のみ、可能な限り低いL）**。旧「56nHでQ25」を含むEXP011等の結果は履歴値であり、新ルール下の性能実証値ではない。新Q条件で再最適化・独立MNA検証した[EXP-015](experiments/chatgpt_topology_search/runs/EXP-015/README.md)と[仕様更新](docs/inductor_series_policy.md)を参照。実際のSRF/Q(f)/寄生は未検証、Phase 3は停止継続。

**Phase 2研究目標**：現行RF-F002の範囲で`full_lpf`候補を探索し、性能・実装性を独立検証する。比較基準LPF-007（最大IL 0.513168414 dB、UL H2/H3最小35.070/35.070 dB）は旧RF-F001条件の有限グリッド値で、RF-F002適合の実証ではない。最終公称目標はIL≤0.30 dB、H2/H3≥35 dB、必須減衰30 dB。有限探索結果を理論限界や実装証明と呼ばない。

**2026-10-11制約更新:** [設計仕様](docs/specification.md)にPCBパターン固定容量を追加（**0.02～0.2pF**、Q40、チップ面積コスト0、最大3個）。GJM01やIC可変Cとは別種別。容量の上限は0.2pFで、実基板の面積と寄生は未評価。従来LPF-007/008の定数や公称性能を自動的に変更したものではない。

**コスト7探索（Phase 2・面積予算を実験的に拡張）:** [EXP-002](experiments/chatgpt_topology_search/runs/EXP-002/README.md) に、コスト6のLPF-007（0.513168dB）を上回った最大IL **0.508389dB** の [A7-01](experiments/chatgpt_topology_search/runs/EXP-002/A7-01.json) と、隣接結合を2組に限定した **0.511964dB** の [A7-02](experiments/chatgpt_topology_search/runs/EXP-002/A7-02.json) を保存。使用チップ面積は両方6⅔。既存の正式hard cap6は変更せず、この比較では7を実験予算として使用。独立MNAで数値を確認したが、最適化器未収束、EM未検証、コスト7の数学的限界は未証明。

**旧0.32dB対現行0.51dBの制約比較:** [EXP-003の独立レビュー](experiments/chatgpt_topology_search/runs/EXP-003/README.md)で、旧4可変C回路CP07（0.328924dB）と現行A7-01（0.508389dB）を同じL/C Qで比較。旧回路でチップ結合だけ一列隣接へ変えても、4可変Cを保持した再最適化解は0.337660dBだった。**現在の2枝・対GND・各4pFという可変C機能制約が主要なボトルネック候補**。旧解は現行の正式候補ではない。

**新しい中間目標：最大IL 0.40dB（公称H2/H3≥35dB、6設定UL/DL全帯域）**。まず [EXP-004](experiments/chatgpt_topology_search/runs/EXP-004/README.md) で現行コスト7基準A7-01（0.508389dB）の更新を狙う。局所探索98件では未達、42条件は未完了。再現可能な[ベクトル化探索器](experiments/chatgpt_topology_search/runs/EXP-004/sweep_040.py)、[手動分割Actions](.github/workflows/lpf-target040.yml)、[進捗集計器](experiments/chatgpt_topology_search/runs/EXP-004/summarize.py)を準備済み。**大規模Actions探索はまだ起動していない**。最終0.30dB目標とPhase 3停止は維持。

**Phase 2・コスト7の更新基準（EXP-005、2026-10-12）:** [A7-03](experiments/chatgpt_topology_search/runs/EXP-005/A7-03.json) で、6設定最大IL **0.507331dB**、H2/H3最小約35.02dBを発見。既存A7-01の0.508389dBを0.001058dB改善（SLSQP未収束、7,001点／周波数区間の数値検証、代表点の独立MNA確認）。[EXP-005レポート](experiments/chatgpt_topology_search/runs/EXP-005/README.md) に追加132局所探索の実施範囲と不成立を記録。**0.40dB目標は未達、hard cap6は変更せず、Phase 3も停止。**

**Phase 2追加探索（EXP-006、2026-10-12）:** コスト7以内の最良数値チェックポイントを [A7-04](experiments/chatgpt_topology_search/runs/EXP-006/A7-04.json) の**最大IL 0.506951dB、最小H2/H3約35.002dB**へ更新。ただし公称35dBへの余裕が約0.002dBしかないため、[A7-03](experiments/chatgpt_topology_search/runs/EXP-005/A7-03.json) を減衰余裕比較用に保持。追加した**PCBパターンC×2/×3と5L構成の合計98局所探索**は[EXP-006レポート](experiments/chatgpt_topology_search/runs/EXP-006/README.md)に記録。大域最適性は未証明、0.40dB未達、hard cap6とPhase 3停止を維持。

**Phase 2・EXP-007追加探索（2026-10-12）:** [固定C再配置・チップL再配置・PCB-L追加の103件の局所探索と2可変C感度解析](experiments/chatgpt_topology_search/runs/EXP-007/README.md)。各群から35dB条件を満たす粗い数値解は合計44件。最良の追加候補は0.524581dBで、**保存済みA7-04（0.506951dB）は未更新**。B71のH2/H3最小減衰に対する2制御変数の局所感度行列は条件数約9.36で、制御感度の偏りが見られた。0.40dB目標未達、正式hard cap6とPhase 3停止は維持。

**2方式を並行**：ChatGPTはRF理論から回路を発案して専用高速最適化、自動探索は有限のグラフ・素子・配置クラスを生成して比較。良好な構造と初期値を相互に利用し、共通MNAと同一の6設定評価で検証する。現在のP4-Aは可変CがIN/OUT接続に固定されており、LPF-007/008の内部トラップCを探索できないため、一般化が最優先。

## ローカル計算基盤（Stage 2）

大規模P4-A探索の主たる実行基盤は、ユーザー指示によりUbuntu 24.04 / WSL2のローカル環境へ移行する。Python 3.12の環境はuvで管理し、依存条件の正本を`pyproject.toml`、固定版を`uv.lock`とする。GitHub Actionsはuv lockを使うCI・回帰試験として維持し、既存の手動P4-A・実験workflowも削除せず利用可能な状態を保つ。

[`docs/local_execution.md`](docs/local_execution.md)にuvセットアップ、P4-Aのplan/run/status/resume/aggregate操作、resource監視、チェックポイント・再開規則を記載する。`scripts/local_p4.py plan`は計算せず、`run`だけがジョブを開始する。P4-Aは`matching_only`であり`full_lpf`性能達成を示さない。Stage 2は計算基盤の構築・小規模検証で、**大規模探索は未着手**。Phase 2継続、Phase 3停止。

## フォルダ構成と作業先

| フォルダ | 用途 |
|---|---|
| [`experiments/chatgpt_topology_search/`](experiments/chatgpt_topology_search/) | **ChatGPT探索の作業場所**。新規実験はその下の`runs/EXP-NNN/`を実験開始時に作成 |
| [`experiments/matching_limit/`](experiments/matching_limit/) | 自動グラフ探索、P4-A最適化、シャード・再開処理 |
| [`src/lpf/`](src/lpf/) | 両探索で共用するMNA、独立解析、評価、制約検証 |
| [`candidates/`](candidates/) | 現行比較候補LPF-007/008の正式な記録 |
| [`data/`](data/) | **現行RF-F002の互換コピー**`design_constraints.json`（正本は`constraints/formal/RF-F002.json`）、制約台帳・履歴条件、帯域`bands.csv`、候補索引 |
| [`docs/`](docs/) | [設計仕様](docs/specification.md)、[Phase 2ロードマップ](docs/roadmap.md)、[ローカル実行](docs/local_execution.md)、[歴史的結果の出典索引](docs/historical_results.md) |
| [`scripts/`](scripts/)・[`tests/`](tests/) | 監査、候補検証、Artifacts、ローカル実行マネージャー、回帰テスト |
| [`.github/workflows/`](.github/workflows/) | 短いCIと手動のP4-A計算 |

## 基本ルール

- AI探索の専用スクリプト・未検証解は実験フォルダへ。広く使える解析・最適化処理は`src/lpf/`へ移す。
- 有望解は独立MNA、SPD、電力収支、6設定のUL/DLとH2/H3を確認してから`candidates/`へ登録する。最適化未収束とジョブ失敗を区別する。
- `matching_only`はH2/H3制約を含まず、`full_lpf`候補との性能比較に混ぜない。
- **過去の実験・旧ロードマップ・旧候補はGit履歴に保管**し、[歴史的結果の索引](docs/historical_results.md)から元コミット・検証状態を追跡する。削除は研究結果が無効になったことを意味しない。
- Phase 2継続。**Phase 3は明示承認まで停止**。旧Phase 4以降の計画は破棄する。

実験の制約・実行・検証の出典は [実験索引](data/experiment_index.csv) と
[マニフェスト運用](docs/experiment_manifests.md) を参照。EXP-001～015は履歴として棚卸しし、
不明な実効条件を現行正式版へ読み替えていない。

## 検証・実行

```bash
uv sync --frozen
uv run --frozen python scripts/audit_results.py
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python scripts/verify_no_pcb_tunable_candidates.py
```

`requirements.txt`は後方互換用の依存条件ミラー。通常の開発・CI・ローカル探索は`uv.lock`で固定したuv環境を利用する。

自動CIでは、基準値を固定したLPF-007/008の有限グリッド回帰と、matching-onlyの解析的既知回路の回帰も検証する。新しい候補は `data/candidate_index.csv` へ追加でき、LPF-007/008を削除することはできない。

大規模P4-Aは[手動Actions](.github/workflows/lpf-p4-a.yml)で実行し、限定的なArtifact保存・再開・集計の再検証には[手動スモーク](.github/workflows/lpf-p4-a-smoke.yml)を利用する。

旧G1の[1シャード実行](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128578799)・[2シャード実行](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128871403)に加え、PR #10変更後の計算構成でも[実機スモーク](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38139630751)が **PASS**。新構成では1シャードの3グラフをArtifact越しに2回再開し、G1集計が完了した。これはソフトウェア動作確認であり、P4-A網羅探索やIL改善の完了ではない。
