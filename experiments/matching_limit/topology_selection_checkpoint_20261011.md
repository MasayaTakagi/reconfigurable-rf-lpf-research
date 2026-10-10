# P2–P4 topology candidate scheduling update (2026-10-11)

Replaced sorted-prefix and shunt-count-only candidate scheduling with cost-bin stratified, deterministic round-robin across component-family signatures. The eligibility filter rejects ground-only signal paths and internal degree-one dead ends; these are structural filters, **not** a guarantee of realizable, well-conditioned or competitive circuits.

Local unit tests: 5/5 pass (selection module, standalone standard-library tests). Full repository integration and numeric optimization have **not** been executed locally because this environment does not contain a checkout of the complete repository. No CI run was requested or triggered intentionally.

Current remaining blockers: coupling optimization not wired to MNA screening, incomplete coverage of up to four internal nodes, no dense worst-band validation, and no global optimality proof. P4 is **not complete** and the historical Pareto frontier remains unchanged.
