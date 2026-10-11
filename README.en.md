# Reconfigurable RF LPF Research

**Active: Phase 2 (topology discovery and RF performance). Phase 3 is paused pending explicit owner authorization.**

## Immediate research target

Beat the current ChatGPT-origin **full-LPF** best-found reference under the *same approved physical constraints*: [LPF-007](candidates/LPF-007.json), worst six-setting UL/DL insertion loss **0.513168414 dB** with minimum H2/H3 rejection **35.069970/35.069996 dB**. These are finite-grid numerical values from a non-converged optimization, not global optimum, EM verification, or manufacturability evidence.

The first objective is **lower worst-case IL while retaining at least 35 dB H2/H3 rejection**. The longer-term nominal IL target is **≤0.30 dB**, with 30 dB mandatory harmonic rejection. Six cases: B71, B12, B28, combined B13+B14, B26, B8. Keep all existing cost, Q, variable-capacitor and physical coupling constraints.

Two complementary discovery tracks run concurrently: (1) **ChatGPT-led RF hypotheses** and specialized reduced solvers, and (2) **systematic finite-class graph search** with deterministic sharded optimization. Both feed a common candidate representation, MNA/evaluation framework, and independently validated evidence. [Architecture and division of responsibilities](docs/architecture.md) / [Current Phase 2 roadmap](docs/roadmap.md) / [Reference candidates](docs/baselines.md).

**Important gap:** the current systematic P4-A adapter places two variable shunt capacitors at IN/OUT. LPF-007 and LPF-008 instead place them at internal trap nodes. Reusable generalized variable-C placement and a common test that reproduces these candidates are prioritized before larger-scale search.

**G1 complete:** GitHub Actions sharding, artifacts, and cross-run resume have passed real one- and two-shard smoke tests. Generalized architecture and faster, better-converging optimization remain Phase 2 work. Phase 3 is not authorized.

[Japanese overview](README.md) · [Machine-readable constraints](data/design_constraints.json) · [Methods](docs/methodology.md) · [Refactoring plan](docs/refactor_plan.md) · [Candidate index](data/candidate_index.csv).

Legacy results and matching-only metrics must not be presented as current full-LPF performance. Historical experiment files are retained without claiming their original optimization environment is reproducible.
