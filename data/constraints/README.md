# Versioned RF constraints (Phase 2)

- **正式条件:** `formal/RF-Fxxx.json`。承認後は変更不可。現行は`RF-F001`、`registry.json`の`active_formal_id`で参照。
- **検討用仮条件:** `trial/RF-Txxx.json`。特定の正式版IDを`base_constraint_id`で固定し、変更点だけを`overrides`へ保存。仮条件は正式条件ではなく、正式採用にはユーザーの明示承認と**新たな正式ID**が必要。
- **既存互換:** `../design_constraints.json`は現行正式スナップショットと完全一致する互換ファイル。正本は`formal/`内の変更不可スナップショット。更新するときは必ず両者とregistryを同時更新し、監査テストで一致を確認。
- **旧条件:** `registry.json`の`historical`で元コミットを記録。旧候補の`spec_id`、性能、スクリプトを遡及変更しない。旧LPF-007/008等の再現・回帰と新条件への適合は別問題。
- **面積:** `RF-F001`では面積コストは**目的関数（ILとのパレート）**でありハード上限を設けない。P4-Aの最大コスト6などはジョブの有限探索範囲にすぎない。コスト0のPCB/IC資源は物理面積0を意味しない。
- **比較:** 同一の正式/仮条件、目的、減衰閾値、グリッド、検証水準で比較し、`best-found`と理論的最適値を混同しない。

## 2026-10-12：3可変Cの比較研究条件（登録済み・Phase 2限定）

**現行正式版は引き続きRF-F001（2独立対GND可変C）**。2可変Cを最終小型化目標として維持しつつ、3可変Cを2系統で比較する。今回のユーザー承認は**仮条件としての研究実行許可**であり正式仕様への採用ではない。

| 条件ID | 状態 | 可変C構成 | 正式条件との差分 |
|---|---|---|---|
| RF-F001 | formal / active | 原則2独立枝、いずれも対GND | 基準 |
| [RF-T001](trial/RF-T001.json) | trial / study_authorized | **3独立枝、すべて対GND** | 最大枝数2→3 |
| [RF-T002](trial/RF-T002.json) | trial / study_authorized | **3独立枝：対GND2＋非GNDブリッジ1** | 最大枝数2→3、ブリッジ接続を追加 |

- 各枝0～4pF、Q80（暫定）。固定C、全6設定の不変素子・可変値のみの設定依存、部品・磁気結合・面積パレート方針はRF-F001から**変更しない**。
- H2/H3最低30dB、公称35dB目標、最悪IL 0.30dB目標を全系列で維持。同じ減衰閾値・周波数グリッド・検証水準の結果だけを比較する。
- 3可変Cの接続内訳はtrialの`study_variable_c_layout`を実効ポリシーにも含め、SHA-256で区別する。`validate_variable_c_connections`は枝数と端点・非GND枝のroleを検査する。**ブリッジが実際に直列経路を構成していないことはグラフ検証が必要**であり、現状の検証関数だけでは証明されない。主信号経路に直列挿入する可変Cは今回承認していない。
- 現行の`src/lpf/constraints.py::check_counts`および既存探索器は**デフォルトでRF-F001を参照する**。trialの登録だけで3個回路のP4-A/専用最適化器が自動対応したことにはならない。後続のR2/R3で実効ポリシーと接続検証を明示的に利用する。
- 新規実験は`load_constraint("RF-T001", allow_trial=True)`または`RF-T002`を指定。manifestはtrialのresolved policy、hash、固定基準`RF-F001`、可変C配置、減衰閾値、計算予算を明記。既存EXP-001～015の履歴を遡及的にtrial実験へ分類変更しない。
- 可変Cの数量自体は現在のチップ面積換算では0でも、追加のIC実装面積、スイッチの寄生/損失、制御資源、可変枝間相互作用を別途評価する。2枝 vs 3枝のコスト–ILパレート比較から最終仕様を判断する。
- 3個構成を正式条件に採用する場合、別途ユーザーの明示承認により**新正式ID（例RF-F002）**を発行する。RF-F001は変更しない。

仮条件の汎用登録例（以下は未登録の模式例）：

```json
{
  "constraint_id": "RF-T999",
  "status": "trial",
  "base_constraint_id": "RF-F001",
  "study_authorized": false,
  "study_variable_c_layout": {"branch_count": 3, "shunt_to_ground": 3, "non_ground_bridge": 0},
  "description": "Example only: proposed trial that has not been registered",
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
