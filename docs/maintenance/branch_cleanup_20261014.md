# GitHub不要ブランチ監査・削除記録（2026-10-14）

対象: `MasayaTakagi/reconfigurable-rf-lpf-research`
実施者: pi coding agent（所有者認証済みGitHub CLI）
本記録はGitHub mainへPR経由で保存。

## 結果概要

- 作業開始時に取得した最新main: `c17f471a81334effe17119b3859d94686d629bae`（PR #44統合後）。ローカルmainをresetせず、mainをforce-updateせず、削除せず。
- 削除前GitHubブランチ: 27本（mainを含む）。Open PR: 0本。
- 削除: 26本。削除失敗: 0本。最終的に保持したリモートブランチ: `main` のみ。
- PR #38のブランチは当初保留。未統合の研究アセットをmainのEXP-020配下へ補完保存するPR #45をsquash mergeし、内容・チェックサム・PR状態を再確認した後に削除した。
- PR #45後のmain: `9ef84d8924a44497e51c44d8d1fac494c116fa26`。PR #45はsquash mergeで、不要な複数親Merge Commitは作成していない。
- PR #45のPhase 2 regression CIは成功（Actions run `38548773857`）。PR上のaudit checksも2件とも成功。
- ブランチ削除後のGitHub一覧取得: `main` — `9ef84d8924a44497e51c44d8d1fac494c116fa26` の1本。

## バックアップ

削除前に全リモートブランチをfetchし、以下のbundleを作成・検証した。GitHubリポジトリには追加していない。

- 保存先: `/home/user/backups/reconfigurable-rf-lpf-research/branch-cleanup-20261014.bundle`
- サイズ: 5.6 MiB
- `git bundle verify`: PASS（complete history、35 refsを収録）
- SHA-256: `0be447f9c564fb8efe4322e1cc82b14b76ec7301c3a0d474481db1a7f6ab45c2`
- bundle中に削除対象ブランチの元ref/SHAが存在することを `git bundle list-heads` で確認。例: PR #38先端 `3ec530c3bcfa7678415659ed5dee6f27ea2e889c`、EXP-024元ブランチ3本の各先端。
- bundleは削除直前に作成済み。bundle内のmainは作成時の `c17f471...`。後続のPR #45 squash commit `9ef84d...` は削除対象ではなく、GitHub mainに保持されている。削除復元用の対象ブランチ履歴はbundleに含まれる。

## 削除前一覧とDry Run判定

ahead/behindは、削除直前のmain `9ef84d...` に対するGitグラフ上の件数（`main...branch`）。Squash merge済みブランチでは元コミットがmainの祖先でないことがあり、件数だけで未統合とは判定せず、PR merge履歴とmain上の保存内容を確認した。

| 削除前ブランチ | 最新SHA | PR / 状態 | ahead / behind | mainとの差分path数 | Dry Run / 実行判定 |
|---|---|---|---:|---:|---|
| `chore/constraint-versions-pareto-cost-20261012` | `e3c700e264953faa6574636ea1965d51bd9b1016` | #21 MERGED | 11 / 157 | 25 | 削除: PR統合済み |
| `codex/r1-constraint-experiment-provenance` | `cb23d2858826b9eb393ddda037d3bd202b1921c0` | #22 MERGED | 2 / 156 | 32 | 削除: PR統合済み |
| `fix/issue-36-branch-current-scaling` | `21fd1ad8417126a782dd32dc9b73a10d5c726fd1` | #37 MERGED | 0 / 50 | 0 | 削除: PR統合済み |
| `fix/rft003-verifier-resource-warnings` | `1a25cb992beb080f53854ca1093274984b1a328e` | #39 MERGED | 0 / 58 | 0 | 削除: PR統合済み |
| `infra/local-runner-stage2` | `45929992cf1f2508a6fa7ddb01c09a81378f7b29` | #35 MERGED | 0 / 52 | 0 | 削除: PR統合済み |
| `integration/exp024-rft004-unmerged-checkpoints-20261014` | `76f210995a1d44ff8c3533e0e0edb2e0cb5cf00c` | #44 MERGED | 2 / 2 | 15 | 削除: PR統合済み、EXP-024内容を照合 |
| `main` | `9ef84d8924a44497e51c44d8d1fac494c116fa26` | — | 0 / 0 | 0 | **保持（削除対象外）** |
| `policy/trial-three-variable-c-20261012` | `0e4516e263daa0eb8116d8fb1126f0deb293d965` | #23 MERGED | 3 / 155 | 12 | 削除: PR統合済み |
| `r2/pr-b2b-explorer-20261012` | `0ad9983717f51c29d062b27a12519d380dda6bab` | #26 MERGED | 0 / 145 | 0 | 削除: PR統合済み |
| `r2/pr-b3-independent-exp015-20261012` | `cd4ae63b6526ead3df66304ba5e78e87209c3c25` | #27 MERGED | 0 / 140 | 0 | 削除: PR統合済み |
| `r2/pr-b4-actions-smoke-20261012` | `2263c85fd07f6dca5483ece973d95f2e2e0db02b` | #28 MERGED | 0 / 136 | 0 | 削除: PR統合済み |
| `r2/shared-hv-hq-variable-c-core-20261012` | `bc093c30400525534928addc96d50f3adacfb6f6` | #24 MERGED | 0 / 150 | 0 | 削除: PR統合済み |
| `research/exp016-initial-screening-20261012` | `db32172f3e370cfc93fef8a067881706ad169873` | #25 MERGED | 7 / 154 | 7 | 削除: PR統合済み |
| `research/exp016-rff002-initial-phase2` | `ffd0de01f55fabc4376865c3a3d4a5a583367f29` | #40 MERGED | 0 / 5 | 0 | 削除: PR統合済み |
| `research/exp017-rff002-loss-optimization` | `1acd6792a91fda0ec4cd9ee7af43246bd46a0531` | #41 MERGED | 0 / 36 | 0 | 削除: PR統合済み |
| `research/exp017-two-variable-c-shunt-merge-20261012` | `ccdd7d9f8edd6de41083ec9dbef6041422043af4` | #29 MERGED | 5 / 154 | 4 | 削除: PR統合済み |
| `research/exp021-rft004-area6-20261014` | `5c376f6bfca0f1870006dd60632f789fce561019` | #43 MERGED | 37 / 21 | 11 | 削除: PR #43のEXP-022統合を確認 |
| `research/rf-t003-30db-authorized-20261012` | `0e2e249fb86752f2aad759c47bbe15a3db054d0d` | #30 MERGED | 10 / 154 | 10 | 削除: PR統合済み |
| `research/rf-t004-chatgpt-phase2-20261013` | `3ec530c3bcfa7678415659ed5dee6f27ea2e889c` | #38 CLOSED・未merge | 20 / 60 | 19 | **初期保留**。PR #45でユニーク資料を保存後、SHA/状態を再確認して削除 |
| `research/rf-t004-exp020-reviewed-archive` | `f8cf695a52a4d0f7317f61a431f5debe773cb97d` | #42 MERGED | 11 / 25 | 10 | 削除: EXP-020統合済み |
| `research/rft003-5l-low-loss-20261013` | `dbc27cf8b1e26dad6225ef608215248247f424a0` | #32 MERGED | 5 / 131 | 4 | 削除: PR統合済み |
| `research/rft003-7l-three-pcb-030-20261013` | `335a3f117e0ee1a3743035adfc08f58a75054573` | #34 MERGED | 0 / 61 | 0 | 削除: PR統合済み |
| `research/rft003-coupling-row-optimization-20261013` | `d850ed551de5301033e243223b14a309db2f04bb` | #33 MERGED | 0 / 108 | 0 | 削除: PR統合済み |
| `research/rft003-loss-breakdown-20261012` | `e00bc7ae628eeedc33b7677c87d46cc6dc0ea433` | #31 MERGED | 3 / 131 | 3 | 削除: PR統合済み |
| `research/rft004-chatgpt-phase2-20261014` | `4e45574dfbabbc7821ae81e2d8606549e6130ce1` | PR #44でEXP-024へ統合 | 3 / 45 | 3 | 削除: checkpoints/READMEをmainと照合 |
| `research/rft004-exp017-l-w3-followup-20261014` | `fd4af4e083d2d46012f82ff215de007bca391889` | PR #44でEXP-024へ統合 | 3 / 44 | 3 | 削除: checkpoints/READMEをmainと照合 |
| `research/rft004-exp018-cost6-20261014` | `31bf90dc8f8d721a35e65532bcdebd54101b0166` | PR #44でEXP-024へ統合 | 5 / 21 | 5 | 削除: checkpoints/READMEをmainと照合 |

## 特別監査：PR #44 / EXP-024

PR #44はmain `c17f471...` に統合済み。削除前に元ブランチとEXP-024保存先のGit blob ID（SHA-1）を直接比較し、対象JSONとREADMEの内容が完全一致することを確認した。これはファイルの同一性確認であり、回路値の新たな数値再検証ではない。

| 元ブランチ | EXP-024保存先 | 一致したblob ID |
|---|---|---|
| `research/rft004-chatgpt-phase2-20261014` | `EXP-024/initial/W03.json` | `8f393cf1613595a00e77dfc65c708a0fe79c4c9e` |
| 同上 | `EXP-024/initial/W023.json` | `d6efba593600db36ea8388f806d75bf6972efa34` |
| 同上 | `EXP-024/initial/README.original.md` | `b50b6e195a87f47fb98e57e0e5349bf2e12bdcb1` |
| `research/rft004-exp017-l-w3-followup-20261014` | `EXP-024/lqw_followup/W3-F4.json` | `5bf7d77b6dd8ae51e93a660c78f892ba85f25846` |
| 同上 | `EXP-024/lqw_followup/W3-F4-k012.json` | `93390987ec9bd16cbcaa077216324d2b3bdecaea` |
| 同上 | `EXP-024/lqw_followup/README.original.md` | `ddc6a597cb3d62ab8a70f1ca2b93e311d65a8e54` |
| `research/rft004-exp018-cost6-20261014` | `EXP-024/cost6/C6_1PCB_H30p1.json` | `7a009152d7d89abeeb719bf94f1354e92835d104` |
| 同上 | `EXP-024/cost6/C6_2PCB_H30p1.json` | `62bbcd8f88e03589825787435ca98d36f83c1ce3` |
| 同上 | `EXP-024/cost6/C6_3PCB_H30p1.json` | `7111c740dee7211467443ddd04ff239112523de3` |
| 同上 | `EXP-024/cost6/README.original.md` | `a6304e6e44633c14eb498ade17bd3fdc888ac5e1` |

PR #44のアーカイブ、manifest、検証コードもmainに存在する。EXP-020〜024等の既存記録、候補、索引を上書きしていない。

## 特別監査：PR #38（Closed、未merge）

初期判断を「削除保留」とし、branch-only path 19件を監査した。PR #42でEXP-020に取り込まれた候補と検証器はmainに存在する一方、PR #38最終先端にある旧EXP-019の追加checkpoint、Pareto表、README、manifest等が不足していた。旧IDがmainの別研究と衝突するため、`EXP-020/source_pr38/` へ**元内容のまま**追補保存し、main上のEXP-016/017や正式索引を置換しないようにした。

- 保存PR: [#45](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/45)、squash merge SHA `9ef84d8924a44497e51c44d8d1fac494c116fa26`。
- 保存内容: PR #38先端の旧EXP-016〜019 README、manifest、checkpoint、Pareto表、検証器の計17ファイル。内容は `source_pr38/SHA256SUMS` で検証し、17件すべてPASS。
- 特に旧 `EXP019-1W7L-C11.667.json`（面積11⅔、source-recorded IL 0.3148244235472347 dB、H2/H3は約35.01 dB）と旧 `EXP-019/pareto.csv` を保存。source reportでもIL≤0.30 dBは未達、物理SRF/Q(f)/EM未検証。**本監査ではこのcheckpointを数値再実行しておらず、元ファイルに記録された検証状態以上の認定はしていない。**
- 元の `data/experiment_index.csv` は旧EXP-016〜019 IDが衝突するためコピー・再登録せず、PR #42のEXP-020正規記録を維持。#38由来の候補テスト変更は現mainの後続guardrailテストで置き換わっている。
- PR #38は削除直前にもCLOSED・未mergeでhead SHA不変、Open PR利用なしを確認。PR #45はMERGED、内容のchecksum PASS、main CI PASSを確認してから削除した。

## 削除の実行・削除後確認

各ブランチについて、削除直前にGitHub上のref SHAを再取得。PRブランチは対応PRのMERGED状態・head名・head SHAを再確認し、EXP-024の3ブランチはOpen PRがないことを再確認した。PR #38は上記の保存条件を再確認した。全ての削除は**明示した完全なref名と期待SHA**を指定した `git push --force-with-lease=<ref>:<expected-sha> origin :<ref>` によるcompare-and-deleteで実行し、途中でSHAが変わったrefは削除しない設計とした。mainを含むrefを削除対象には指定していない。

GitHubから削除後にbranch一覧を再取得し、結果は `main` 1本のみ。main SHAは `9ef84d8924a44497e51c44d8d1fac494c116fa26`。削除対象の復元手段は上記bundleに残る。

## 不変条件・CI

- `data/constraints/`、`data/design_constraints.json`、`data/bands.csv` は変更していない。
- `candidates/`、既存の実験記録、正式制約、RF-F002/RF-T004の区分は変更していない。追加した資料はEXP-020配下の明示的なPR #38 source archiveのみ。
- Phase 2を維持。Phase 3、新規回路探索、制約変更は実施していない。
- GitHub Actionsのworkflow設定を変更していない。main SHA `9ef84d...` のPhase 2 regressionはPASS。
- PR #45 merge後のbranch削除操作はremote refsに対するもののみ。mainは保持され、reset/force-updateしていない。

## 最終一覧

| 項目 | 結果 |
|---|---|
| 削除前ブランチ数 | 27本 |
| 削除成功 | 26本（マージ済みPR 22本、EXP-024元ブランチ3本、PR #38ブランチ1本） |
| 削除保留 | 0本（PR #38は一旦保留後、必要資料保存と照合の完了後に削除） |
| 削除失敗 | 0本 |
| 削除後ブランチ数 | 1本（main） |
| main SHA（削除後確認時） | `9ef84d8924a44497e51c44d8d1fac494c116fa26` |
| 研究成果保存 | PASS（ファイルSHA/チェックサム照合。PR #38の追加checkpointは本作業で独立再計算していない） |
| Backup bundle | `/home/user/backups/reconfigurable-rf-lpf-research/branch-cleanup-20261014.bundle`、SHA-256 `0be447f9c564fb8efe4322e1cc82b14b76ec7301c3a0d474481db1a7f6ab45c2` |
| CI | PASS（Phase 2 regression、run `38548773857`） |

この記録自体は削除完了後にPRでmainへ追加するため、そのPRのsquashによってmain SHAは記録内の「削除後確認時SHA」からさらに進む。PR branchはmerge時に削除する。
