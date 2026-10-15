# Phase 2 / EXP-017 30dB近接報告点の原ソース追跡（2026-10-15）

## 追補（2026-10-15）：正式RF-F002の原ベクトルを回収し、独立MNA追試PASS

**旧記録の「未回収／RG-001 open」は本段落追加より前の調査時点の状態。以下が現在の更新結果であり、旧文書・元manifest/元READMEを改竄しない。**

- ユーザー提供 `EXP-017_RF-F002_loss_exploration_20261014.zip`（157,492バイト、SHA-256 `e685e918a4592a9ec53ffb8221c8b4d59fdf8604dd9119cf3cabbf42174a0daf`、26メンバ・CRC PASS）から、元候補 `EXP-017/EXP017-LQW4-H30-NEAR.json`（2,959バイト、SHA-256 `fa997fb131a1237c41ec8a42ead80e40fe2436275a7e944837afecea9c387896`）を確認。23要素の全最適化パラメータ、LQW04×4、固定GJM×2/PCB C×1、物理順序L0,L1,L2,L3、隣接k3、6設定×2枝の可変Cが記録されている。
- 元ZIPには、24+44+33+172+132+48＝**453局所最適化試行のデータ**と元Pythonスクリプトも存在。ただし今回は**元の453回を再最適化したわけではない**。比較用に供給されたもう一つのZIP `rff002_phase2_exploration_20261014.zip`（84,505バイト、SHA-256 `24fa1dd5f41cbe708ef3360f621b13b83b6c2afaa7bf0b2335bf48c0f6f8b4f7`）は**EXP-016**の元データであって欠落点の置換ではない。
- 新規のGit上の派生チェックポイント：[EXP017-LQW4-H30-NEAR.recovered.json](../experiments/chatgpt_topology_search/runs/EXP-017/EXP017-LQW4-H30-NEAR.recovered.json)。**元ZIPのバイトそのものと同一ではない正規化表現**である。元ZIPのSHAとmember SHAを保持。
- **ZIP内の回収候補JSON原本もバイト同一で保存済み**：[EXP017-LQW4-H30-NEAR.original.json](../experiments/chatgpt_topology_search/runs/EXP-017/EXP017-LQW4-H30-NEAR.original.json)。Git blob SHA-1 `bf69321254fe22c89ad76e90388698fe7339b337`、原ZIP内2,959Bの SHA-256 `fa997fb131a1237c41ec8a42ead80e40fe2436275a7e944837afecea9c387896`と一致。原ZIP全26ファイルのサイズ・SHA256を[出典インデックス](../data/exp017_rf_f002_source_zip_index_20261015.json)へ登録。**残り25の元memberやZIPバイナリそのものはGitへ追加しておらず、全探索履歴をGitから復元できるとは主張しない。**
- 元ZIPの全26member目録は `data/exp017_rf_f002_source_zip_index_20261015.json` に保存済み。原ZIPを保持している環境では、`python scripts/verify_exp017_source_zip.py --zip EXP-017_RF-F002_loss_exploration_20261014.zip`で**ZIP全体と26ファイルのSHA-256を展開・コード実行なしで照合**できる。元ZIPをGitへコミットしていないため、**GitHub CIがZIP全26memberの現物を直接再検査したわけではない**。Gitに保存した2,959B元JSONはCIで実バイト照合できる。
- 元ソースから独立して作成した `scripts/verify_exp017_recovered_mna.py`による**9×9枝電流MNA**と**5×5ノード方程式**のクロスチェックを、`data/bands.csv`の28のUL/DL/H2/H3個別周波数区間×**7,001点**で実行（**計196,028回の複素回路解析**）。[検証summary](../data/validation/exp017_rf_f002_recovered_20261015/summary.json) に6設定の数値・発生周波数・環境を保存。
- **再評価最悪IL 0.3012482451489075dB、H2最小30.004999999986865dB、H3最小30.004641701571376dB。** K最小固有値0.8351878156601953、最大電力収支残差1.8214596497756474e−17W、5×5式との最悪IL差1.1937117960769683e−11dB。**元報告と一致。30dBの有限格子判定PASS。IL目標0.30dBは未達。**
- 旧EXP-017 `manifest.json` は変更せず、研究候補台帳に `EXP017-LQW4-H30-NEAR`を追記する。これにより**RG-001「欠落した正式回路ベクトル」の問題は解決**し、ソースZIPの原本バイナリGit保管・全453件再実行・連続帯域極値保証・SRF/Q(f)/EM/寄生/公差の物理実証は**未完了**と区別する。RF-T004の試験3可変Cの成果と混同しない。

## 適用範囲・判定

- 調査基準は main commit ad1cda8c47054fbe97edc5b8bb97261804281285（PR #52の統合後）、運用正本 docs/chatgpt_project_instructions.md、現行正式RF-F002、帯域 data/bands.csv。
- 対象はEXP-017 READMEに記載された「30dB必須条件、LQW04×4、面積13⅓、IL=0.301248245dB、min H2=30.005dB、min H3=30.004642dB」の局所解。
- **現時点の判定：数値はREADME/PR本文の報告として存在するが、完全な回路パラメータと6設定の可変Cベクトルは確認できず、独立再計算は実施できない。RG-001はopen。**
- 「GitHub上で確認したrefsに未保存」は「当時のチャット添付ZIPや手元のバックアップから永久に復元不能」と同義ではない。本調査で外部ZIPの内容確認は行っていない。

## GitHub上の実施済み調査

| 調査対象 | 観察できた事実 | 解釈の限界 |
|---|---|---|
| [PR #41](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/pull/41)のFilesとコミット9件 | PRの7変更ファイル中、EXP-017の完全候補JSONとして保存されたのは EXP017-LQW2-H35.json（35dB、IL約0.378798dB）だけ。READMEには別の30dB近接報告値がある。 | PR説明の「8種類の高密度チェックポイント」は、全8件がGitへ完全ベクトルとして保存されたことを意味しない。 |
| EXP-017/README.md | 30dB近接値のIL・H2・H3と元の7001点/84点MNA**報告**、合計453局所試行、生データを当時のチャット成果物ZIPへ保管した旨。 | このREADMEのテキストだけでは回路のL/C、結合、配置、6設定ごとのCvを復元できない。 |
| EXP-017/EXP017-LQW2-H35.json | 別の35dB候補の完全なモデルと6設定を保存。data/validation/rf_f002_checkpoint_reproduction_20261014/summary.jsonで7001点/区間の数値再計算が記録されている。 | 30dBのLQW04×4、IL=0.301248245dBとは別候補で代用不可。 |
| data/validation/exp017_20261012/checkpoints.json | RF-F001参照・NONCANONICAL_UNAPPROVEDの旧別実験記録。 | RF-F002の30dB近接候補へ昇格させない。 |
| EXP-020/source_pr38/EXP-017/EXP017-35P008.json | PR #38由来の別資料。RF-T004という試験条件の保存スナップショット。 | 現行正式RF-F002 2可変Cの30dB近接点ではない。 |
| 現行mainの再帰Git tree | 追跡ファイル731個（取得時truncated=false）、EXP-017関連ソースと保存候補をパス単位で照合。 | パス・既存ソース確認であり、過去の未到達Gitオブジェクト全件探索ではない。 |
| 現存するmain以外の6ブランチ | 各headの再帰Git treeをmainと比較。EXP-017の未登録候補ファイルパスの追加なし。各headでEXP-017元ファイルの変更も確認されなかった。 | 消去済み過去ブランチの内容や、外部チャット添付ZIPはこの検査範囲に含まない。 |

EXP-017 READMEを導入したPR #41コミットは [94ef858450956477410e6263a62a3809c4827a0d](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/commit/94ef858450956477410e6263a62a3809c4827a0d)。PR #41はMERGEDで、PR本文もこの近接値を明確に**30dB条件**として扱う。READMEに列挙された保存候補は35dBのEXP017-LQW2-H35.jsonだけであり、数値的に似ている別チェックポイントは補完根拠にならない。

初期レビュー時の35dB表記は [docs/result_record_corrections_20261014.md](result_record_corrections_20261014.md) で訂正済み。一方、data/validation/rf_f002_checkpoint_reproduction_20261014/summary.jsonの旧説明欄には35dBの誤表示が履歴として残る。元ファイルは改変せず、読み替え根拠を現在の訂正文書で維持する。

## 2026-10-15追加調査：ユーザー提供のRF-T004 EXP-017チャットZIP

**ファイル:** `RF-T004-EXP017-bundle.zip`（今回のチャット添付。GitHub mainの保存ファイルと同一であるとは仮定しない）。`SHA-256=48175d3579d3814e5d3740858ee3959b88e9731b835cb2cd306ce6b0093ae640`、118,646 bytes、35 ZIP entries、展開後合計475,557 bytes。ZIPのCRC検査は**PASS**。元ZIPの中身はこの時点でGitHubへアップロードしていないため、本記録とSHAだけではCIから元ZIPを取得・完全再検証できない。

### 制約クラス判定

報告書・保存候補・元探索ソースに明記された条件は `RF-T004`（RF-F002をベースに**最大3可変C**を許した試験条件）。探索219局所試行を報告し、30dB/35dBの探索結果・Pythonコード・ログを含む。しかし今回探している正式RF-F002のEXP-017 **IL=0.301248245dB、30dB必須、2可変C**の完全ベクトルとは**別の実験**である。ZIP内の全テキストを調べても `0.301248245` および数値断片 `301248245` は検出しなかった。このZIPの発見により**RG-001を解決済みへ変更してはならない**。

ZIP内の `data/bands.csv` は最新mainのGit blob SHA-1 `80ad91c456bda439a6c40ce431df26a8128a6a36` とバイト一致した。保存済み候補 `EXP017-35P008.json` は5個のLQW04（設計仮定Q33）、4個の固定GJM01、3個の可変IC Cで、各6設定のCv値を保持。GitHubのPR #38由来のEXP-020/source_pr38アーカイブにある同一IDの拡張JSONと**Lの5値、物理一列順序、4結合係数、4固定C、6設定×3可変Cの全数値が一致**する。ただしZIP内の短縮JSONとGitHub上の拡張JSONは**バイト同一ではない**。ZIP全35エントリのGit blob SHA-1と最新mainの731追跡ファイルを比較すると、**完全バイト一致は同梱のdata/bands.csvの1件のみ**（34エントリはmainに同一Git blobなし）。この34件には別表現で既存資料を表すものも含まれるため、すべてを独自研究成果と断定しない。原ZIPを失わないよう別アーカイブ方針が必要だが、既存Git資料への同名上書き・重複の無検討追加は避ける。RF-F002の候補台帳へ昇格させない。

### 今回の再実行結果（元の報告とは区別）

ユーザーZIPに含まれる `verify_checkpoint_exp017.py` と `EXP017-35P008.json` および同梱 `data/bands.csv` のみを作業フォルダへ複写し、元ソース**無修正**で以下を実行した（2026-10-15）。Python/NumPyのローカル実行でありGitHub Actionsではない。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_checkpoint_exp017.py EXP017-35P008.json --bands data/bands.csv --points 14001
```

| 指標 | 今回の算出値 |
|---|---:|
| 6設定・全パスバンドの最悪IL | **0.2999624819232782 dB** |
| H2全区間の最小減衰 | **35.0079968600488 dB** |
| H3全区間の最小減衰 | **35.00799999967868 dB** |
| 磁気結合行列Kの最小固有値 | 0.7851275840330142 |
| 独立枝電流MNA照合点 | 84 |
| 最大節点電圧差 | 6.24198150805748e-15 V |
| 最大電力収支残差 | 1.745565497701662e-17 W |
| 保存値からの差分 | 1e-6dB以下、**検証スクリプトPASS** |

各帯域区間14,001点の有限格子検証。**同一ZIP内の保存値と同梱コードの再実行**であり、第三者実装による完全独立ソルバでのクロスチェックや回路大域最適性、連続帯域の極値保証ではない。周波数依存Q/SRF/EM/寄生/実装可能性と公差合格率も未検証。IL目標との差は約0.000037518dB、減衰35dBに対する最小余裕は約0.007997dBと非常に狭い。

**アクション:** RF-T004の外部生証拠ZIPとしてSHAとユーザー提供元を記録。次のリポジトリ保管最適化で、既存PR #38保存物との重複・独自の生ログとコードを区別し、バイト原本をどこに保全するか判断する。**このZIPからRF-F002欠落ベクトルが復元できたという主張は禁止**。

## RG-001の解決ゲート

1. 453試行のチャット成果物ZIP、当時のローカルバックアップ、元PRの保存先から欠落チェックポイントを回収できるか**外部ソースを別途調査**する。今回、このZIPは入手・展開できていない。
2. 回収できた場合、元ソースのハッシュ、取得元、保存日時、RF-F002実効制約SHA、目的30dB、完全なL/C/結合/チップ配置、6設定Cvを照合し、候補を新たな派生記録として保存する。元manifestや既存実験JSONは遡及変更しない。
3. その後、**別の新規数値実行**としてRF-F002の6設定UL/DL・H2/H3全周波数区間を共通周波数格子で走査し、独立枝電流MNA、SPD・電力収支を検証し、収束/未収束も分けて報告する。
4. 実元ソースが回収できなければ、文書の報告点という位置づけを保持したまま、正式な統合候補/達成候補への昇格を禁止し続ける。探索で類似値が出ても**元の回路の再現**と呼ばない。

## 関連する未完了事項

- 正式RF-F002、30dB strictの登録最小ILは約0.381014dB、35dB strictの登録最小ILは約0.378798dB（data/research_candidate_register.csvにある選別13件の各区分内の値）。当該0.301248245dBは未保存ベクトルなのでこのParetoへ追加できない。
- RF-T004の0.297114dBは3可変C試験条件であり、RF-F002の達成ではない。
- 原ZIP再収集、元の全453試行の再現、新規RFシミュレーション、連続帯域の数学的保証、Q(f)/SRF/寄生/EMの物理検証は**今回未実行**。
- Phase 2を継続し、Phase 3へ移行しない。

本書はGitHubの保存ソース・履歴照合による調査記録であり、「外部ソースが存在しない」「元報告の数値が誤り」との断定ではない。
