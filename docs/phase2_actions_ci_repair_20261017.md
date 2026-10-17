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


## 2026-10-17: stale PR workflow repair and regression guard

**Main Phase 2 CI green**: prior metadata repair validated by [run 38996198991](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38996198991), SUCCESS. Added standard-library-only workflow-input duplicate-key test at tests/test_github_actions_yaml_keys.py (commit dd4e98ed934e61ff2f730ef559515462bf029e29). Main [run 38996711799](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38996711799) also completed SUCCESS, including unittest. CI success is not RF circuit analysis or EM validation.

**Root cause:** open PR branches inherited .github/workflows/exp042_passband_q.yml with duplicate if-no-files-found: warn keys in one with: mapping. Such runs showed zero jobs, indicating workflow loading failure rather than numerical code failure. Main already had a corrected workflow, Git blob fcb85b8b52603202a9d71e79bc96c05db7217e68. Its exact contents were backported:

| Draft PR | Branch | Fix commit | Confirmed validation |
|---|---|---|---|
| #65 | exp-045-rft005-3l-t-loss | cea5a551b9efda254135ea67f1f75d1a83dd956b | Fixed workflow blob re-read on branch; full new PR CI not observed |
| #64 | exp045-rft005-t3l-loss-refine-20261017 | ba46c0fc3911709f1d66a7ad538bc55b26267599 | [EXP-042 Q run 38996649034](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38996649034) SUCCESS; separate audit fails because EXP-045 manifest invalid |
| #62 | research/phase2-t-inductor-modal-q-20261016 | 762940db822c7e88a0b1738c579a7aed6e7b83a1 | [EXP-042 Q run 38996651758](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38996651758) SUCCESS; [Phase 2 regression run 38996651748](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38996651748) SUCCESS |

### Separate unresolved metadata validation, not a YAML error

PR #64 [run 38996649074](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38996649074) launches a real audit job, fails in scripts/audit_results.py and logs:

> Invalid EXP-045 manifest: Missing manifest fields: ['bands_sha256', 'code', 'constraints', 'environment', 'evidence', 'execution', 'purpose', 'random_seed', 'search_scope', 'validation']

This PR still has a legacy flat EXP-045 manifest. Do not silence audit or fabricate execution SHA or independent verification to obtain a green run. Proper migration must retain the original as historical evidence, resolve approved RF-T005 policy precisely, and label in-chat versus unexecuted archive replayers accurately. Thus the PR #64 content validation remains unresolved, while its EXP-042 YAML workflow is repaired.

RF numerical outcomes, constraints, experiment reservations and Phase status were not changed. Phase 2 continues; Phase 3 remains unapproved.


## 2026-10-17 final PR review / merge reconciliation (03:44 UTC)

The "PR #64 unresolved" subsection above is a **historical snapshot** and is now superseded for the merged branch. GitHub state confirmed all five reviewed draft PRs have been merged:

| PR | Merge commit | Provenance / reconciliation |
|---|---|---|
| #65 | `cc22c7ec2ff97b836365e77a14ca9d32832ff0b1` | EXP-045 research in-chat evidence, canonical source/manifest; Phase 2 regression 38997436104 PASS |
| #62 | `a3bed9b304e55f3fb623c8255d30478b986f1950` | T/π electromagnetic-coupling theory; added `tests/test_phase2_standalone_function_coverage.py` because the six theory modules used pytest-style functions not discovered by `unittest`; corrected PR head regression 38998999844 PASS |
| #64 | `39d394b9f310928115c119b7a253030441707505` | Distinct EXP-045 3L checkpoints and reproducers merged while preserving #65 canonical `EXP-045/manifest.json` / README; archived original PR #64 versions as `archive_PR64_original_manifest_20261017.json` and `archive_PR64_original_README_20261017.md`. Metadata index remains one EXP-045 row. Earlier PR #64 failed CI 38996649074 must not be reclassified as passing. |
| #59 | `e9ca3cab477ad0e8fc197f2817247b092998b38c` | Additional EXP-042 4L numerical provenance and replay source, separate from formal RF-F003 achievements; merge-head main regression 38999715559 PASS |
| #58 | `6b4f3941067e3cb0823f602051e22bcccd72aebc` | EXP-042 Cf2∥Cv2 circuit correction / source updates; associated PR check workflow runs 38999677183, 38999677194, 38999677216 and 38999677351 all SUCCESS |

**Post-merge main gate:** [Phase 2 regression 38999850687](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38999850687), head `6b4f3941067e3cb0823f602051e22bcccd72aebc`, completed **SUCCESS** with 28 successful steps and no failed steps. Source tree shows one unique record each for EXP-042, EXP-045, EXP-046 in `data/experiment_index.csv`. All five PRs are closed as merged, and no open PRs remained when checked. The previous validation failure in the original #64 branch was resolved by source preservation plus canonical synchronization before merge; the earlier failed run remains an authentic historical failure.

Review caveat: Actions PASS establishes the committed regression/evidence scripts executed by those workflows; it does not verify unexecuted offline reproducers, physical SRF/Q(f), EM, fabrication tolerance, continuous-band extremes, or formal RF-F003 performance. No explicit Phase 3 authorization has been issued.
