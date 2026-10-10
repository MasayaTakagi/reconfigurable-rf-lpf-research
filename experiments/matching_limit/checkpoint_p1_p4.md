# P1–P4 initial coverage checkpoint (2026-10-10)

## Finite graph enumeration (P1)
Run `python experiments/matching_limit/enumerate_graphs.py --nodes 3 --branches 6`.

Enumerates **two fixed terminals plus at most one internal node**, up to **six branches**, each typed LQP01/LQP02/PCB-L/GJM01, with chip area <=6 and PCB-L<=3. Branches are between distinct nodes, parallel branches allowed. IC variable-C placement, chip physical order, coupling assignments and full topological optimization are **not** enumerated. This is a small bounded graph subset, not exhaustive across the approved component and topology space.

Expected graph counts (this restricted class; internal-node isomorphism only):
- raw multisets: 18,772
- feasible labeled and connected: 17,112
- area 0–2: 2,109
- area >2–4: 11,244
- area >4–6: 3,759
- total retained: 17,112

Counts are structural, **not optimized or validated circuit candidates**. Series-chain topologies needing more than one internal node are excluded, so even this set is not a complete coverage of conventional ladders.

## P2–P4 optimization pilot
Run `python experiments/matching_limit/parallel_chip_screen.py`.
Tests 2, 4, and 6 LQP02 windings in parallel between source and load, adjacent chip k=+0.4, fixed 6-setting topology, per-setting input/output IC C 0–4pF. Two deterministic starts per topology; SLSQP coarse ~5MHz grid; rescore ~0.02MHz. Results are exploratory and must not replace the historical verified series-L baseline without independent MNA validation. A successful solver run is not a global optimum certificate.

## Gate status
P0: complete and CI verified on main. P1: bounded graph generation implemented and tested; wider topology and physical layout enumeration incomplete. P2/P3/P4: representative pilot scripts in CI, **not complete minimax optimization of enumerated graphs**. Next action is graph-to-MNA circuit instantiation and prioritized multi-start optimization with all coupling/layout variants. No new global IL lower bound claimed.

## Unresolved modeling decisions
A practical upper bound on internal nodes and on how many parallel branches can share the same terminals is required before any defensible completeness claim. Default physical design constraints are unchanged; increasing the topology enumeration computational bound does not relax RF specifications.
