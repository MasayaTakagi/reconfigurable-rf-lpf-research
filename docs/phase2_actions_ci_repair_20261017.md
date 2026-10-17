# Phase 2 GitHub Actions CI repair — 2026-10-17

## Scope and evidence

- Purpose: restore workflow YAML validity and metadata-only regression checks following the repository's change to public visibility. Public visibility and runnable GitHub-hosted jobs were confirmed independently; this repair does **not** alter GitHub billing.
- Failure before repair: `Phase 2 regression` run [38993047810](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38993047810) reaches `scripts/audit_results.py` and fails with an invalid EXP-044 execution state and absent EXP-046 manifest. `exp042_passband_q.yml` had duplicate `if-no-files-found` keys, causing push-triggered validation failures without jobs.
- EXP-044: map verbose execution/validation strings to the approved manifest states. All prior free-form records are kept in `search_scope.pre_schema_repair_record_20261017`, and original file contents remain in Git history. No RF result is replaced.
- EXP-046: add a versioned trial RF-T005 provenance manifest referencing the existing 2026-10-17 report and archived programs. The 28x1001 reduced-nodal result and independent 84-point MNA comparison are *previously reported evidence*, not reproduced by this CI repair. In-chat source SHA/seed/replay limitations are explicit; no false claim of Actions execution.
- Update `data/experiment_index.csv` to match these manifests. EXP-045 is reserved on main but has no `manifest.json` directory in the checked snapshot and is **not** indexed as executed.
- EXP reservation workflow: allow active RF-F003 and authorized RF-T005 in manual input choices; retain explicitly authorized historical RF-T004. Former RF-F002 selection was inconsistent with the existing `valid_constraint` program's allowed IDs.

## Verification gate

Required success criterion is a completed **new** `Phase 2 regression` GitHub Actions run on the repair head / merged main with `scripts/audit_results.py` passing and the complete test sequence succeeding. A push/PR event's mere creation does not constitute PASS. Large numerical optimizations are **not** run by this repair.

No change to `data/constraints/`, `data/bands.csv`, component models, circuit vectors or calculated RF figures. Project remains Phase 2; Phase 3 requires separate explicit owner approval.
