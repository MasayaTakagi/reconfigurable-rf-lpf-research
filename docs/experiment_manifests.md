# Phase 2 実験マニフェストと索引

実験の入口は [data/experiment_index.csv](../data/experiment_index.csv)。各
`experiments/chatgpt_topology_search/runs/EXP-NNN/manifest.json` を正本とし、索引は
[共通API](../src/lpf/experiment_manifest.py)から決定的に生成する。
[候補索引](../data/candidate_index.csv)は元のID・spec_id・性能列を維持し、
制約分類・正式/仮条件ID・実効ハッシュ・マニフェスト参照を追加した。

## 過去のEXP-001～015

今回の登録は、main `641a2792d65f754534f4828507024faab52fbc7b` にある証拠の棚卸し。
再最適化や新しい独立数値検証を意味しない。各READMEの目的、記録済み面積探索範囲、
結果・スクリプト・損失/検証記録への参照とファイルSHA-256を保存している。
面積上限6/7/4は当時の実験条件であり、RF-F001の正式RF上限ではない。
複数条件を比較するEXP-003の単一面積上限は `null` とした。

- 全15実験は `historical`。EXP-015も3可変Cや非GND枝等の比較を含み、
  RF-F001の採用前の記録なので、シリーズ適合だけを理由に `formal` としない。
- 元の実行時コードSHA、実効RF制約全体/ハッシュ、全実行のseed、数値環境、
  経過時間・総評価回数は確認できないため `null`。一部の結果に記録済みのseedや
  実行件数は元のJSONに保持しているが、実験全体の単一値へ読み替えない。
- `code.archive_sha` は棚卸しした証拠の保存版であり、`code.execution_sha` とは別。
  証拠ファイルのSHA-256を実効RF制約ハッシュへ流用しない。
- `execution.status=unknown` は実験全体の完了境界を再構成できないことを示す。
  実験未実行を意味しない。局所探索の完了/未完・未収束・例外は個別の元記録を参照する。
- `validation.*=reported_in_sources` は選択された保存解について元文書に検証記録が
  あることを示す。全試行の検証成功でも、今回実行した検証の結果でもない。
  EXP-004の独立検証水準は `unknown`。グリッドは元文書への参照で保存し、
  異なる探索/スクリーニング/密グリッドを単一の点数へまとめない。
- 物理実装検証は `not_run`。数値MNA一致はSRF、Q(f)、EM、製造可能性の証明ではない。
- LPF-007/008はEXP番号導入前の基準で、対応EXPのmanifestは空欄。
  LPF-009はEXP-001へ参照する。`historical_registry_key` は旧policy_versionの履歴索引であり、
  全ての当時のoverrideを含んだ実効条件の同一性を保証しない。

不明な過去条件を推測してRF-T番号を新規登録・承認することはしない。
歴史的結果・コードを更新せず、再実験は新しいEXPへ保存する。

## 新規実験の開始

例は作成手順のみであり、実験実行済みを意味しない。scope JSONはノード/枝上限、
面積探索範囲、素子種別/配置、グリッド、最適化反復数などを記録する。
正式RF制約とは別の計算パラメータである。

```bash
python scripts/experiment_manifests.py create EXP-016 \
  --purpose 'P4-A小規模確認' --objective matching_only \
  --constraint-id RF-F001 --seed 20261012 --scope results/scope.json
python scripts/experiment_manifests.py index
python scripts/experiment_manifests.py audit
```

`create` は制約・コード・帯域・seed・Python/NumPy/SciPy・環境を記録し、
`execution.status=planned`、検証は `not_run` で開始する。既存manifestの置換は拒否する。
コードの未コミット変更がある場合はdirtyフラグと再現性上の制限を保存する。
正確な再実行を主張する前に変更をコミットし、その版の新規実験として開始する。

試験条件を使う場合は `--constraint-id RF-Txxx --allow-trial` とする。
台帳とtrialファイルで同じ正式基準版・検討承認状態が一致する必要がある。
opt-inはユーザー承認の代用ではない。今回はRF-T条件を登録していない。

実行器は共通API `new_manifest` を開始前に呼び、結果保存時に次を記録する。
既存の専用最適化器/P4-Aへの自動組み込みは後続R2～R4で行う。

| 項目 | 保存する情報 |
|---|---|
| `constraints` | formal/trial分類、制約ID、固定基準ID、実効制約全体とSHA-256、旧policy_version（別フィールド） |
| `search_scope` | ジョブ固有の面積/ノード/枝上限、素子アルファベット、可変C位置、探索格子/予算 |
| `execution` | planned/running/partial/completed/failed/not_run/unknown、時間、評価回数 |
| `validation` | numerical/independent/implementationの個別状態、解析/独立検証グリッド |
| `evidence` | リポジトリ相対パスとファイルSHA-256。採用する結果の保存後に追記する |
| `limitations` | 未収束、未探索、未検証、dirtyコード、不明seedなど |

実行・検証に応じて作業中の新規manifestを更新し、索引を再生成する。
`completed` は宣言した計算範囲の消化を示し、大域パレート最適や物理検証を意味しない。
`matching_only` と `full_lpf` を混ぜず、H2/H3閾値・グリッド・検証水準も
同条件であることを後続のパレート集計で確認する。

## 監査と変更保護

通常の `python scripts/audit_results.py` がマニフェスト監査も実行する。
正式版の承認状態・識別子・固定ハッシュ、trialの型/既知キー・基準版・承認の一致、
実効制約と帯域のハッシュ、証拠ファイル、実験索引、候補の制約参照を照合する。
JSONのNaN/Infinityやリポジトリ外のパスを拒否する。

RF-F001のスナップショットと互換コピーは今回変更していない。
登録ハッシュとRF-F001の固定回帰テストで意図しない変更を検知する。
新しい正式条件は明示承認を受けた別IDで登録し、旧版を残す。
trialの検討承認を正式採用へ変換する処理は提供しない。

履歴ファイルの訂正が必要になった場合、監査を通すためだけに保存済み証拠ハッシュを
書き換えず、元版を維持した別実験または出典付きの訂正記録としてレビューする。
Phase 2継続、Phase 3停止。

P4-Aの計算ソース指紋は`src/lpf/*.py`と台帳を含むため、本変更で設定ハッシュが変わる。
互換性の境界を明示するためアルゴリズム版を `p4-a-bounded-sharded-v4-provenance` に更新した。
旧Artifactは同条件とみなして復元せず、新規チェックポイントを作成する。
既存の中断/再開回帰は新設定で行い、旧証拠・旧ワークフローを削除しない。
