# P4 A: four-internal-node / eight-branch numerical checkpoint

Date: 2026-10-11. This is a **pilot**, not completion.

A = internal nodes <=4, branches <=8, area<=6, PCB-L<=3. The sampler is seeded and non-exhaustive. Only IC shunt C values vary between the six cases. Coupling K is common to all cases.

## Local reproducible smoke run

A locally reconstructed copy of the MNA and independent nodal solvers was used because the full GitHub repository could not be cloned in this environment (network DNS blocked). Command: `python p4_batch.py --attempts 50 --per-bin 1 --starts 1 --layouts 1 --iterations 3 --validation-points 3`. The sampler generated 245 eligible inductive graphs, and one graph from each of the 15 internal-node/area cells was optimized. All 15 were independently cross-checked.

| Internal nodes | P2 worst IL dB | P3 worst IL dB | P4 worst IL dB |
|---|---:|---:|---:|
| 0 | 0.9349 | 1.3681 | 0.9716 |
| 1 | 2.4605 | 2.4663 | 0.5179 |
| 2 | 3.9400 | 3.3928 | 2.9751 |
| 3 | 3.3184 | 3.4000 | 1.5517 |
| 4 | 1.1013 | 5.1679 | 0.5543 |

These values use only 3 passband validation points per segment, one start and one coupling layout, three optimizer iterations, and are **not comparable as a final optimum** to prior best matching-only IL values. None improves the historical cost<=6 matching-only IL 0.114837004 dB.

A separate 3-graph smoke run gave independent nodal gain discrepancies <=1.6e-15 and absolute power residual <=5.4e-18 W at its validation points. Local source files are not identical byte-for-byte to GitHub modules; integration tests on the repository have not run. A longer 15-graph run with 2 starts, 2 layouts, 15 iterations and 21 validation points exceeded the local execution budget and produced no complete result; no values from that run are claimed.

## Important limits
- Coupling layout candidate generation currently includes adjacent-chip k=0 and +/-0.4, but does not yet search PCB-PCB k up to 0.6 or chip-PCB k up to 0.03.
- The sample is not exhaustive and the family selector does not ensure physically realizable component geometry or winding polarity.
- Optimization is nonsmooth worst-case SLSQP and may stop in poor local minima.
- Dense H2/H3 evaluation is diagnostic only; this is matching-only P4, not an LPF solution.
- No 4-node/8-branch coverage certificate, no cost-by-cost Pareto frontier, and no mathematical optimality bound. Therefore **P4 A is not complete**, and expanding node/branch limits cannot yet be justified by A's performance results.
