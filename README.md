# Reconfigurable RF LPF Research — Phase 2

**目標**：現行RF制約の範囲で、ChatGPT主導探索の最良候補 **LPF-007** を超える `full_lpf` を発見する。先行候補は6設定UL/DL最大IL **0.513168414 dB**、UL H2/H3最小 **35.070 / 35.070 dB**（有限グリッド・最適化未収束）。当面はH2/H3≥35 dBを維持してIL改善、最終公称目標はIL≤0.30 dB。必須減衰は30 dB。有限探索結果を理論限界や実装証明と呼ばない。

**2方式を並行**：ChatGPTはRF理論から回路を発案して専用高速最適化、自動探索は有限のグラフ・素子・配置クラスを生成して比較。良好な構造と初期値を相互に利用し、共通MNAと同一の6設定評価で検証する。現在のP4-Aは可変CがIN/OUT接続に固定されており、LPF-007/008の内部トラップCを探索できないため、一般化が最優先。

## フォルダ構成と作業先

| フォルダ | 用途 |
|---|---|
| [`experiments/chatgpt_topology_search/`](experiments/chatgpt_topology_search/) | **ChatGPT探索の作業場所**。新規実験はその下の`runs/EXP-NNN/`を実験開始時に作成 |
| [`experiments/matching_limit/`](experiments/matching_limit/) | 自動グラフ探索、P4-A最適化、シャード・再開処理 |
| [`src/lpf/`](src/lpf/) | 両探索で共用するMNA、独立解析、評価、制約検証 |
| [`candidates/`](candidates/) | 現行比較候補LPF-007/008の正式な記録 |
| [`data/`](data/) | **RF制約の正本**`design_constraints.json`、帯域`bands.csv`、候補索引 |
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

自動CIでは、基準値を固定したLPF-007/008の有限グリッド回帰と、matching-onlyの解析的既知回路の回帰も検証する。新しい候補は\`data/candidate_index.csv\`へ追加でき、LPF-007/008を削除することはできない。\n\n大規模P4-Aは[手動Actions](.github/workflows/lpf-p4-a.yml)で実行。**以下のG1 smokeはPR #10より前の計算構成の結果**であり、PR #10の新ハッシュで再実行が必要。旧G1の1/2シャードsmokeと再開は[1シャード](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128578799)・[2シャード](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128871403)で成功済み。詳細な実行結果はGitHub履歴で追跡する。
