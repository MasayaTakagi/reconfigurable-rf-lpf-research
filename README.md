# Reconfigurable RF LPF Research

**Phase 2（トポロジー・性能限界探索）進行中。Phase 3は明示承認まで停止。**

6設定：B71 / B12 / B28 / B13+B14 / B26 / B8。全UL/DL通過帯域で最大ILを評価し、ULの2倍波・3倍波全域で最小減衰を評価する。公称目標は最大IL≤0.30dB、H2/H3≥35dB（必須≥30dB）。

## 現行仕様

- [仕様説明](docs/specification.md) / [機械可読な正本](data/design_constraints.json) / [帯域表](data/bands.csv)
- [解析方法](docs/methodology.md) / [設計判断](docs/decisions.md) / [ロードマップ](docs/roadmap.md)
- [候補索引](data/candidate_index.csv) / [候補の管理方法](candidates/README.md)

## 結果の読み方

旧35dB減衰付き候補は歴史的な数値探索結果であり、新仕様の可変C枝数・配置規則への適合は未確認。新しい整合専用の低IL値はH2/H3を課していないため、LPF成立値ではない。数値的な最良候補は大域最適性やEM実装性を証明しない。

## ディレクトリ

| 場所 | 用途 |
|---|---|
| `data/` | 現行仕様、帯域、候補一覧、過去の数値表 |
| `docs/` | 仕様・方法・判断・ロードマップ |
| `src/lpf/` | 共通解析基盤（移行中） |
| `experiments/` | 新規実験と保存済み研究結果 |
| `candidates/` | 採用候補の個別定義 |
| `tests/` | 自動検証 |
| `history/` | 旧データ（過去コードの再現性維持は対象外） |

## 実行

```bash
python scripts/audit_results.py
python -m unittest discover -s tests -v
```

**注意:** 現行の監査は主に保存データの整合性チェック。EM、全帯域の数学的保証、回路全体の独立再計算を意味しない。

## 最新のPCB-Lなし再最適化（2026-10-11）

新しい固定GJM01／対GND可変IC C（2枝・各0–4pF）／チップL単列結合／面積上限6の条件を使った有限回数のPhase 2探索を実施。**構造的制約を満たすが、最大IL 0.30dB目標は未達**。

| 候補 | チップL | 固定GJM01 | IC可変C | 面積 | 最大IL | H2/H3最小 |
|---|---|---:|---:|---:|---:|---:|
| [LPF-005](candidates/LPF-005.json) | LQP02×4 | 3 | 2 | 6 | 1.2511dB | 35.16/35.16dB |
| [LPF-006](candidates/LPF-006.json) | LQP02×2＋LQP01×2 | 4 | 2 | 6 | 1.1638dB | 35.19/35.31dB |

固定C・L値と6設定の可変C・結合行列は各JSONを参照。詳細は[探索レポート](experiments/no_pcb_policy_update_20261011/README.md)、[バンド別検証](experiments/no_pcb_policy_update_20261011/six_case_verified.csv)、[共通解析器による再計算スクリプト](scripts/check_no_pcb_candidates_20261011.py)。以前のCP07（0.3289dB）は可変Cの接続位置・枝数の新仕様に適合しない**歴史的参考値**であり、置き換えず保持する。**全トポロジーの網羅や大域最適性は未達**。LQP01実品番のL範囲も未確認。Phase 3は停止中。
