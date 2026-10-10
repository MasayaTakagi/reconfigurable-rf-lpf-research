# Four-internal-node coverage pilot (2026-10-11)

## Local results (reproducible)
Seeded sampler with seed 20261011, 2,000 attempts for each of 15 (internal-node count 0..4, area P2/P3/P4) cells, max 8 branches. Structural constraints: chip area<=6, PCB-L<=3, ground-independent source/load path, no degree-one internal node. Counts are **unique labeled sampled graphs**, not exhaustive and not canonical under internal-node permutations.

| Internal nodes | P2 | P3 | P4 |
|---|---:|---:|---:|
| 0 | 283 | 672 | 348 |
| 1 | 308 | 784 | 381 |
| 2 | 274 | 954 | 475 |
| 3 | 203 | 1068 | 551 |
| 4 | 114 | 1086 | 693 |
Total 8,194 sampled labeled graphs. Standalone local unit tests 2/2 pass.

## Independent exploratory MNA pilot
A separate local MNA calculation with 50-ohm source, 60-j40-ohm load, L/C Q factors 15/25/12/80, 6 independent 0..4pF pairs, and 24+ pass-band endpoint samples (including split B13+B14 segments) was applied to **one graph per cost bin**, with two randomized starts and 25 SLSQP iterations. Results:
- P2 area 0.667: 0.74044 dB, converged (single series GJM01 C; poor topology).
- P3 area 2.333: 3.85898 dB, not converged.
- P4 area 4.333: 0.49779 dB, converged, 4 internal nodes.

These are exploratory coarse endpoint-only results, without coupling, dense validation, harmonics, independent cross-check against repository solver, or robustness analysis. They are **not** new best designs, P4 completion, or physical performance limits.

## Scope and remaining blockers
The former bounded prefix enumeration cannot reach four internal nodes within a realistic small max_raw; this seeded sampler explicitly covers each node-count/area cell, but does not provide exhaustive coverage. A finite cost<=6 does not itself bound arbitrary zero-cost PCB-L arrangement without the PCB<=3 limit, but high multiplicity of fixed capacitors and 4 internal nodes still creates combinatorial explosion. Need an agreed finite topology/branch bound and acceptable coverage/stopping rule before declaring P4 exhaustive. Coupling layout integration, multiple initializations, dense-band worst IL, and independently checked passive network are outstanding.
