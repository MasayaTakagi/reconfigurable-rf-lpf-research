# Historical research index (Phase 2)

This is an **index**, not a claim that legacy files satisfy the current RF policy. Numerical source of truth for *current* designs remains `data/design_constraints.json`. The historical snapshot below is **main at `35642be3e89f46b6ba135391cc857d76de433b92`**, immediately before PR #10; deleted files can be recovered with `git show` or GitHub's permalink.

## How to recover the original evidence

```bash
git fetch origin
git show 35642be3e89f46b6ba135391cc857d76de433b92:data/design_checkpoints.csv
git show 35642be3e89f46b6ba135391cc857d76de433b92:docs/g1_p4_sharding_validation_20261011.md
git show 35642be3e89f46b6ba135391cc857d76de433b92:experiments/matching_limit/p4_A_checkpoint_20261011.md
```

The immutable revision is also readable as `https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/blob/35642be3e89f46b6ba135391cc857d76de433b92/<path>`.

## Reference results (not interchangeable)

| Class / source at snapshot | Recorded result | Evidence status and limits |
|---|---|---|
| Current-policy LPF-007 / `candidates/LPF-007.json` (retained) | worst six-setting UL/DL IL **0.513168414 dB**, min UL H2/H3 **35.069970 / 35.069996 dB** | Finite-grid verified; optimizer did not converge; not EM-verified; fails IL ≤0.30 dB target. |
| Current-policy LPF-008 / `candidates/LPF-008.json` (retained) | IL **0.518587126 dB**, H2/H3 **35.099999 / 35.099995 dB** | Same caveats; alternative coupling layout. |
| Current-policy LPF-005/006 / `candidates/LPF-005.json`, `candidates/LPF-006.json` | IL **1.251127 / 1.163823 dB** | Local finite-grid candidates; do not meet IL target; now historical. Their independent evaluation evidence was in `experiments/no_pcb_policy_update_20261011/`. |
| Legacy CP07 / `data/design_checkpoints.csv` | IL **0.328924 dB**, H2/H3 about **35.05 dB** | **Obsolete configuration**: four independently tuned capacitances, incompatible with current maximum two tunable shunt-C branches. Not a current baseline. |
| Legacy CP09/CP10 / `data/design_checkpoints.csv` | IL **0.324314 / 0.323391 dB** | Historical PCB-coupled studies; not revalidated under all current constraints. |
| Historical theoretical CP11 / `data/independent_validation/independently_verified.json` | IL **0.295208369 dB**, H2/H3 about **35.1 dB** | k=0.98 ideal PCB-PCB coupling **exceeds current |k|≤0.6**; theory-only, not an implementable/approved reference. |
| Restricted matching-only area study / `data/matching_only_pareto_20261010.csv` | Example: at area 4, best-found chip-only IL **0.121684842 dB** | **Matching-only** objective; H2/H3 not required. Finite search; not an LPF baseline or mathematical lower bound. |
| P4-A local 15-cell pilot / `experiments/matching_limit/p4_A_checkpoint_20261011.md` | 245 eligible sampled graphs; 15 selected and independently checked with coarse grid | Incomplete/non-exhaustive pilot. One start and 3 optimizer iterations; **not** a Pareto limit or evidence P4-A is complete. |

Additional historical registers and decisions:
- `data/evidence_register.csv` — older validation levels, source pointers, physical/global-proof flags.
- `data/design_checkpoints.csv` — CP00–CP14, applicable objective class and evidence path.
- `docs/decisions.md` — approved rules and historical decisions.
- `docs/p0_runner_validation_20261011.md` — P0 Actions endurance pilot and artifact evidence.
- `docs/g1_p4_sharding_validation_20261011.md` — G1 source fingerprints, SIGTERM/resume tests, and CI observations.
- `experiments/matching_limit/p4_A_expansion_gate.md` — reasons **not** to expand P4-A bounds before a stable baseline.
- `experiments/matching_cost_20261010/reproduction_20261010.md` and matching-only scripts — limited-scope numerical reproduction, no harmonic constraints.

## Current milestones and provenance

G1's **original** Actions one-/two-shard smoke and continuation were recorded as passing in [run 38128578799](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128578799) and [run 38128871403](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38128871403). This is evidence for that historical calculation configuration, **not** a fresh P4-A run against PR #10's modified fingerprint.

PR #10 intentionally changes source fingerprints and the policy-document pointer. Resume must reject incompatible saved checkpoints; start fresh with the new configuration hash and verify artifact upload/restore on the modified head. These historical values remain comparable **only after** reconciling the circuit model, objective, fixed/variable component rules, frequency grid, and physical constraints.

This index does **not** restore old optimizer source or claim repeatable optimization from the current tree. Reproduction of a historical experiment may require checking out the above historical commit and retrieving any referenced archives/artifacts that remain available.
