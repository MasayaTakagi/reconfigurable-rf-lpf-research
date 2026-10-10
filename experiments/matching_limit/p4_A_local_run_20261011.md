# P4-A: local 15-cell MNA run and interrupted refinement (2026-10-11)

Scope: 0..4 internal nodes, max 8 branches, 6 common-setting fixed topologies and only two 0..4 pF shunt IC C per setting. **Matching-only objective**, no harmonic constraint enforced.

Local command: `OPENBLAS_NUM_THREADS=1 python experiments/matching_limit/p4_batch.py --attempts 35 --per-bin 1 --starts 1 --layouts 2 --iterations 5 --validation-points 5 --output p4_run_new.json`.

Sampler: 174 inductive eligible graphs; 15 selected and evaluated, one per (node count, area bin). All SLSQP convergence flags false. Validation 5 frequency samples per passband segment.

| Internal nodes | P2 dB | P3 dB | P4 dB |
|---|---:|---:|---:|
| 0 | 0.77248 | 0.92653 | 0.94329 |
| 1 | 3.94881 | 1.98552 | 1.21024 |
| 2 | 2.59007 | 1.20165 | 1.66644 |
| 3 | 3.76765 | 2.75444 | 1.39338 |
| 4 | 0.44145 | 0.46084 | 1.53003 |

**Interpretation:** exploratory finite-grid IL, nonconverged, no improvement over historical matching-only cost<=6 IL 0.114837004 dB. No new Pareto frontier or mathematical limit.

A refinement attempt with 70 attempts/cell, 1 graph/cell, 2 starts, 3 layouts, 12 SLSQP iterations and 11 validation samples per segment exceeded the 240-second local execution limit. It produced no complete report. To prevent loss of completed graph evaluations on subsequent timeouts, `p4_batch.py` now writes an atomic JSON checkpoint after every graph and marks a completed final report separately.

**Remaining A completion gates:** budgeted multi-start convergence, cost-resolved Pareto frontier, nominal PCB/chip coupling sweep (including continuous values and physical polarity), dense-band validation, structural search coverage audit, and stopping/coverage diagnostics. Do not expand to A+ until the A baseline is sufficiently stable. Phase 3 remains excluded.
