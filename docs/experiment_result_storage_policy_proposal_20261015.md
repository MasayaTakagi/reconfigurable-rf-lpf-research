# Phase 2：今後の実験結果保存・再現性・アーカイブ運用方針（提案、2026-10-15）

> **状態：提案／未採用。** この文書をGitHubに追加しても、既存実験のデータ移動・削除、正式RF制約変更、Phase 3開始、PR #53マージを許可したことにはならない。運用正本は `docs/chatgpt_project_instructions.md`、正式制約の値は`data/constraints/formal/RF-F002.json`とregistry、周波数は`data/bands.csv`。旧実験の`manifest.json`は遡及改変しない。

## 1. 過去の観測と設計要件

| 観測済みの問題 | 改善する保存ルール |
|---|---|
| EXP-017 RF-F002・30dB・IL=0.301248245dBの**報告値だけ**残り、完全なL/Cおよび6設定Cvと元ChatGPT ZIPが回収できない（RG-001、保留） | 重要候補は発見時に完全な機械可読checkpointとハッシュを保存し、外部原ZIPの保管確認なしに実験を「archived」としない |
| 39実験のうちseed未記録25、実行SHA未記録15、環境未記録16、execution unknown16 | 実験開始前にrun identity/条件/seed/環境を記録。終了時に実行/最適化/検証状態を別々に確定。未確認値は`unknown`にする |
| 6つの元manifestはevidence 0件。補助索引36件が別に存在 | 新規runではmanifest↔元証拠↔SHAを必須とする。旧manifestは変更せず検証overlayとsupplemental ledgerで関連付け |
| EXP-034〜037旧warm-startの端子remap不具合 | インポート元checkpoint SHA、グラフ/端子mapping、元制約、修正revision、実行stageを記録し、bad resultとcorrected runを混合しない |
| RF-T004試験3CとRF-F002正式2C、H2/H3 30/35dB、strict/toleranceを混同しやすい | 制約ID+effective SHA、objective、threshold、validation classを**比較キー**に含め、違う比較キーを自動Paretoに入れない |
| 生実験ファイルとmanager/worker logs/lock、Git blob重複が混在 | 不変研究原本・診断/再開根拠・一時ファイルを**用途と役割**で分類。SHA一致は同じ証拠用途を意味しない |
| Actions成果物は有期限、チャットZIPは別チャットから発見困難 | 一時配布と永続保管を分離し、複写先のhash再確認と**実際の復元試験**を保存終了条件にする |

## 2. 運用上の三層構成と正本

1. **Gitに残す小型正本（A/B/C）**：RF制約、bands、実験/run manifest、出典台帳、候補の完全な回路JSON、独立検証サマリー、比較用の選別台帳、集計結果。これらはレビュー・差分・CIに適している。
2. **外部永続アーカイブ（D）**：全生探索・全iteration/seed・元実行コードのスナップショット・中間checkpoint・生ZIP・診断の要保全部分。**推奨**はバージョニングされた非公開オブジェクトストレージ＋別障害ドメインへの複製、または同等の耐久性を備える保管先。content-addressed（例：`sha256/<hash>.zip`）で不変性を確認。Git LFSでもよいが利用枠、転送量、参照維持、backup、取得テストを事前確認し、Git通常blobに巨大base64は埋め込まない。
3. **作業領域（E/F）**：ローカル`results/`内のraw run、ログ、lock、status、scratch、キャッシュ。動作中は原子書込み・再開性を優先し、終了時に外部保全対象と再生成可能データを分類。**バックアップ検証が終わる前の自動削除は禁止**。GitHub Actions artifactはCI配布/短期一時コピーであり、長期保存の唯一の根拠にはしない。

**原則：Git上のmanifest/保存台帳がインデックス、外部アーカイブのハッシュ照合可能なraw bytesが原本。** 保存先URIだけの記述やSHA文字列だけの記録を「原本保存済み」とは判定しない。アクセス権・機密性・鍵管理はストレージ運用で別途定義する。

## 3. 新規実験の識別と保存パス

- AI主導探索は既存`experiments/chatgpt_topology_search/runs/EXP-NNN/`、汎用探索は`experiments/matching_limit/`を維持。歴史的IDのリネーム禁止。並列stageは別`run_id`（例：`EXP-042/20261015T...-rf-f002-35db-seed0001`）で識別し、全生成物と共通コードSHAを結び付ける。既存リポジトリのパスを**今すぐ移動しない**。
- 各新規runのGit管理文書には`manifest.json`（元実行の記録）、`run_summary.json`（集計）、`checkpoints/<candidate_id>.json`（選別候補）、`validation/<validation_id>.json`（後日別実行、元と区別）、`archive_receipts.json`（原本保管証明）の**役割**を割り当てる。導入時の実ディレクトリは既存`data/validation/`等との互換とリンク整合を検査し決定する。
- 新規候補は「実験番号＋内部run ID＋stage ID＋候補ID」で衝突を回避。名称の再使用、PRや別チャットでの異なる`EXP-017`系列の同一視を禁止。旧IDとの対応は`legacy_origin_id`で明示する。
- 元データの取得元は`git_commit`/`GitHub Actions run`/`local run`/`chat_attachment`等の列挙値、`source_uri`、`captured_utc`、ZIP/各member SHAで記録。保存時のGit SHAと実行時のGit SHAは別属性にする。

## 4. run manifest：実行前に必須のものと終了後に追加するもの

**実行開始前（未実行でも残す）**：

- `experiment_id`、`run_id`、`stage_id`、`phase=Phase 2`、`objective=full_lpf|matching_only|diagnostic`、開始UTC、実行者/実行方式（ChatGPT/WSL2/Actions）。
- `constraint_class=formal|trial|historical`、`constraint_id`、`base_constraint_id`（trial時）、`effective_constraint_sha256`、`bands_sha256`、**減衰要求`required_harmonic_attenuation_db=30|35`**、6設定の設定ID、不連続周波数区間の扱い。
- `execution_git_sha`、`working_tree_dirty`、dirty時の完全patchまたは実コードsnapshotのSHA、`uv.lock` SHA、Python/NumPy/SciPy/BLAS/OS/CPU、および解決済み数値環境。
- `search_space`、グラフ列挙上限、目的関数・loss定義、初期候補、warm-start元候補SHA、**端子/枝/可変C mapping定義とそのversion/hash**、`random_seed`とseedの導出方法、シャード・worker割当て。
- `execution_status=planned`。必要値を取得できない場合は**未記録のままcompletedとせず`unknown`と理由**を記載。run開始前のCI検査では新仕様の必須項目がない場合、実行許可を出さない方式を段階導入する。

**終了時（失敗・中断も記録）**：

- `execution_status=completed|partial|failed|interrupted|not_run|unknown`、開始/終了UTC、elapsed、graph/start/iter/evaluationの計画/実施/成功/未収束/失敗/未実施数、最終solver success/exit code/停止理由、CPU/RSS、再開・retry履歴。
- `archive_status=local_only|upload_pending|uploaded_unverified|verified_restore|lost_or_unavailable` を**execution/validationとは独立**させる。
- `validation_status=not_run|reported_only|finite_grid_passed|independent_mna_passed|physical_validated|failed`を別軸で保持。数値公差による分類`strict_finite_grid|tolerance_only|failed_threshold|not_checked`を別属性にし、`success=False`を性能限界と誤読しない。
- 元コード/生データ/ログ/チェックポイント/検証を`evidence[]`として登録：`role`、`logical_path`、`relative_git_path`又は外部`archive_id`、`sha256`、`size_bytes`、`provenance`、`retention_class`、`availability_status`。**新規runで evidence 0件は「保存完了」と認めない。**
- 新規または後日実施した再検証は**別の検証実行ID/ファイル/コードSHA/条件SHAを持つimmutable overlay**として登録。元source report・manifestを再解釈して上書きしない。

## 5. チェックポイントの最小完全性（EXP-017再発防止）

良好値を発見したときは、報告テキストの前に**完全な回路ベクトルを機械可読JSONとして確定**する。

- 全枝の`component_id`、種別/系列、ノード端子、値、Qモデル、PCB/IC資源、固定GJM/パターンC、各磁気結合の符号・k・物理隣接配置、共有トポロジー。部品ID・ノードIDの意味を安定化させる。
- **6設定すべて**の可変C枝ごとの接続と数値、UL/DLおよびH2/H3の区間ごとの最悪値と周波数、面積算出内訳、悪化ケース、反射・損失の必要な内訳。
- `constraint_id`+`effective_sha`+`bands_sha`+`evaluation_grid`（区間・点数・端点/極値探索）+`solver SHA`+`execution status`を候補に固定する。
- 未収束点、source-reported点、修正前の端子対応失敗runは消さず、`candidate_status`と`validation_status`を分けて保存。未保存ベクトルは**候補登録・Pareto昇格不可**。
- 粗いスクリーニングで全iterationをGitへ登録しない。**各トポロジー/面積/条件群の有望上位Kと境界近傍、反例、失敗原因を示す数例**の完全checkpointはGit登録候補に選別する。それ以外のraw試行・途中全checkpointは外部アーカイブへ保持する。K・選別基準はrun設定に記録し、終了後に恣意的に変更しない。

## 6. 数値結果の比較・昇格条件

- 最低比較キー：`constraint_class + constraint_id + effective_constraint_sha256 + objective + H2/H3 threshold + validation_depth + grid_policy`。`matching_only`と`full_lpf`、RF-F002とRF-T004、30dBと35dBを混在させない。
- **source_reported** は元の報告値。**replay_passed** は同ソースの再実行。**independent_mna_passed** は別実装と高密度6設定UL/DL/H2/H3の全不連続区間・受動性・SPD・電力収支の照合を伴う。さらに**physical_validated**はQ(f)/SRF/部品寄生/実装レイアウト/EM/公差等を別証拠で追補する。これらをまとめて単一の`passed`にしない。
- `strict_finite_grid`と`tolerance_only`の比較を分ける。有限格子内の合格は連続周波数区間の数学的保証や実機合格ではない。
- 正式制約でIL≤0.30dBの認定は、必要な**正式2可変Cの合法回路ベクトル**と独立検証証拠が揃うまで保留。試験3可変C・0.297dB級はtrialのまま維持。

## 7. 原本アーカイブの保存と復旧検査

**保存ハンドシェイク（毎回）**

1. raw探索結果・実コード・実行環境・checkpoint/ログのmanifestを確定し、パスごとのSHA-256、サイズ、件数を記録する。ZIP化する場合は**ZIP全体と全member**のSHA-256とCRC/サイズを記録。
2. バージョニング/削除保護のある外部ストレージに原本を書き込み、`archive_id`、保存場所URI、アップロード日時、保存期限、世代、アクセス権、保管媒体/複製先を領収記録として保存。**ChatGPT添付やGitHub Actions artifactのみは`verified_restore`を許可しない。**
3. **アップロード元ではなく保管先から再ダウンロード**してSHA-256とZIP memberを照合。代表checkpointに対しrun metadataと6設定Cvが再ロード可能であることも試験（非信頼ZIPは安全な領域で展開、検証時のコードの実行には別許可）。
4. `archive_status=verified_restore`と復旧テスト日時/ソフト/結果をGit台帳に記録して初めて元ローカルrawを整理対象に移す。**元ファイル自動削除は行わない**。研究証拠の削除・不可逆な移動は個別の所有者承認が必要。
5. 保管先の障害・期限・アクセス不能・hash不一致が起きたら`archive_status=unavailable|corrupted`の新しい監査記録を追加し、候補の根拠が欠けることを通知する。元の正常な過去記録は消さない。

**保管期間の初期案（採用時に所有者決定）：** A/B/Cと昇格済みD・元公式rawは期限を定めず保全。E診断は関連不具合や再開エビデンスならD同等に保存し、それ以外は**少なくとも90日を目安**に保全してから削除審査。Fキャッシュは再生成可能かと原証拠に含まれないことを確認して整理。日数だけをトリガーとする削除・Git履歴改変は禁止。容量超過時は保持期間短縮でなく原本/副本の階層移動を検討。

## 8. CIで導入する機械的ゲート

1. **new-manifest schema / preflight**：新規runだけ必須ID・条件SHA・帯域SHA・seed・コード/環境記録・mappingを検査。旧39 manifestには遡及適用しない。
2. **finalize check**：実行/数値/物理/アーカイブの各状態を分離、回路ベクトルと設定数、証拠role・SHA・サイズ/所在、失敗・未収束の件数整合を検査。
3. **candidate promotion**：正式/試験の混同、未保存ベクトル、source-only、wrong remap、tolerance-onlyをstrict候補へ昇格させない。既存候補監査と接続。
4. **archive integrity**：Git保管なら実bytesをSHA-256検査。外部保管なら必要な認証で**保管先の実bytes**を検査。CIがアクセスできなければ`archive_not_reverified`と表示しPASSと同義にしない。
5. **inventory and retention**：Git参照逆引き、旧manifestとoverlay整合、保管台帳の一意ID、重複内容を別役割で保持する理由、期限切れActions artifact参照の有無を検査。外部URLがあってもハッシュ一致なしでは保存証明としない。

**CI軽量化:** push(main)・PRで重複実行しない。metadata/sha/分類の軽量検査を毎PR、RF高密度/独立MNAやバックアップ復元を重要成果・手動実行・定期監査に分ける。定期チェックを新設する場合もGitHub Actionsによる実際の実行結果が出るまで「実装済み」としない。

## 9. 実験運用手順（提案）

`plan`（実行しない）→ `preflight`（実効RF条件・コード/環境/seed・mappingハッシュ確定）→ `run`（rawファイルへ原子記録、シャード別checkpoint、定期スナップショット）→ `finalize`（成功/未収束/中断の内訳）→ `archive+verify_restore`（外部原本のハッシュ照合）→ `curate`（代表完全checkpointのGit登録）→ `independent_validate`（別実行・別証拠）→ `review`（条件別台帳/Paretoへ昇格）。

長時間runは「毎Nタスクまたは一定時間」のcheckpoint間隔と再開pointを事前指定し、成果物配布の期限より前に**incremental backup**を確保する。中断やSIGTERMでも`partial`と最終checkpoint出典を残し、無条件の`completed`へ読み替えない。

## 10. 旧資料の移行と導入順

- **M0（本書のみ）:** 既存39実験のメタデータ不足・source-only・保管分離を記録。元manifest/生証拠は改変しない。RG-001は引き続き保留。
- **M1（新規runの最小ルール）:** schema v2の追加仕様・preflight template/CIを新規runだけに適用し、manifest→checkpoint/evidence参照の整合を確保。旧索引は互換保持。
- **M2（原本保管先確定）:** 専用の外部永続領域を選定し、少量のtrial ZIP・1つの模擬raw runでupload→download→全SHA→復旧を実地検証。適格性/運用費/容量/アクセス・機密性を評価。これができるまで保管先を**決定済み**と扱わない。
- **M3（大規模探索への適用）:** WSL2/GitHub Actions runner双方にpreflight/finalize/archive/curationを導入し、新しい1実験をend-to-endで監査する。
- **M4（旧データの非破壊整理）:** 当初46件、Git branch全履歴、source-only manifest6件を個別レビュー。十分な復元検証と所有者承認がない削除・history rewrite/force pushは禁止。

## 11. 合意・完了基準（提案）

- 少なくとも**新規1件の完全な実験**でrun前/後メタデータ、失敗・中断時のstatus、全設定回路ベクトル、Git候補、archive領収、外部原本の復元、独立MNA overlayまで一貫してPASS。
- 証拠が消失した際に機械的に`unavailable`を表示し、`strict`結果を誤昇格させない。
- 既存mainのRF制約・bands・39元manifest・raw evidenceに差分がない。
- 所有者がアーカイブ先、保管期限、外部アクセス/費用、実際の削除を別途承認。
- **最適化の記録方針の採用 ≠ リポジトリ保管最適化の完了 ≠ RF性能達成 ≠ Phase 3承認**。PR #53は所有者が明示するまでDraft/未マージを維持。
