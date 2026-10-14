# Phase 2 / EXP-017 30dB近接報告点の原ソース追跡（2026-10-15）

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
