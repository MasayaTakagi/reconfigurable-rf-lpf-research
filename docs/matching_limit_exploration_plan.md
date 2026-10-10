# Phase 2 matching-only topology coverage plan (approved 2026-10-10)

## Scope
Optimize worst transducer IL across every UL/DL segment of B71, B12, B28, shared B13+B14, B26, B8. Ignore H2/H3 attenuation constraints **only for this matching-only experiment**. Fixed topology, fixed L/C, fixed mutuals, source 50Ω, load 60−j40Ω, per-setting 0–4pF IC shunt capacitors (at most two). Phase 3 remains stopped.

## Baseline and scientific claims
Reference one-row adjacent-chip-coupled matching-only frontier: area 0: 0.160621870dB (PCB3), area 2: 0.131991212dB, area 3: 0.122209045dB, area 4: 0.118042384dB, area 5: 0.115868661dB, area 6: 0.114837004dB. This is a **best-found** restricted family, not a mathematical lower bound.

## Execution gates
- **P0**: validate source bands, MNA vs independently formulated nodal method, power balance, historical reoptimization, zero IC-C. Completed via CI on main.
- **P1**: canonical two-terminal graph enumeration under an explicit node/branch bound. Deduplicate graph isomorphisms with fixed terminals; retain physical chip placement and coupling as separate discrete variables. Track raw/generated/deduplicated/pruned counts. No claim of all passive circuits.
- **P2**: screen area 0–2, including PCB-only, chip-only, mixed chip/PCB, shunt and series L/C, and parallel branches. Validate shared components across all six settings.
- **P3**: expand to area >2–4, include bridge and coupled branches; use multiple initial points, coarse screening, dense rescoring and independent solver cross-check.
- **P4**: expand to area >4–6, up to three PCB-L, adjacent chip strong pairs only, PCB pair |k|<=0.6, chip–PCB |k|<=0.03. Positive-definite full L matrix mandatory; record area–IL Pareto frontier and model sensitivity.
- **P5**: high-precision extremum verification of shortlisted solutions, independent equations, passivity and catalog feasibility.
- **P6**: numerical lower bounds/relaxations with precise scope, sensitivity and physics interpretation.

## Limits on topology completeness
Complete enumeration requires a **finite** and explicitly declared graph class, branch count, and number of internal nodes. Graph completeness does not imply continuous global optimality. Enumerate connectivity and L/C branch labels; chip/PCB physical layout, polarity and couplings are additional dimensions. Zero-ohm wires, floating nodes, isolated components, disconnected source/load and exact parallel/series duplicates should be canonicalized or pruned. Treat transformers as coupled windings, not cost-free ideal components. All LQP01 inductance ranges and LQW04 Q are catalog-unverified; LQW04 is conditional-only.

## Search and validation protocol
1. Enumerate/prune under cost 0–6 (1/3 increments), PCB-L<=3, IC-C<=2, chip single physical row, strong chip k<=0.4 only adjacent, nonstrong nominal zero; PCB–PCB <=0.6; chip–PCB <=0.03.
2. Optimize minimax IL over all passband segments, first coarse grid, then adaptive extrema search with endpoints, then <=0.02MHz dense grid.
3. Use DE/multistart local solvers with reproducible random seeds. Preserve optimizer failures; do not replace them with claims of physical bounds.
4. Verify full coupled-inductance matrix SPD and nonnegative dissipation, energy balance, and independent nodal/MNA consistency.
5. Keep objective worst-case (not mean), record frequency, band, C setting, element currents and dissipation, all chip and PCB costs.
6. Store every run's topology fingerprint, random seed, bounds, optimizer version, code SHA, grid, convergence and evidence status.

## Candidate status
exploratory: initial coarse screening; provisional: dense grid and model checks; verified: independent formulation and continuous-segment extrema checked; none means hardware/circuit-SRF verified. Do not conflate matching-only and full-LPF results.

## Reporting
Keep P2, P3, P4 individual coverage and Pareto tables; label incomplete classes explicitly. Only claim "exhaustive" inside the declared finite search class, never globally. Do not advance to Phase 3.

## Approved staged internal-node expansion (owner decision: C, 2026-10-10)
Start from the existing one-internal-node pilot. Expand to **up to four internal nodes** (six total nodes) as the next coverage target; then consider up to six internal nodes (eight total) if unexplored topologies remain promising. These are enumeration/computational bounds, **not** RF specification relaxations.

At each stage: (1) enumerate and canonicalize, (2) report raw and unique counts and whether the run was truncated, (3) map candidates to realizable MNA circuits and assign physical chip order/couplings, (4) optimize multiple starts and validate on dense passbands, (5) measure Pareto improvements and remaining untested families. Only promote a node bound when the prior stage's coverage and candidate quality have been assessed.

Because 6-node/6-branch multigraph enumeration can be very large, a `--max-raw` budget is mandatory for initial pilots. A budgeted run must be marked `TRUNCATED_INCOMPLETE`, and its counts must not be described as exhaustive. Expand search using connected-graph generation and canonical augmentation before attempting full 6-node enumeration.
