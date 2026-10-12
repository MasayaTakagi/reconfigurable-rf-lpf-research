# Phase 2 topology search lessons: EXP-011 compact-LPF discovery

**2026-10-12** — This is an implementation-oriented index of empirically supported exploration rules, not a global limit or an approved change to project RF constraints.

## Central discovery

The best-found numerical 3-variable-C, 30 dB full LPF changed from **EXP010-05** (area 6, IL 0.299890577 dB, 4 LQP02 + 3 GJM + 1 PCB-C) to **EXP011-01** (area 4⅔, IL 0.293821739 dB, 4 LQP02 + 1 GJM + 0 PCB-C).

The successful chain was **rewire a fixed GJM to a tunable-C edge → collapse the two equal-Q parallel fixed/tunable C pairs → remove the remaining small PCB-C and reoptimize *all* fixed/tunable L/C/k**. The collapse is exact only within the constant-Q lumped model and 0–4 pF / six-setting variable ranges. The rewiring and PCB-C removal are **not** exact-equivalence operations: their improvements require numerical reoptimization and independent comparison.

Full technical and historical account: [EXP011 DISCOVERY_HISTORY](../experiments/chatgpt_topology_search/runs/EXP-011/DISCOVERY_HISTORY.md). Machine-readable transformation operators: [DISCOVERY_LINEAGE.json](../experiments/chatgpt_topology_search/runs/EXP-011/DISCOVERY_LINEAGE.json).

## Rules to adopt in the search engine

| Priority | Rule | Validation before accepting |
|---|---|---|
| P0 | Look for *same-node-pair + same-Q* fixed C in parallel with a variable C. Merge C totals by setting. | Every setting sum within 0–4 pF; identical Q/frequency model; full independent MNA equality; cost decreases or stays. |
| P0 | Do not restrict searches to minimum component count at graph generation. Generate promising richer graphs, then apply safe algebraic reduction. | Deduplicate topology only after checking exact network equivalence, not from appearance alone. |
| P0 | Optimize all fixed L/C/k and all six tunables again after **any non-equivalent** graph edit (rewire/add/delete). | Full UL/DL six-setting worst IL and UL H2/H3 minima; SPD; chip cost; connection and placement rules. |
| P1 | Evaluate adding **and deleting** PCB-C, fixed GJM, L and C branches as separate operations. | PCB-C zero *chip-area* cost is not zero loss or zero layout cost; removing is not generally electrically equivalent. |
| P1 | Carry across known good element vectors when new topology is related; use multiple random starts. | Keep seeds, evaluations, success flags, failures, code SHA and per-shard checkpoint; never infer optimality from finite runs. |
| P1 | Preserve Pareto records by (chip cost, worst IL, H2/H3 margin) rather than selecting the single smallest nominal IL. | Numerical 0.0001 dB rejection margin on EXP011-01 is not a manufacturable tolerance margin. |
| P1 | Use loss budgets as a **search heuristic**, not a causal attribution. L0/L3 contribute ≈0.1797 dB of ≈0.2938 dB overall IL in EXP011-01. | Check redesigned network after any proposed current redistribution; reflected/dissipated watt decomposition does not predict ΔIL from removing an element. |
| P2 | Explore simultaneous multi-L rewiring, physical inductor row order, and L/C rewiring; single-edge rewires are not enough. | Physical strong coupling only neighbors |k|≤0.4, other nominal 0, full SPD. |

## Stop conditions and evidence levels

- **Screening:** 201 points per individual frequency interval is local finite evidence only.
- **Refinement:** joint multi-start minimax with adaptive worst-frequency enrichment, explicit tolerance to target.
- **Validation:** at least 7,001 points per individual UL/DL/H2/H3 interval, independent current-augmented MNA representative points, passivity, power budget, inductance matrix SPD, setting-by-setting tunable bounds, physical row.
- **Archive:** preserve canonical LPF-007, all predecessors, unverified promising and invalid candidates separately. Save intermediate graph transformations and full six-setting vectors where possible.
- **No false completion:** partial/failed/unexecuted jobs must remain visible. Do not equate GitHub commits or a passed CI with completing an optimization or real-world EM validation.
- **Policy:** Q(LQP02)=25, Q(GJM/IC)=80, Q(PCB-C)=40 constant. Three-variable-C including non-ground and minimum 30 dB are **Phase 2 experimental overrides only**; canonical two-grounded-C/nominal 35 dB remains unchanged. Phase 3 is paused.

## Reuse in script-driven P4-A

Implement graph normalization **after graph generation and before optimization**, using explicit safe equivalence proofs. Feed reduced candidates back into the candidate pool with area savings and mapped six-setting variable vectors. Use EXP011-01 and EXP011-02 as warm starts when their graphs are compatible, but independently validate every prospective improvement. Report searched graph count, feasible convergence count, measured IL/attenuation, and unsearched graph count per cost cell. Do not claim a mathematical lower bound from a finite survey.
