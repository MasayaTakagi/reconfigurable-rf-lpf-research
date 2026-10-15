# Phase 2：GitHubのみで管理する実験結果保存方針（2026-10-15、提案）

> **変更指示：ユーザーは外部アーカイブの不使用を明示。GitHubを唯一の長期保管場所とし、保存対象を厳選する。** 本文は先行する「外部アーカイブ併用案」を置換する方針案であり、**採用/本番導入は未完了**。元のrun・manifest・保存候補・PR #53 Draftは不変更。Phase 2継続、Phase 3未承認。正本は `docs/chatgpt_project_instructions.md` と現行 `RF-F002` / `data/bands.csv`。

## 1. GitHubの実容量と背景

2026-10-15確認のmain `ad1cda8c47054fbe97edc5b8bb97261804281285`：**731個のtracked blob、非圧縮ファイルサイズ合計8,449,154バイト**。`data/validation/` 264ファイル・4,395,071B、`experiments/chatgpt_topology_search/runs/` 249ファイル・2,621,302B、その他218ファイル・1,432,781B。Gitの全履歴・packサイズではないため、容量判定に`git count-objects -vH`と`git-sizer`を併用する。

公式GitHubの一般ガイダンスはリポジトリ**理想的には1GB未満**、単一Gitオブジェクト**1MB推奨上限（100MB制限）**。本プロジェクトでは余裕を持って、以下の**内部レビュー閾値**を提案する（GitHub公式のハード制限とは異なる）。

| 指標 | 新規保存の目安 | 超過時の扱い |
|---|---:|---|
| 新規runのキュレーション一式（元コード共通部を除く） | **512KiB以下** | 超過はデータ役割・圧縮・重複を見直し、必要証拠なら例外を記録 |
| 新規の単一Gitファイル | **128KiB以下が望ましい** | 128KiB超はレビュー、**1MiB超は原則新規追加しない**（所有者承認例外） |
| 現行mainの全trackedファイル非圧縮合計 | **25MiBで増加監査** | 研究不要データの無条件削除ではなく、追加傾向と選別基準を見直す |
| 大容量探索を開始する前 | **保存見込みサイズをrun planに記載** | 原本が肥大する探索は保存すべき最小の意味ある成果へ縮約 |

### Git-onlyでの「再現性」の範囲

- **候補再評価可能**：完全回路定義＋全6設定可変C＋RF制約/bands/code SHA＋評価器で、IL/H2/H3を再計算できる。全探索途中経過の保存は不要。
- **探索の再実行可能**：上記に加え、最適化コード・環境/seed・探索範囲/初期値・ワーカー/端子mappingを揃えて探索を再実行できる。浮動小数点・並列の非決定性により完全一致を保証しない。
- **厳密な全試行履歴保存**：全iterations/tasks/logsを保持する場合のみ主張。**Git-only省容量運用ではデフォルトの保証対象にしない。** run manifestに保存レベルを明記し、未保持データを「後で復元できる」と主張しない。

## 2. 必ずGitに残す情報（A：重要証拠）

| 種別 | 必須内容・理由 | 保存形態 |
|---|---|---|
| 制約/帯域 | 有効な `RF-F002` / `RF-T004` の区分、`effective_constraint_sha256`、`bands_sha256`、30/35dB条件 | 既存正本の**SHA付き参照**。runごとの巨大な制約全文コピーはしない |
| run manifest | 実験ID/run/stage、実行Git SHA、dirty時のコードsnapshot/patch SHA、uv.lock/数値環境、seed、開始/終了/exit/収束、探索目的と範囲 | **短いJSON**。終了前/途中/失敗/unknownを区別 |
| 実験サマリー | 実行/未実行/未収束/失敗の件数、グラフ/seed/iter/evaluation範囲、最良値と制約余裕、理由別失敗内訳、選別ルール | **集計JSON + 短いREADME**。全iteration履歴で代用しない |
| 完全候補checkpoint | **全L/C、各部品Q/系列/端子、固定/PCB部品、結合符号kと物理一列順、6設定の可変C値、出典と閾値** | 候補ごとJSON、保存候補のID一意化。best/閾値近傍/パレート/代表的失敗を残す |
| 検証証拠 | 6設定UL/DLとH2/H3各不連続区間、worst周波数・min attenuation・格子条件、MNA/SPD/電力収支、実行器/検証器SHA | 数値サマリーJSON、必要な代表波形のみ。独立検証は別ID・別ファイル |
| 根拠チェーン | `candidate_id` → `experiment_id/run_id/stage_id` → checkpoint/git blob/元run/検証overlayへのパス/SHA | 既存の研究候補台帳とmanifest evidenceで参照 |
| 再現に必要なコード | 共通実装は`src/lpf/`または`scripts/`のGit SHAを参照。実験固有コードで元Gitに無いものは短い実コード/差分を保存 | コード重複/巨大なsource_snapshotを省略できるのは**Gitから元コードが復元可能な場合のみ** |

**候補がよい数値を示した直後、READMEへ値を書く前に、完全checkpointをGitで追跡可能な形へ保存する。** EXP-017のIL=0.301248245dB（正式RF-F002 30dB）の欠落を繰り返さない。報告値だけで元ベクトルがない場合は`reported_only`のままで、候補台帳へ昇格させない。

## 3. 条件付きでGitに残す情報（B：必要な場合に保全）

- **探索失敗と中断の証拠**：crash時最終checkpoint、原因を示す代表ログ/stacktrace、失敗時の端子mappingや誤継承の実例、stop/resumeベンチに必須なstatus/lockの記録。EXP-034〜037のように原因同定へ不可欠な場合は保存する。
- **全探索の縮小要約**：全試行の個別ベクトルを残す代わり、目的・条件・グラフ/seed別の計画/試行/収束/失敗件数、分布統計、局所最小の順位、失敗種別と代表例を保存する。非決定探索で厳密再生不能な点は`limitations`に書く。
- **最良以外の候補**：面積–ILパレート点、30/35dB境界付近、異なるトポロジーの有望解・反例、独立検証に使った点は完全ベクトルで保存。選別上位Kや数値差閾値は**実行前のplanで宣言**する。Kを固定して重要点を落とさない。
- **ChatGPT添付ZIP**：手元またはGitHubのほかに完全元コード・初期探索履歴が無い場合は、ファイル自体が**小容量ならGitへ原本を直接保全**してよい。元ZIPはSHA/件数/内部pathを台帳化し、展開後の同一データを無批判に二重コミットしない。特に受領済みRF-T004原ZIPは**118,646B**なので推奨128KiB以内。現状は台帳のみGitにあり、**ZIPのGit保存は未実施**。

## 4. 原則Gitに追加しない情報（C：実行中だけの一時成果）

- 毎iterationのフルパラメータダンプ、全試行の巨大JSON、ランダムな中間波形/大量の周波数ごとの全行列。
- 成功時の全worker stdout/stderr、heartbeat、空の`.lock`、cache、再生成可能な`*.pyc`、ダウンロード済み依存パッケージ、同一sourceファイルのrunごとの完全コピー。
- checksum・origin・環境を持たない一時ZIP、同一元候補の多重表現で内容が再現できるもの。

**省略の前提**：run終了前にAと必要なBが**Gitへコミット済み・元SHAで読み戻し検証済み**であること。これに失敗した場合、ローカル`results/`のrawを保持したまま`preservation_incomplete`を記録する。成功前の自動削除は禁止。ローカルのscratchは長期アーカイブではなく作業領域である。

## 5. 具体的なファイル構造と保存例

既存 `experiments/chatgpt_topology_search/runs/EXP-NNN/`・`data/validation/`・`src/lpf/`を維持し、新規runに限って次の役割を定義する（既存39件は不変更）。

```text
experiments/chatgpt_topology_search/runs/EXP-NNN/
  manifest.json               # run状態、制約SHA、実行コード、seed、選別理由
  README.md                   # 目的、探索範囲、達成/未達、問題点
  run_summary.json            # 試行・失敗・収束件数と分布/選別集計
  checkpoints/
    <candidate_id>.json       # 完全L/C/結合/6設定Cv
data/validation/<run_id>/
  validation_summary.json     # 別数値検証の結果、検証器SHA、失敗理由
  representative_failure.json # 保存が必要な診断点のみ
data/research_candidate_register.csv
  ...                         # full_lpf/matching_only、正式/試験、strict/公差を分離
```

- 元の `manifest.json` は不変のsource evidence、再解析は`data/research_validation_overlays.csv`と別validationファイルで追記する。
- 実行状態 `planned/completed/partial/failed/interrupted/unknown`、最適化収束、出典再現、独立MNA、物理性、保存完了を**独立フィールド**にする。
- ファイルの証拠リンクには `path`、`sha256`、`role`、`bytes` を保存。元のtrial `RF-T004`とformal `RF-F002`の比較禁止、H2/H3 30/35dB、`strict_finite_grid`と`tolerance_only`の分離を維持する。
- 実験ID衝突時は元名称/出所branch・チャットを残し、別source_idで区別する。後から別のEXP-017の元ZIPを同じ実験番号へ置換しない。

## 6. Git-onlyでの完了判定とコミット前検査

**保存完了条件**：重要候補の完全ベクトル、必須Aの全ファイル、必要なBの代表原証拠がGitに存在し、元ファイルのSHAとGit再取得内容が一致、6設定を読み込み数値再評価できることを確認。コミットやCI成功だけでは独立MNA/物理検証を主張しない。

1. `plan`：探索前に分類（full_lpfかmatching_onlyか）、constraint SHA、seed、コード、上位K/反例保存規則と予測保存容量を宣言。
2. `preflight`：元コードがGit commitから復元できるか確認、dirtyなら差分または源コードも保持。開始前に最小run manifest保存。
3. `run`：ローカル`results/`へ原子書込み。重要な数値点の完全checkpointは失わないよう実行中に保存。
4. `finalize`：全試行の件数と最良値を集計。元トレースのうち重要候補/失敗証拠を抽出してサイズ監査。
5. `commit+verify`：Aおよび必要なBをGitへコミットし、SHA・ソース構成・制約/帯域一致・全6設定確認。**この時点までは元の一時ファイルを消さない**。
6. `independent_validate`：検証は元探索とは別の結果JSON・条件SHA・検証器SHAで保存。共通格子数値や物理確認を実施していない場合は明記。
7. `review`：formal/trial・閾値・strict/toleranceで分離した比較台帳に昇格。必要に応じてパレート生成。

将来のCIゲート（本書の追加だけでは未実装）：新規runだけのmanifest schema v2、全設定checkpoint completeness、同一候補・コード・shaの重複確認、容量予算の閾値表示、RUN status と集計整合。旧39 manifestは不変・互換保持。

## 7. GitHub上の旧ブランチと全履歴の保存

- GitHubを唯一の保管場所とする以上、**期限付きActions artifactのGit bundleを恒久バックアップの代わりにしない**。
- 既存mainと履歴が異なる旧6ブランチを削除する必要がある場合は、**先端SHAを指すGitHub上の保護対象tagまたはarchive ref**を新設し、`git fetch --tags`と`git fsck`で履歴が到達可能であることを確認してから削除の可否を個別審査する。タグ・refの生成自体が履歴保存であり、巨大なbundleをGitの中へコミットして二重保管しない。
- archive refの移動・削除は禁止として運用。GitHub外部障害に対する別サイト冗長性を保証しないという**GitHub単独保管のリスクは受容**する。
- **今回、旧branch・実験ファイル・Git履歴の削除は実施しない。** Tag/branch削除はユーザーの別承認が必要。

## 8. 導入順序と判定

- **G1：方針案と容量基準**（今回）：Git-only方針を文書・PRへ反映し、容量監査を追加。元実験未変更。
- **G2：新規1件の端から端までの試行**（未実施）：preflight → run → 完全候補 → Git commit → Gitから再取得・数値追試 → 別validation overlay。証拠未保存時のエラーも検査。
- **G3：重要な元添付の採否**（未実施）：RF-T004 ZIPは119KB弱。**1回だけ原ZIPをGitに保全**する案と、必要な元コード・局所探索要約・独立候補だけをGitへ整理する案を比較し、重要根拠を欠かさず最小化。raw ZIPを未保存のまま「保管完了」としない。
- **G4：旧46ファイル・重複とログ整理**（未実施）：元39 manifest／源run出典／付随PR参照を再検証し、新旧保管階層を遡及変更せず整理案を作成。削除は別承認。

**今回の文書化を、完全導入・研究結果の新規達成・正式RF制約の変更・Phase 3の開始・PR #53マージと混同しない。** EXP-017正式RF-F002の未回収0.301248245dBは引き続き保留。
