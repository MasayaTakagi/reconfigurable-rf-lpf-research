# EXP-024 — RF-T004未統合研究ブランチの選別記録（Phase 2、2026-10-14）

**状態：既存の3研究ブランチから実行済みと報告された候補と記録をmainへ収容したアーカイブ。今回、新たな最適化・独立MNA再実行・物理実装検証は行っていない。** 正式条件RF-F002は変更しない。Phase 3は未承認・未着手。

## 背景とID衝突
mainでEXP-016は別のRF-T004回路探索、EXP-017は**正式RF-F002**探索、EXP-020は旧PR #38の研究系列、EXP-021/022は別のRF-T004探索、EXP-023は正式RF-F002の記録として使用済み。
したがって旧ブランチのEXP-016/017/018をmainの同名フォルダへ上書きしない。元README/JSONを下記のサブディレクトリへ内容を保ってコピーした。

| 原ブランチ (head SHA) | 本アーカイブ | 元の主張と位置づけ |
|---|---|---|
| `research/rft004-chatgpt-phase2-20261014` (`4e45574dfbabbc7821ae81e2d8606549e6130ce1`) | `initial/` | W03: 面積10、最悪IL0.290638dB、H2/H3約30.02dB。W023: 面積12、IL0.280576dB、H2/H3約30.02dB。 |
| `research/rft004-exp017-l-w3-followup-20261014` (`fd4af4e083d2d46012f82ff215de007bca391889`) | `lqw_followup/` | W3-F4: 面積8⅔、IL0.298356dB、H2/H3約30.02dB。W3-F4-k012: IL0.298755dB。 |
| `research/rft004-exp018-cost6-20261014` (`31bf90dc8f8d721a35e65532bcdebd54101b0166`) | `cost6/` | 面積6のPCBパターンC 1/2/3個候補：最良IL0.330120dB、H2/H3約30.10dB。IL≤0.30dB未達。 |

上記は**原ブランチが報告した数値**であり、今回の統合操作による追試ではない。各JSONに6設定可変C値とL/C/kが保存されている。各元READMEの「未マージ」は作成時点の記述であるため、統合後の状態として読み替えない。

## 評価条件と制約上の注意
試験条件RF-T004（正式RF-F002固定ベース）。対応する現在のresolved fingerprintは`c66302a281a1fdb88da355fc44dac1ef3b1c4e18e8ff297db9e842b219b5b0c4`。入力50Ω、負荷60−j40Ω、6設定のUL/DL全域とH2/H3各不連続帯域。LQP02HV Q25、LQW04 Q33（**仮定**）、GJM Q80、PCB-C Q40、IC可変C Q50（3枝・各0–1.5pF）、隣接チップLのみ|k|≤0.15の一定Q集中定数モデル。

実部品のLQW04公称値の利用可能性・Q(f)・SRF、異種部品の結合を含むEM/レイアウト、PCBパターンC寄生・面積、公差、大信号および周波数連続区間の厳密極値は**未検証**。30dBの試験数値達成を正式RF-F002の35dB達成と混同しない。EXP-020の35dB条件で面積13⅔・IL0.297114dBという先行の独立検証済み基準も置換しない。

## 検証器・再現性
`cost6/original_verify.py`は元ブランチのソースをGit blobとして完全保存。`cost6/verify.py`はアーカイブへの移動に伴いリポジトリルート探索（`parents[4]`→`parents[5]`）のみを変更した移植版。次で3個の面積6候補を、各区間7,001点・枝電流9×9 MNAで再評価可能：

```bash
OPENBLAS_NUM_THREADS=1 uv run python experiments/chatgpt_topology_search/runs/EXP-024/cost6/verify.py
```

**上記の移植版スクリプトは作成時点で未実行**。原探索コード・全試行ログのGit上完全再現性は未確立。元ブランチの説明・不収束・未実行の区別を維持する。本アーカイブを正式候補インデックス`data/candidate_index.csv`へ登録しない。

## 主な保存物
- `initial/README.original.md`, `initial/W03.json`, `initial/W023.json`
- `lqw_followup/README.original.md`, `lqw_followup/W3-F4.json`, `lqw_followup/W3-F4-k012.json`
- `cost6/README.original.md`, `cost6/C6_1PCB_H30p1.json`, `cost6/C6_2PCB_H30p1.json`, `cost6/C6_3PCB_H30p1.json`
- `manifest.json`（正規制約スナップショットと保存元コミット・未知項目の区別）

元ブランチは削除せず、mainへの選別研究アーカイブのみ先に統合する。
