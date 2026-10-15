# Phase 2：EXP実験番号の中央予約規則（2026-10-15・提案）

> **新規EXP実験の開始前ゲート。** 正本は`main:data/experiment_number_registry.csv`。予約されない番号での探索run、manifestコミット、候補登録は禁止。**PR #53がmainへマージされるまで本方式は本番運用されない**。新規実験`EXP-042`は本PRでは予約しない。現行RF-F002/RF-T004、Phase 2は変更しない。

## 1. 確認済みの過去番号・欠番

mainの`data/experiment_index.csv`と`experiments/chatgpt_topology_search/runs/`で**39実験**の存在を確認：`EXP-001`〜`EXP-017`および`EXP-020`〜`EXP-041`。`EXP-018`と`EXP-019`の元実験は現行mainに存在せず、番号には歴史的衝突の危険があるため**`legacy_gap_retired`（永久欠番）**として記録した。存在したと捏造しない。最初の新番号候補は`EXP-042`。過去の番号再採番・別実験への転用をしない。

`data/experiment_number_registry.csv` は`experiment_id,state,owner,request_id,purpose,constraint_id,reserved_at_utc,origin`を持つ。原登録39件は`legacy_recorded`、欠番2件は`legacy_gap_retired`。新番号は`reserved`、作業開始後`active`、完了`completed`、中止`cancelled`として将来状態更新可能だが、**一度割り当てた行/番号は削除・再利用しない**。中止の「元実験manifest完成」は要求しない（予約の履歴は必ず保持する）。

## 2. 実験の開始手順

1. 現行mainが同期したことと目的/制約を確認。**1つの目的・条件で複数workerやshardを動かす場合は1つのEXP番号を共有し、run_id/shard_idを分ける**。目的/条件が異なる並列実験はそれぞれ別の予約を取得する。
2. GitHub **Actions → Reserve next EXP number → Run workflow** をmainブランチ上で実行。目的とRF制約（現行RF-F002、認可済みRF-T004）を入力。GitHubログに`EXP-NNN`が表示され、`main`の台帳へ保存されたことを確認。任意の`request_key`を指定すれば同一申請の重複予約を抑止できる。空欄時はGitHub Actionsのrun IDを利用。
3. **正式予約成立条件＝非force main push成功＋最新mainの予約台帳再取得・同一request_key/番号の一致**。成功ログよりも台帳を優先し、記録がmainにない場合は**予約失敗・実験開始禁止**。
4. 作業者は`git fetch origin main`後、`python scripts/experiment_id_registry.py --experiment-id EXP-NNN --owner <github_actor>`を実行。これがPASSしてから新しいrunブランチ/`manifest.json`を作成する。
5. 必須の実験保存手順は[GitHub-onlyの保存方針](experiment_result_storage_policy_proposal_20261015.md)。run ID、トポロジー、コードSHA、RF制約SHA、環境/seed、完了・中断内訳、重要な完全回路ベクトル、6設定Cv、数値検証証拠をGitに残す。runは始まっただけで`completed`にしない。

**main書込みがGitHubのbranch protectionやrulesetsで禁止された場合**：予約workflowは失敗として停止する。保護を迂回しない。新番号を仮予約した**短い台帳変更PR**を作ってレビュー・mainマージを完了し、改めてmainで`experiment_id_registry.py`のPASSを確認してから作業開始する。**保護下ではPR提案中の番号はまだ確保済みではない**。競合するPRの古い行はmainの最新台帳から再採番・rebaseしてからmergeする。今回、保護設定はアプリ権限からAPI確認できなかったため、workflow push可能性は実運用まで**未検証**。

## 3. 並列競合に対する挙動

- GitHub Actionsの複数申請を単一pending枠の`concurrency`に頼らない（後からの申請でpending処理が入れ替わるリスク）。**Gitの通常fast-forward pushを排他の確定点**とし、同じ番号を選んだ2件のうち先にmainへ保存された1件だけ成功。負けた申請はmainを取り直し、後続番号で最大12回再試行する。
- 再試行中・サーバ応答不明の場合は最新mainで元request_keyを探し、**既存予約があれば同じ番号を返す**。同request_keyなのにowner/目的/制約が異なる場合はエラー。回数超過、権限拒否、実行環境不正は**fail closed（未予約）**。
- ブランチ上の台帳コピー、自己判断での`EXP-042`予測、GitHub Issue番号、PR番号、ChatGPT内の口頭合意はいずれも**予約ではない**。
- **実験番号は回収・払い出し直しを行わない**。中止・失敗・計画変更でも予約状態と理由を履歴に残し、次は最大番号+1を使う。予約台帳は監査・コードレビューの対象。

## 4. 実装とゲート

| 実装 | 役割 | 導入状態 |
|---|---|---|
| `data/experiment_number_registry.csv` | 001〜041の39既存番号と永久欠番2件 | PR #53に追加。mainには未反映 |
| `.github/workflows/reserve_experiment_number.yml` | 手動main予約、認証済みactor/条件、再取得・非force push再試行 | PR #53に追加。**未起動** |
| `scripts/reserve_experiment_number.py` | 最新main読込、ID衝突防止、push競合再試行 | 同上 |
| `scripts/experiment_id_registry.py` | 台帳形式・不変過去ID・同request key検証／main予約確認 | 同上 |
| `scripts/audit_experiment_number_registry.py` | 新しい実験manifestは既存main予約必須。古い39 manifestは免除 | 同上・CIに追加 |
| `tests/test_experiment_number_reservation.py` | 重複申請・変更申請・終了後非再利用・欠番改竄などの回帰 | 同上 |

**スキーマv2やGitHub-only保管予算との統合:** 新規`EXP-NNN`のpreflightで既存main予約とRF制約/帯域SHA、完全候補保存先を確認。PRが予約と新manifestを同時に追加しても、main上に予約がない場合はaudit FAIL。旧実験の回収やEXP-017正式2C checkpoint欠落の保留は独立課題。

**確認ゲート：** workflowがmainへ正式導入されたあとに、owner承認下で実際の2件同時申請を行い、別番号・証跡・非再利用・preflightを確認する。それまでは`GitHub Actionsの競合耐性は実装済みだが現場未検証`と記録する。mainマージは別途ユーザー明示承認が必要。
