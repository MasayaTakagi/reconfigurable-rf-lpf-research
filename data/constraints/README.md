# Versioned RF constraints (Phase 2)

- **正式条件:** `formal/RF-Fxxx.json`。承認後は変更不可。現行は`RF-F001`、`registry.json`の`active_formal_id`で参照。
- **検討用仮条件:** `trial/RF-Txxx.json`。特定の正式版IDを`base_constraint_id`で固定し、変更点だけを`overrides`へ保存。仮条件は正式条件ではなく、正式採用にはユーザーの明示承認と**新たな正式ID**が必要。
- **既存互換:** `../design_constraints.json`は現行正式スナップショットと完全一致する互換ファイル。正本は`formal/`内の変更不可スナップショット。更新するときは必ず両者とregistryを同時更新し、監査テストで一致を確認。
- **旧条件:** `registry.json`の`historical`で元コミットを記録。旧候補の`spec_id`、性能、スクリプトを遡及変更しない。旧LPF-007/008等の再現・回帰と新条件への適合は別問題。
- **面積:** `RF-F001`では面積コストは**目的関数（ILとのパレート）**でありハード上限を設けない。P4-Aの最大コスト6などはジョブの有限探索範囲にすぎない。コスト0のPCB/IC資源は物理面積0を意味しない。
- **比較:** 同一の正式/仮条件、目的、減衰閾値、グリッド、検証水準で比較し、`best-found`と理論的最適値を混同しない。

仮条件の登録例（説明用であり登録済み・承認済み条件ではない）：

```json
{
  "constraint_id": "RF-T001",
  "status": "trial",
  "base_constraint_id": "RF-F001",
  "study_authorized": false,
  "description": "Example only: 3 independent tunable C branches",
  "overrides": {
    "components": {"IC_VARIABLE_C": {"max_branches_principle": 3}}
  }
}
```

実行する場合は`registry.json`の`trial`へ承認状態を登録する。実行時は基準正式版へ差分を適用した**実効制約全体**とSHA-256、目的`matching_only/full_lpf`、探索範囲、コードSHA、乱数seed、数値環境をmanifestに保存する。


## 登録の整合性検証（R1）

`validate_registry` は正式版の `state=approved`、ID/パス、実効JSONの
`effective_constraint_sha256` を照合する。正式版の内容を変えて登録済みハッシュを
維持した読み込みは拒否する。RF-F001には変更せず台帳へハッシュを追加した。
新しい正式条件は新IDで登録し、既存版のハッシュを差し替えない。

trial登録には台帳の `base_constraint_id` とファイルの同項目が一致すること、
台帳の `state=study_authorized` とファイルの `study_authorized=true` が一致することが必要。
未承認は `proposed`、不採用は `rejected`、取下げは `withdrawn` とし、ファイル側はfalse。
いずれも実行時opt-inだけでは読み込めない。制約ID/状態、旧policy_version、Phase 3の
状態をtrial差分で上書きすることはできない。正式昇格APIは存在しない。

実験マニフェストの仕様・履歴の不明値・新規実験開始手順は
[docs/experiment_manifests.md](../../docs/experiment_manifests.md)を参照。
