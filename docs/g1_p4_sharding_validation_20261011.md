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

## Independent review follow-up

- Follow-up work used branch `codex/g1-p4-shards`, starting from local commit `1ff8ff48e00f849dc1dbb3b07db07e6f9b59aa2f`; its tree matched the then-current PR head `62f123859d388df833cf0679f5d3a8cb88136f74`. The pre-existing G1 implementation edits were present in the working tree and were continued on this branch.

- Reworked the compatibility hash to include the algorithm version, P4-A topology and RF constraints, complete sampled graph set, frequency grid, calculation-source fingerprints, exact Python/NumPy/SciPy versions, and normalized BLAS/LAPACK identity. Git SHA, Actions run/job IDs, runner platform/CPU, wall time, and timestamps are recorded in execution history and excluded from the compatibility hash. A different commit is accepted only when the compatibility hash still matches.
- Added one-graph (default) and one-batch-time-limit controls. Each shard job uploads its checkpoint at the end of the bounded batch and confirms a nonempty Artifact ID and digest. A later run checks the named Artifact through the Actions API before downloading it. A missing or expired shard Artifact is reported and that shard restarts; API/permission errors and corrupt or incompatible checkpoints fail explicitly.
- Candidate results are fsync-backed in the Runner checkpoint as each optimizer start finishes. GitHub's external Artifact is uploaded only after the graph batch ends; only that successful upload is durable across Runner loss. Since the preceding successful upload, forced loss can therefore require replaying up to `max_graphs_per_batch` graph work units (one by default, at most four); saved candidates from the current, not-yet-uploaded graph are not externally protected. `max_batch_seconds` is checked before starting another graph and does not preempt an active graph. Artifacts are retained for 14 days. A successful SIGTERM handler leaves the local checkpoint available to the workflow's always-run upload step when the Runner continues far enough to run it; actual Actions persistence still needs the post-merge smoke test.
- Expanded aggregation states to `completed`, `in_progress`, `incomplete`, `failed`, `corrupt`, and `incompatible`; missing shards are `not_run`. It checks global graph assignment, duplicate graphs/candidate keys, mixed conditions, malformed checkpoints, and the matrix result. Optimizer nonconvergence remains a per-candidate field and does not mean the job failed.
- Added candidate-level atomic checkpointing inside each graph. A candidate whose optimizer result was saved before interruption is reused when that graph resumes; an unfinished in-flight candidate is recorded and may be replayed. Completed graphs and candidates are tracked separately in execution logs, and the aggregator includes partial candidate counts without calling the search complete.
- Added a POSIX process integration test that runs the real SciPy SLSQP P4-A optimizer on a three-graph bounded sample, saves one complete graph plus a candidate in the next graph, sends SIGTERM, copies that checkpoint as a downloaded-artifact stand-in, resumes in another process, and compares graph IDs, seeds, initial/result vectors, best IL, objective evaluation counts, candidate counts, and duplicate work against an uninterrupted run. A second test restores successive one-graph batch checkpoints in separate processes until all graph units finish.
- Preserved the numerical commands removed from automatic PR CI in `.github/workflows/lpf-research-regression.yml`, which is manual-only. The automatic `audit.yml` still runs data audit and the unit suite and does not start numerical exploration.
- Follow-up local checks in the repository `.venv`: **PASS**, 79 unit tests, data audit, Python compile, workflow YAML parsing with duplicate-key rejection, and `git diff --check`. `actionlint` is not installed. (Test count includes the candidate-resume and duplicate-result regressions.)
- **Implementation status:** complete on `codex/g1-p4-shards`. **G1 final verification:** pending the first real `lpf-p4-a.yml` Actions run and a subsequent run that restores its uploaded Artifact. `workflow_dispatch` must be present on the default branch to launch it; no merge was performed.

## First post-merge smoke run

Use `lpf-p4-a.yml` with `shard_count=1`, `attempts=1`, `per_bin=1`, `starts=1`, `layouts=1`, `iterations=1`, `coarse_points=2`, `validation_points=1`, `max_graphs_per_batch=1`, and `max_batch_seconds=600`. Leave `resume_run_id` empty for the first run. For each continuation, use the same calculation inputs and set `resume_run_id` to the immediately preceding successful run ID. With the current sampler these settings select three graph units, so the expected smoke sequence is one initial run plus two resume runs, each uploading a shard Artifact; the final aggregate should report `completed`.

This smoke test is a matching-only software check. Its IL and harmonic validation values are not RF performance limits or a full-LPF sign-off. Phase 3 remains paused.
