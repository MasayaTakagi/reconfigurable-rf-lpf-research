# Phase 2: 六設定の帯域評価

共通評価器は data/bands.csv にある6設定のUL/DL/H2/H3の全区間を読み、両端を含む周波数メッシュで評価する。B13+B14は2バンドの区間を同一設定で処理する。

Python API: lpf.evaluate.evaluate_settings(make_circuit, samples_per_segment=21)。make_circuit(case)はlpf.circuit.solveのキーワード引数を返す。固定トポロジー・L・固定C・結合の設定間不変性は呼出側の責任であり、現時点では自動検査しない。

ILと高調波帯域の伝送電力減衰はともに -10log10(Pload/Pavs)。UL/DLは最大、H2/H3は最小を報告する。有限メッシュの極値は連続帯域の保証ではない。

independent.py はインダクタ枝を消去した節点アドミタンス法による照合であり、MNAとは異なる線形方程式の組立てを用いるが、同一集中定数物理モデルを共有する。EM検証や高調波生成モデルではない。

仕様適合する新しいLPF候補を発見したわけではない。Phase 3は停止中。
