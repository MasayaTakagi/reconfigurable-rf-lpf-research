# EXP-045 alternative 3L T-type local screens retained from draft PR #64

## Provenance / reconciliation (2026-10-17)

This supplementary record preserves distinct, previously reported **Phase 2 / trial RF-T005**
numerical options from draft PR #64. EXP-045 was reserved on main before the recorded runs.
The separate PR #65, already merged, is now the canonical EXP-045 manifest and README;
the original draft #64 manifest and README are archived verbatim as
`archive_PR64_original_manifest_20261017.json` and
`archive_PR64_original_README_20261017.md`. Neither original file is to be used
as the canonical manifest or to override the versioned RF-T005 conditions.

The two unmodified 26-parameter candidate checkpoints were computed **in-chat** using
the original fixed input and output S2Ps (not a new GitHub Actions numerical run).
The supplied separate 7x7 coupled-inductor MNA was reported on 84 probes.
The submitted Python scripts `recheck_exp045.py` and
`reproduce_exp045_search.py` are **reconstructed, saved-only, and not
executed**; their code and the SHA-256 of the original S2Ps were not independently
replayed in the original V8 run. These scripts do not constitute CI verification.

| Archived candidate | Worst IL (dB) | Minimum H2 (dB) | Minimum H3 (dB) | Grid |
|---|---:|---:|---:|---|
| `checkpoints/t3l_lowil.json` | 0.895985052552 | 30.001229126 | 30.006004113 | 28×301 |
| `checkpoints/t3l_harmonic_margin.json` | 0.896596659077 | 30.016703612 | 30.017049096 | 28×301 |

These are distinct from the canonical PR #65 additional PCB-C case (worst
IL 0.895180009065 dB on 28×1001, numerical result previously reported as
in-chat and independently probed on 84 points). Their tiny margins and lack
of standalone Python replay mean that neither old screen is promoted as the
experiment winner, a formal RF-F003 design, or a physical/safety claim.

## Review and verification gates

- Canonical `manifest.json` and `README.md` are copied **exactly** from
  the merged PR #65 main state. Do not re-index EXP-045 or replace its selected
  checkpoint with one of these alternatives.
- Do not claim the two archived scripts ran when the GitHub Actions
  metadata-only regression passes.
- Continuous extrema, SRF, real Q(f), EM, two-pair coupling layout and
  production tolerances remain unchecked.
- RF-T005 is a trial; **Phase 2 only**, Phase 3 not approved.
