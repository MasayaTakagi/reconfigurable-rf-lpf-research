# P0 runner pilot implementation (2026-10-11)

Status: workflow and pilot script **implemented but NOT yet executed on GitHub Actions**. Do not mark P0 complete without a successful 30-minute run and artifact verification.

- Workflow: `.github/workflows/lpf-p0.yml`, manual `workflow_dispatch` only.
- Inputs: 2, 10 or 30 minutes; job timeout 40 minutes; standard `ubuntu-latest`.
- Pilot: `scripts/p0_runner_pilot.py` alternates the independent eight-candidate MNA regression and the LQP02 reduced-model SLSQP reproduction. It records per-check return code, elapsed time, log tail, Git SHA, Python version and runner platform.
- Checkpoints: atomic `results/p0_runner_pilot.json` updated after each check, uploaded with `if: always()`, 14-day retention.
- It is **not** a broad topology search and does not claim new best IL.
- Run GitHub > Actions > **LPF P0 runner endurance pilot** > Run workflow > minutes=2, inspect result and artifact. Then minutes=30 for the P0 endurance gate.
- A workflow_dispatch action is not exposed by the available GitHub connector; launching the run must be done through the GitHub Actions UI or another authorized execution environment.
- If `audit.yml` automatically triggers on this push, treat it separately from the P0 manual pilot.
- Success gate: 30-minute completed status, zero failed checks, uploaded JSON, reproducible baseline, recorded SHA and timing. Follow with P1 profiler; no Phase 3.
