# PR #58: C-H30p0002 drawing interpretation and source-only optimizer

## Phase-2 archival reconciliation — 2026-10-17

The original PR #58 notes concerning the older EXP-021 user-supplied drawing
and RF-T005 finite-grid screening are preserved verbatim at
`archive_PR58_original_README_20261015.md`. The EXP-042 canonical README,
manifest, recorded winners, index and constraints from main take precedence.

This PR adds the original archived Python **source-only**
`optimize.py` (29-dimensional SLSQP epigraph exploration) and the historical
drawing-connectivity diagnosis. Source discovery/test import and CI metadata
audit do **not** mean its end-to-end optimizer was executed or converged.

**Distinct historical graph fact:** the archived image C-H30p0002 has fixed
Cf2 and tunable Cv2 *parallel* across the same two nodes. The historical
RF-T004/Q50/old-coupling, no-external-S2P rounded-value reproduction
IL≈0.305480dB is **not** RF-T005 or RF-F003 compliance. Its first RF-T005
screen with mandatory frozen external S2P (28 finite disconnected bands)
remained H2/H3-infeasible at about IL 0.873491dB / H2 28.988dB / H3
28.363dB (coarse 5-point screening). The source optimizer's later full
search and independent dense MNA have **not** run here.

Do not promote this source-only legacy checkpoint over main EXP-042
Q25 results, or interpret the source as a completed new numerical run.
Phase 2 only, Phase 3 not authorized.
