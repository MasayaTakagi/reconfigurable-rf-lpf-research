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
