# 再現方法・データ系譜

## 1. 依存と環境

```bash
python --version                 # 推奨: Python 3.11+
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/audit_results.py
python -m unittest discover -s tests -v
```

NumPy, SciPy, Numba, Matplotlibが必要。過去の数値最適化コードの依存バージョンは厳密には凍結されていないため、最適化ルーチンの数値解は環境により変化する可能性がある。再計算開始前に `pip freeze`、BLASとCPU情報を保存すること。

## 2. 直近の理論強結合モデル

```bash
cd experiments/strong_pcb_coupling_theory
OPENBLAS_NUM_THREADS=1 python independent_verify.py
```

- `independently_verified.json` と `stack_band_verified.csv` を再生成する。
- フル探索ではなく、保存された各結合係数条件の解を、**別の全7巻線節点解析**で確認するコマンド。
- k=0.98で6ケース最大IL約0.295208dB、H2/H3最小約35.10dBが目安。
- 大量の探索を再実行する場合は `stack_refine.py`、`series_stack.py` を参照。出力の一部はファイルを上書きするので、再生成前に原始データを別途コピーすること。

前処理なしで数値チェックする場合：

```bash
python scripts/audit_results.py --detail
```

チェックするのは保存データの内部整合・構成・周波数帯定義であり、電磁界の成立性はチェックしていない。

## 3. 以前の探索

- `experiments/phase2_4chip_baseline/`: 4チップL・35dB目標のトポロジー比較。
- `experiments/three_series_baseline/`: 3段直列並列LC＋中間シャントの数値検証・再計算。
- `experiments/weak_pcb/`: chip–PCB間\(|k|\le0.03\)を含むPCB-L増設探索。
- `experiments/pcb_pcb_coupled/`: PCB間結合を0～0.30まで許した数値探索。
- `experiments/strong_pcb_coupling_theory/`: PCB間の受動性条件のみ課した理論探索、同極性直列PCB-Lによる改善。
- `history/original-analysis/`: 各段階の原始ZIP。手元の再編でファイル構造が変わっていないことを確認するために保管。

各実験フォルダに保存されているREADME/スクリプトを確認。**過去のコードは研究過程のスナップショットであり、すべてが一括自動実行可能であると保証していない。** 直接編集して履歴を失うのではなく、再計算用フォルダをコピーして実施すること。

## 4. エビデンスの変更管理

- 正式に比較可能な結果は `data/evidence_register.csv` のIDで参照する。
- `data/archive_manifest.csv` に原始ZIPのSHA-256を記録する。著者の既存ファイルを再編集・再圧縮するとハッシュが変わる。
- グラフの値とテーブルは、可能であれば同じCSV/JSONから自動描画する。
- 詳細チェックは、6設定のUL＋DLとUL由来H2/H3すべての**帯域端および内部極値**を確認すること。細かい周波数メッシュだけでは数学的な証明にならない。
