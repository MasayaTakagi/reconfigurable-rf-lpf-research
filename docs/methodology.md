# 解析方法

共通MNA解析器: [src/lpf/circuit.py](../src/lpf/circuit.py)。RMSフェーザで各L枝の電圧降下を ZL I として解く。ZL=diag(ωL/Q)+jωM、Mij=kij√(LiLj)。C枝は ZC=(1/Q−j)/(ωC)。電源は50Ωのテブナン電源、負荷は60−j40Ω。

Pavs=|Vs|²/(4Rs)、Pload=|Vload|²Re(1/Zload)、IL=−10log10(Pload/Pavs)。反射電力は|Vs−2Vin|²/(4Rs)。Pavs=Pload+Pref+ΣPL+ΣPC を検証する。

結合の制約チェックは [src/lpf/validate.py](../src/lpf/validate.py)。実際の配置、巻線極性、寄生、SRFの検証は別途必要。MNAは任意の集中定数枝グラフの解析基盤であり、トポロジー探索、複数初期値最適化、全帯域極値の厳密保証は未実装。

6設定UL/DLの最大ILとULのH2/H3全域の最小減衰を分離して報告。matching_onlyとfull_lpfは同列比較しない。旧結果は新仕様への適合が未検証であり、Phase 3は停止中。
