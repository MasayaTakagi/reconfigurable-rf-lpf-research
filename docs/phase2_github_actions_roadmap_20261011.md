# Phase 2 compute and topology-search roadmap (2026-10-11)

Repository visibility verified public on 2026-10-11. This plan is a proposal; new workflows and benchmark results are not yet implemented.

## Objective and boundaries
Six cases: B71, B12, B28, B13+B14, B26, B8. Pass all UL/DL. Mandatory H2/H3 attenuation >=30dB; nominal exploration target >=35dB. Worst passband IL target <=0.30dB, chip area <=6. Fixed topology, L, fixed C and coupling; only two grounded IC variable C (0..4pF each) change by case. Preserve all approved Q and physical coupling constraints. This remains **research Phase 2**; do not start switch-C discretization or other Phase 3 tasks.

Distinguish matching-only IL frontier from LPF optimization with H2/H3 constraints. Never label finite random search as exhaustive/global.

## Execution architecture
1. ChatGPT: scientific objectives, constraints, review and decision log.
2. Codex/cloud code environment: profiling, solver refactoring, reproducible tests.
3. GitHub Actions: manually launched long-running matrix batches, bounded budgets, artifact outputs. Public repository standard GitHub-hosted runners are generally free; check current platform limits.
4. GitHub: source, seeds, configurations, validation reports and immutable result manifests.

Existing workflow: `.github/workflows/audit.yml`. Do not launch expensive jobs automatically on push.

## Gates
| Gate | Work | Evidence to advance |
|---|---|---|
| C0 | Runner pilot | 30-minute reproducible job, results/artifact, commit SHA, wall time, success status |
| C1 | General MNA profiling | agreement with reduced equivalent circuit and independent nodal solver; timing per candidate and per frequency; passivity |
| C2 | Optimizer bakeoff | nonsmooth SLSQP vs epigraph minimax vs warm-start/continuation; identical 10-30 benchmark graphs; convergence and IL |
| C3 | Structural enumeration | grounded canonical graphs, internal-node isomorphism, physical chip ordering and coupling admissibility; explicitly quantify uncovered classes |
| C4-A | approved A: <=4 internal nodes, <=8 branches | fixed-budget cost-resolved frontier, multi-start diagnostics, dense six-case UL/DL checks, independent validation |
| C4-B | A+ ablation | compare <=5 nodes/8 branches, <=4 nodes/10 branches, <=5 nodes/10 branches, optionally <=6 nodes/10 branches; one axis at a time, same RF constraints and numerical budget |
| C5 | full LPF | six-case UL/DL and entire UL second/third harmonic bands with >=30dB required and >=35dB target; dense revalidation |

C4-A cannot be signed off solely from nonconverged 5-iteration screens. Existing restricted series-L baseline is 0.114837004 dB at area6 matching-only; it needs 5 internal nodes to represent six individual series inductors, so it lies outside A's 4-node structural cap. Retain as external benchmark, not an A candidate.

## Workflow design
- `lpf-validation.yml`: short baseline regression, SPD, power balance and independent gain verification.
- `lpf-benchmark.yml`: manual 10-30 representative graphs; profile CPU, wall clock, convergence, max IL, worst-case frequency.
- `lpf-search.yml`: manual seeded matrix partitions, `fail-fast: false`, configurable node/branch/area budget, starts and max iterations, `timeout-minutes` bounded by runner limit.
- Partition candidates by canonical graph ID, not by process-dependent Python hash. Record SHA, config hash, graph ID, RNG seed, solver version, Q model, frequency grid, convergence status, evaluation count and elapsed time.
- Save atomic per-graph checkpoints and upload partial results with `if: always()`; provide a separate aggregation job that checks missing/failed shards and never silently treats missing results as complete.
- Keep artifacts reasonably sized and retention bounded; preserve promoted checkpoint summaries in Git.

## Optimization improvements
- Separate fast topology-aware reduced solver from independent general MNA validation; never collapse coupled coils where current-equality is not established.
- Precompute incidence matrices, batch frequencies, scale nH/pF optimization variables, benchmark BLAS thread counts.
- Compare direct nonsmooth max-IL SLSQP against epigraph `min t` subject to `IL(case,f)<=t`; adaptively add worst-frequency points.
- Use prior validated circuit values as warm starts and graph mutations, plus reproducible diverse random starts.
- Expand nominal physically allowed chip-adjacent and PCB-PCB signed coupling; check inductance SPD and physical orientation; weak chip-PCB nominally zero unless deliberately analyzed.

## Suggested initial allocation
Start with 1 runner, 10-30 minutes, then 2-4 shards, then up to 20 concurrent shards if quota permits. Do not commit to 20 parallel runners before measuring throughput and cost. For large batches, preserve per-graph partial outputs and use resumable shard IDs.

## Decision criteria
A+ is justified only if it improves the cost-resolved, independently validated worst-case six-setting passband IL with comparable compute budget and no RF constraint relaxation. Full LPF selection additionally requires complete H2/H3 checks. The output is a *best-found frontier* unless mathematical coverage/optimality is established.
