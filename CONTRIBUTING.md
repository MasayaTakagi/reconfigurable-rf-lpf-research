# Contributing

- Read `docs/specification.md` and `data/design_constraints.json` before submitting designs.
- Record `spec_id`, `objective`, and numerical/physical verification level with every result.
- Do not compare matching-only IL to full-LPF IL without explicitly stating that harmonic rejection was excluded.
- Preserve previous candidate results; assign new IDs to materially changed topologies or assumptions.
- New experiments use `experiments/EXP-NNN/` with `config.json`, `results.json`, and `summary.md`.
- Run `python scripts/audit_results.py` and `python -m unittest discover -s tests -v` before merging.
- Phase 3 work requires explicit project-owner approval.
