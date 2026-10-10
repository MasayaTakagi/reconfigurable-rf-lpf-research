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
