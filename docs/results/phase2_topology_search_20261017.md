# Phase 2 W2: トポロジー・結合符号の検索索引（2026-10-17）

**既存24候補を出典SHAで参照する派生索引。新たなRF解析結果ではありません。**
正式RF-F003と試験RF-T005を分け、kの符号・コイル順を元の報告ラベルとして記録する。
結合の物理的同時実現性、EM、SRF、Q(f)、公差の検証ではない。

| ID | 制約 | 回路系列 | 接続の出典種別 | コイル順ラベル | k符号ペア |
|---|---|---|---|---|---|
| T005_3L_A3_EXP043 | RF-T005 | 3L_shunt_L | own_prose | unknown | L0-Ls:+;Ls-L1:- |
| T005_3L_A3p667_EXP045 | RF-T005 | 3L_shunt_L | own_structured_edges | L0;Ls;L1 | L0-Ls:+;Ls-L1:- |
| T005_3L_A4p333_EXP043 | RF-T005 | 3L_shunt_L | not_stated_in_own_checkpoint | unknown | L0-Ls:+;Ls-L1:- |
| T005_4L_A4p667_EXP042 | RF-T005 | 4L_EXP042_related | related_EXP047_only_not_independently_confirmed | L0;L1;L3;L2 | L0-L1:+;L1-L3:+;L3-L2:- |
| T005_4L_A5p333_EXP042 | RF-T005 | 4L_EXP042_related | related_EXP047_only_not_independently_confirmed | L0;L1;L3;L2 | L0-L1:+;L1-L3:+;L3-L2:- |
| T005_4L_A6_EXP042 | RF-T005 | 4L_EXP042_related | related_EXP047_only_not_independently_confirmed | L0;L1;L3;L2 | L0-L1:+;L1-L3:+;L3-L2:- |
| F003_4L_A4p667_EXP047 | RF-F003 | 4L_EXP042_related | own_prose | unknown | L0-L1:+;L1-L3:+;L3-L2:- |
| F003_4L_A5p333_EXP047 | RF-F003 | 4L_EXP042_related | own_prose | unknown | L0-L1:+;L1-L3:+;L3-L2:- |
| F003_4L_A6_EXP047 | RF-F003 | 4L_EXP042_related | own_prose | unknown | L0-L1:+;L1-L3:+;L3-L2:- |
| F003_4L_A6p667_EXP047 | RF-F003 | 4L_EXP042_related | own_prose | unknown | L0-L1:+;L1-L3:+;L3-L2:- |

## 利用方法と限界

- [構造CSV](../../data/catalog/phase2_topology_search_20261017.csv)のcatalog_idを
  [元24候補性能CSV](../../data/catalog/phase2_candidate_catalog_20261017.csv)へ結合する。
- topology_family、electrical_inductor_edges、reported_physical_inductor_order、signed_coupling_pairsで検索できる。
- 旧14候補の値は未抽出であり、回路構造が存在しないという意味ではない。
- related_EXP047_only_not_independently_confirmedは別EXPの同一系列記述であり、
  個別checkpointsで接続が証明された意味ではない。
- kの符号は数値ベクトルの正負であり、実PCBでの磁気結合の向き・実現性を証明しない。

再生成: python scripts/build_phase2_topology_search.py [--check]

**研究Phase 2継続。Phase 3へは移行していません。**
