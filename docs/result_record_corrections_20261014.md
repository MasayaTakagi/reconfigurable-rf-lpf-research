# Phase 2 証拠の整合性調査と時点訂正（2026-10-14）

## 基準と範囲

正本は現行 `docs/chatgpt_project_instructions.md`、RF-F002正式制約とtrial RF-T004の台帳。観測された元のREADME、manifest、checkpoint、Gitコミット履歴を区別する。本書は**訂正記録**であり、過去のREADME、数値チェックポイント、manifestを遡及上書きしない。今回は保存物と版履歴の照合だけで、独立RF計算を実行したことにはならない。

## ERR-001：EXP-017 IL=0.301248245dBの減衰要求の誤記

**確認済み事実:** `experiments/chatgpt_topology_search/runs/EXP-017/README.md`の「30dB必須条件での近接値」節には、LQW04×4・面積13⅓の別の局所解について次を記録している。

- 最悪IL：**0.301248245dB**
- H2最小：**30.005dB**
- H3最小：**30.004642dB**
- 有限グリッド：各独立周波数区間7001点、代表84点の独立MNAを実施したと**README上に報告**

したがって、この点を35dB公称目標の候補として列挙するのは誤り。文書`docs/rf_f002_full_lpf_phase2_20261013.md`の一部にある「35 dB candidate reported near IL=0.301248245 dB」等の表現は、**上記READMEに照らし30dB報告点へ訂正して読む**。

`data/validation/rf_f002_checkpoint_reproduction_20261014/summary.json`の`unavailable_requested_checkpoint`にも35dBという古い説明が残るが、当時の追試記録として保存する。回路の完全なL/C/配置/6設定可変Cベクトルは現行mainで未確認で、**30dBでも35dBでも再現された候補とは呼ばない**。旧`data/validation/exp017_20261012/checkpoints.json`はRF-F001非標準ケースであり代用不可。復元または新実験による独立再計算までは統合候補台帳へ昇格させない。

## ERR-002：EXP-016 READMEとmanifestの実行状態不一致

**原因に関するGit履歴の事実:**

| 保存物 | 最初に保存したコミット | 時点における位置づけ |
|---|---|---|
| `EXP-016/manifest.json` | `b3dfb114bd53` | source-only inventoryとして、`execution=unknown`, `numerical=not_run`, `independent=not_run`, `evidence=[]` |
| `EXP-016/checkpoints.json` | `eb155972b573` | 数値候補の保存、READMEと検証コードは別コミット |
| `EXP-016/README.md` | `bfbdb33c41bc` | RF-T004有限探索の実施内容と照合を**文章で報告** |
| `EXP-016/ADDENDUM_2026-10-14.md` | `3a02d1bdd218` | 追加探索、7001点/区間・84代表点独立MNAを**文章で報告** |

従って「READMEでは実行済み、manifestでは未実行」は、**manifest作成時に確認できた証拠と、後から保存された結果が異なる時点のもの**と整合する。ただし当時のGit上の先後関係だけで外部数値実行の実際の成功や元ローカル環境の再現性まで実証はできない。

`EXP-016/checkpoints.json`には4候補の完全な固定L/C・可変C 6設定ベクトルがある。READMEと追補は別実装の有限grid/MNA照合を報告するが、`EXP-016/verify.py`のuv固定環境CI実行は追補時点で明示的に未実施。manifestの`not_run`は**作成時点の証拠状態として保存**し、後から`passed`へ書き換えない。

**次に必要な証拠:** RF-T004実効制約ハッシュとチェックポイントのロード検証、`verify.py`のuv固定環境での実行と代表点独立MNA照合のログ、出力のSHA/使用したGit SHA。追加検証が成功した場合は別の検証記録（新EXPまたは別versionのvalidation record）を作成する。

## ERR-003：EXP-034～037 warm-start結果の誤比較防止

`docs/rf_f002_full_lpf_phase2_20261013.md`では、EXP-034～037の一部にcanonical terminal remap不備があったと明記。中断・再開、worker比較の観測は目的を限定して保持可能だが、該当taskを保存回路から正しく再最適化した候補として用いてはいけない。EXP-038以降のcorrected importerで確認したものと分離する。

## 運用上の対応

- 元のJSON、失敗run、過去の誤記は削除・暗黙訂正しない。本書に「元記録／訂正／未検証」を明記する。
- 39実験全体の現行manifestの状態を、`data/experiment_evidence_inventory.csv`に読み取り専用で投影する。**manifestのevidenceが0件でも結果が未実行と確定するものではない。**
- 完了・passed・reported_in_sources・screened・unknown・not_runを混同しない。
- RF-F002とRF-T004、30dBと35dB、`matching_only`と`full_lpf`を分離する。Phase 3は停止したまま。
