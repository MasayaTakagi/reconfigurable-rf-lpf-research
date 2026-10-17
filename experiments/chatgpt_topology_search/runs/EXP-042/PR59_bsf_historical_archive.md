# PR #59: archived EXP-021 4L BSF exploration under trial RF-T005

## Review disposition (2026-10-17)

This supplement preserves distinct research artifacts from the earlier EXP-042
bridge/BSF candidate exploration, **without replacing** the current main
EXP-042 canonical `manifest.json`, `README.md`, experiment index,
inventory, or validated latest Q25 low-IL checkpoints. Their exact previous
branch content is preserved in `archive_PR59_original_README_20261015.md`
and `archive_PR59_original_manifest_20261015.json`, as well as Git history.

The new archived program `verify_rf_t005.py`, its saved checkpoint JSON and
`.github/workflows/exp042-rf-t005-verify.yml` originated in draft PR #59.
The old numerical local search includes **4×LQW04 with assumed Q33** and
separate **4×LQP02HV with assumed Q25**; these different component families
and chip areas must not be treated as equal-cost, equal-Q alternatives.
LQW04 Q33 is **not** an authorized replacement for the LQP02HV/Q25 basis
in the later RF-T005 fair low-IL ranking. Original PR #59's 35dB-focused
results were exploratory local screening, not evidence of meeting the
0.8dB RF-T005 interim loss goal or the RF-F003 formal 0.3dB goal.

Saved source-only or historical evidence:
- `baseline_hv35_clipped.json`
- `phase2_coarse_checkpoint.json`, `phase2_refinement_checkpoint.json`
- `phase2_q33_checkpoints.json`
- `verify_2001_results.json`, `verify_q33_2001_results.json`
- `verify_rf_t005.py` and its dedicated workflow

**Run provenance must follow its own CI record:** do not infer execution of
this Python verifier merely because its file or workflow exists. Any new
CI run results should be linked separately. Do not substitute old
per-band results for the main RF-T005 28-interval/S2P benchmark.

No edits to RF policy, component model, or result vector are made in this
review. Phase 2 only; Phase 3 is not authorized.
