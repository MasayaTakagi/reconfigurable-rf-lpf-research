# G1 P4-A sharding implementation log — 2026-10-11

## Baseline

- Starting branch: `main` tracking `origin/main`; working tree clean.
- Starting commit: `89ce2df141beb569bb34cc366840b6204ad3cfd0`.
- Starting tree: `cc9bd372a0aca4d52934c8c71dce1fbcb3bccc98`.
- Runtime: Python 3.12.14 from `.venv` (system site packages enabled).
- Available declared packages: NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8.
- Numba is declared in `requirements.txt` but is not installed. No tracked source imports Numba; it is not a blocker for G1 or the current source tree.

## Baseline checks

- `python -m unittest discover -s tests -v`: **PASS**, 55 tests.
- `python scripts/audit_results.py`: **PASS** — band arithmetic, historical evidence metadata, and independent validation metadata.

Both commands were run with `.venv` activated before implementation changes.

## G1 scope

Implement deterministic P4-A shards, atomic resumable checkpoints, explicit result aggregation with missing-shard accounting, and a manually dispatched GitHub Actions workflow. Preserve the existing RF constraints and keep Phase 3 paused. Do not launch a numerical search as part of this implementation.

## Implementation and checks

- Added canonical graph IDs invariant to internal-node relabeling, stable SHA-256 shard assignment, and config-checked resume checkpoints.
- Added atomic checkpoint writes, SIGINT/SIGTERM handling, graph-level resume, and an aggregator that fails on missing, malformed, mixed-configuration, or failed shards.
- Added `.github/workflows/lpf-p4-a.yml` as a `workflow_dispatch`-only workflow with bounded input budgets, at most 8 matrix slots and 4 concurrent jobs, checkpoint artifacts, and an always-run aggregate report.
- Updated `.github/workflows/audit.yml` to run audit/tests only, so pushes and pull requests do not launch numerical searches.
- Removed Numba from `requirements.txt`: it is absent from the environment and no tracked source imports it.
- Post-implementation `python -m unittest discover -s tests -v`: **PASS**, 62 tests.
- Post-implementation `python scripts/audit_results.py`: **PASS**.
- `python -m py_compile` on the changed Python scripts/tests: **PASS**; `git diff --check`: **PASS**.
- `actionlint` is not installed in the environment, so workflow static validation was unavailable. The workflow was not dispatched.
- No numerical search was started. No files under `data/` were changed; existing RF design limits and specifications remain intact.
