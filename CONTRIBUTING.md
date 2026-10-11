# Contributing to Phase 2

Read [current roadmap](docs/roadmap.md), [architecture](docs/architecture.md), [baseline protocol](docs/baselines.md), [specification](docs/specification.md) and the machine-readable [constraints](data/design_constraints.json) first.

- **Two discovery tracks are both first-class**: AI-proposed physics-driven topologies and systematic graph-generated topologies. Submit either with a reusable candidate representation and the same validation requirements.
- Put shared circuit models, validation, topology handling, and reusable optimization algorithms in `src/lpf/`. Keep `experiments/` for reproducible experiment orchestration/results and `scripts/` for command-line entry points. Follow the staged, backwards-compatible [refactor plan](docs/refactor_plan.md).
- Include full six-setting topology (fixed component values, physical chip row and mutuals, and both variable-C connection nodes plus per-case values); record whether it is `matching_only` or `full_lpf`, the approved `spec_id`, candidate origin, area, run seed, solver convergence, grid density and evidence.
- Do not present matching-only IL as satisfying the H2/H3 requirement. Recompute both the proposed circuit **and LPF-007** under the same physical constraints and evaluation grid before claiming improvement; require an independent circuit-equation check for promoted results.
- Preserve all earlier candidates, checkpoints and source references. Assign new IDs to materially different topologies, assumptions or optimization campaigns. Keep failed, interrupted and untested units visible.
- Run `python scripts/audit_results.py`, `python scripts/check_no_pcb_candidates_20261011.py`, `python scripts/verify_no_pcb_tunable_candidates.py`, and `python -m unittest discover -s tests -v` before merge; for changes to G1/P4-A recovery, run a bounded Actions artifact/resume smoke as well.
- Run expensive searches manually, with explicit resource limits and checkpoint retention. Never infer a mathematical global bound from finite sampling or a failed optimizer.
- Changing an approved RF constraint requires owner approval and a documented policy revision. Phase 3 (capacitor switch codes, parasitics, Ron/Coff) remains paused; no Phase 4+ plan is active.
