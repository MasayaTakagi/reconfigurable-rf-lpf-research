# Reconfigurable low-loss LTE low-band LPF — external review overview

**Status (2026-10-10):** Phase 2, circuit topology exploration. **Phase 3 is paused until explicit project-owner approval.** Primary documentation is in Japanese; see [README.md](README.md).

## Objective

One passive network with six configurations: **B71, B12, B28, B13+B14 (one shared setting), B26, B8**. For each selected configuration, pass its uplink and downlink allocations with minimum *worst-case* insertion loss, and attenuate the entire 2nd and 3rd uplink harmonic ranges.

- Hard stopband requirement: at least **30 dB** (Phase 2 nominal exploration target: **35 dB**).
- Nominal minimax passband IL target: **≤0.30 dB** across the six settings.
- Source: 50 Ω. Load: frequency-independent 60−j40 Ω.
- Constant Q loss model: chip inductors 25, internal PCB inductors 12, capacitors 80. **Do not substitute Murata's published nominal Q numbers.**
- Chip area budget: LQP02=1, LQW04=3, internal PCB L=0; total ≤4. PCB traces still have physical layout, via, and coupling feasibility issues.
- Chip-chip coupling: at most two major pairs (|k|≤0.25), four minor pairs (|k|≤0.16). Chip-PCB coupling: |k|≤0.03. PCB-PCB coupling unrestricted **only within a positive-definite inductance matrix** in the theoretical exploration.
- Capacitors remain **ideal continuously adjustable values in Phase 2**. Discrete switched-capacitor realization is not yet approved.

## Published numerical search results (not global optima)

| Candidate | Worst nominal IL | Minimum H2/H3 | Qualification |
|---|---:|---:|---|
| Four chip L, 4 C, three series-path resonators + shunt trap | ~0.3289 dB | ~35.05 dB | Reference topology |
| Four chip L + three PCB L, weak chip–PCB coupling | ~0.3243 dB | ~35.05 dB | Additional shunt/bridges |
| PCB-PCB coupled alternative | ~0.3234 dB | ~35.05 dB | Geometry feasibility unknown |
| Three series-aiding PCB inductors, pairwise k=0.98 | **0.2952 dB** | **35.10 dB** | **Theoretical only; nearly perfect PCB–PCB coupling required** |

The last candidate was cross-checked using an explicit seven-winding nodal formulation, with energy conservation close to unity in the saved case. That is **not** a statement that the geometry can be manufactured or that the design is robust. See [results and evidence](docs/03_results_ja.md), [reproduction](docs/07_reproduction_ja.md), and [review questions](docs/06_review_request_ja.md).

**Not yet established:** exhaustive topology coverage; mathematical global lower bounds; interval-certified continuous-frequency compliance; tolerance/temperature; high-power (>23 dBm) nonlinear stress; component SRF, parasitics, PCB feasibility; switched-C discrete states.
