# Grounded topology coverage audit — 2026-10-11

Local offline Python audit, 0 internal nodes, node 0=GND, 1=input, 2=output; graph labels LQP01/LQP02/PCB_L/GJM01, chip area <=6, PCB_L<=3, non-ground signal path required. Counts below are **labeled, pre-isomorphism, pre-coupling, pre-optimization**.

| Maximum branches | Raw multisets | P2 area<=2 | P3 2<area<=4 | P4 4<area<=6 |
|---|---:|---:|---:|---:|
| 4 | 1,819 | 618 | 697 | 0 |
| 5 | 6,187 | 1,260 | 3,256 | 255 |
| 6 | 18,563 | 1,740 | 9,698 | 3,249 |

Critical correction: the grounded MNA pilot previously used max 4 branches, making its P4 bin empty by construction. Increase to 6 branches. This does not imply P4 optimization completion. The production generator performs canonical deduplication, so its counts differ from the offline labeled audit.

The existing main branch had been merged at PR #8; this batch carries forward the later ground-only path rejection and physically admissible coupling matrix validation from the research branch.

**Unresolved**: cost-stratified selection remains heuristic; many circuits are ill-conditioned or disconnected from signal when grounded branches dominate; physical dot convention must be checked; no comprehensive 4-internal-node enumeration, full layout/coupling search, dense validation or global limit proof. No Pareto frontier update is justified.
