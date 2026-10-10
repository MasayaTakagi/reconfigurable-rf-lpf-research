# Reconfigurable low-loss LTE low-band LPF — external review overview

**Status (2026-10-10):** Phase 2, circuit topology exploration. **Phase 3 is paused until explicit project-owner approval.** Primary documentation is in Japanese; see [README.md](README.md).

## Objective

One passive network with six configurations: **B71, B12, B28, B13+B14 (one shared setting), B26, B8**. For each selected configuration, pass its uplink and downlink allocations with minimum *worst-case* insertion loss, and attenuate the entire 2nd and 3rd uplink harmonic ranges.

- Hard stopband requirement: at least **30 dB** (Phase 2 nominal exploration target: **35 dB**).
- Nominal minimax passband IL target: **≤0.30 dB** across the six settings.
- Source: 50 Ω. Load: frequency-independent 60−j40 Ω.
- Constant Q loss model: chip inductors 25, internal PCB inductors 12, capacitors 80. **Do not substitute Murata's published nominal Q numbers.**
- **New chip footprint cost (approved 2026-10-10):** LQP02=1 unit (Q25), LQP01=2/3 unit (Q15), LQW04=3 units (Q unspecified), fixed GJM01 capacitors=2/3 unit each (Q80 assumed; ≤100pF per part). Chip-footprint budget is swept up to **6 LQP02-equivalent units** for the current study (previously 4). PCB inductors (Q12) are **normally limited to 3**; IC variable capacitor branches (Q80 assumed) to **2 total**, **0–4pF of variable capacitance per branch**, shunt to ground only unless separately approved. Fixed GJM01 capacitors may be series or shunt, and parallel combinations with variable capacitors are permitted. Count PCB resources and IC branch count separately. Full rules: [design constraints (Japanese)](docs/11_component_cost_topology_rules_ja.md) and [machine-readable policy](data/design_constraints_20261010.json).
- Chip-chip coupling: at most two major pairs (|k|≤0.25), four minor pairs (|k|≤0.16). Chip-PCB coupling: |k|≤0.03. PCB-PCB coupling unrestricted **only within a positive-definite inductance matrix** in the theoretical exploration.
- For **new Phase 2 runs**, only the IC capacitor branches have continuously adjustable 0–4pF values; fixed GJM01 capacitors are shared across all six settings. No discrete switched-capacitor implementation work is authorized (Phase 3 remains paused).

## Latest matching-only study: area <=6, PCB pairwise |k|<=0.6 (2026-10-10)

With the 6-setting worst-passband IL objective, a new non-exhaustive sweep yielded **0.121685dB at 4 LQP02 units**, **0.114741dB at 5**, and **0.108543dB at 6**, using no PCB inductors and two shunt IC-variable-C branches. PCB-only 3-winding candidate with k=0.6 gave **0.160622dB at chip area 0**, excluding physical PCB layout cost. These are matching-only numerical candidate values, not certified minima or harmonic-filter results. See [new study](docs/13_matching_area6_pcb_k06_ja.md), [candidate envelope](data/matching_only_area6_k06.csv), [full-MNA verifier](experiments/matching_cost_20261010/verify_area6_k06.py). **PCB–PCB coupling is now normally limited to |k|<=0.6** in new research; the old 0.98 case below is archived theoretical research and outside this standard.

## Previous matching-only cost–IL study (2026-10-10)

A new Phase 2 candidate sweep covers 296 matching-only circuit configurations using the owner-approved chip-footprint model, fixed GJM01 constraints, and at most two IC shunt capacitor branches. Examples: one LQP02 + up to two IC shunt capacitors gives ~0.1669 dB worst-six-band IL; four coupled LQP02s give ~0.1217 dB. Zero-chip-footprint PCB-only solutions rely strongly on assumed PCB magnetic coupling and do **not** imply zero physical implementation cost. These are numerical candidate upper bounds within a restricted set of topologies, not global optimum claims or harmonic-filter results. See [study](docs/12_matching_cost_frontier_ja.md), [candidate envelope](data/matching_only_pareto_20261010.csv), and [shortlist verification code](experiments/matching_cost_20261010/verify_shortlist.py).

## Published numerical search results (not global optima)

**Historical results below have not been re-optimized or checked against the new fixed-GJM01 and two-branch variable-C constraints; they are not evidence of new-policy compliance.**

| Candidate | Worst nominal IL | Minimum H2/H3 | Qualification |
|---|---:|---:|---|
| Four chip L, 4 C, three series-path resonators + shunt trap | ~0.3289 dB | ~35.05 dB | Reference topology |
| Four chip L + three PCB L, weak chip–PCB coupling | ~0.3243 dB | ~35.05 dB | Additional shunt/bridges |
| PCB-PCB coupled alternative | ~0.3234 dB | ~35.05 dB | Geometry feasibility unknown |
| Three series-aiding PCB inductors, pairwise k=0.98 | **0.2952 dB** | **35.10 dB** | **Theoretical only; nearly perfect PCB–PCB coupling required** |

The last candidate was cross-checked using an explicit seven-winding nodal formulation, with energy conservation close to unity in the saved case. That is **not** a statement that the geometry can be manufactured or that the design is robust. See [results and evidence](docs/03_results_ja.md), [reproduction](docs/07_reproduction_ja.md), and [review questions](docs/06_review_request_ja.md).

**Not yet established:** exhaustive topology coverage; mathematical global lower bounds; interval-certified continuous-frequency compliance; tolerance/temperature; high-power (>23 dBm) nonlinear stress; component SRF, parasitics, PCB feasibility; switched-C discrete states.
