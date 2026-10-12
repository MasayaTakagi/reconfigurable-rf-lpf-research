# EXP-009 — 3-variable-C placement and fixed-GJM rewiring (Phase 2; 2026-10-12)

## Key numerical finding

**Best finite-search cost-6 checkpoint:** [EXP009-01](EXP009-01.json) achieves six-setting worst UL/DL IL **0.307775390 dB** with minimum UL H2 **30.049481 dB** and H3 **30.049998 dB**, using **four LQP02 Q25 inductors, three GJM01 Q80 fixed capacitors, and three IC tunable Q80 capacitors**. All variable capacitors remain 0–4 pF. The Q values are constant-frequency lumped assumptions. The `0.30 dB` IL target is **not yet achieved**.

**Important engineering limit:** the L1 inductance converges to the **27 nH search upper bound**. Availability/SRF and Q(f) of such a small inductor at 617–2745 MHz are **not validated**. The two largest adjacent chip couplings are close to 0.4 and have not been EM validated. The harmonic attenuation margin is only about 0.05 dB. Consequently EXP009-01 is a **numerical Phase 2 checkpoint**, not an approved manufacturable circuit.

| Candidate | L1 upper bound | Worst IL | H2 minimum | H3 minimum | Cost | Status |
|---|---:|---:|---:|---:|---:|---|
| Earlier [C6-02](../EXP-008/C6-02.json) | 27 nH search range | 0.339093 dB | 30.030001 dB | 30.029976 dB | 6 | Separate preserved baseline |
| **[EXP009-01](EXP009-01.json)** | **27 nH** | **0.307775 dB** | **30.049481 dB** | **30.049998 dB** | **6** | Best-found; SRF concern |
| [EXP009-L15](EXP009-L15.json) | 15 nH | 0.314621 dB | 30.044973 dB | 30.044995 dB | 6 | L-range sensitivity only, not physically verified |
| [EXP009-L12](EXP009-L12.json) | 12 nH | 0.323169 dB | 30.044939 dB | 30.044997 dB | 6 | L-range sensitivity only, not physically verified |

**Exactly one fixed-C edge is changed relative to EXP-008 C6-02**: Cf3 (Q80 GJM01, common to all six settings) moves from in parallel with L0 (input node 1 to node 2) to in parallel with L1 (output node 3 to node 4). The remaining inductor graph, grounding capacitors, variable-C graph, and physical coil order are unchanged, but **all component values, neighbor k, and all six 3-C vectors are reoptimized**. This is neither a simple 1-parameter perturbation nor evidence of an exact causal decomposition.

### Topology and constraints

- Source 50 Ω; load 60−j40 Ω, constant across frequency.
- L0: nodes 1–2; L1: 3–4; L2: 2–5; L3: 2–3.
- Fixed Cf1: 1–3; Cf2: 5–GND; Cf3: **3–4**.
- Variable Cv0: 4–GND; Cv1: 5–GND; Cv2: 2–3 (non-ground, parallel to L3).
- Chip physical row L1–L2–L3–L0. Only adjacent k are nonzero; each |k|≤0.4; full inductance matrix is positive definite.
- Chip area 4×1+3×2/3=**6.0**. The IC resources and actual board space have not been included in this footprint metric.
- Six distinct settings B71/B12/B28/B13+B14 shared/B26/B8; same fixed network, only three C values change by setting.
- Both UL harmonic bands (H2 and H3) use the complete frequency intervals from `data/bands.csv`; IL is worst across all UL/DL settings.

### Finite local searches actually executed

- **14** local variable-C placement/control trials (13 unique edge/2-vs-3-variable combinations, with one duplicate edge label) started from C6-02. Their best 201-grid locally feasible trial was the original L3 placement at IL 0.339410 dB; **these are not limits on alternative variable placements**.
- **25** one-at-a-time fixed-GJM rewires, one start each. The Cf3→parallel-L1 trial produced IL 0.310810 dB (H2≈30.0394 dB), with SLSQP hitting its 130-iteration limit.
- **12** additional multistarts of the *original C6-02 topology* provided no improved 30 dB locally feasible result. They are not an exhaustive multistart for the new Cf3-parallel-L1 topology.
- **4** continuation/bound-sensitivity optimizations from the Cf3-parallel-L1 result: a 31- and 91-point minimax continuation yielded IL 0.307775 dB; 15 nH and 12 nH L1 caps yielded the two additional sensitivity candidates above. All runs are local, nonconverged, and were not run with global-optimality certification.
- Total **55** local optimizer executions across the above categories. The full iteration-level trace of these chat-time prototype runs was not retained in GitHub. Saved finished numerical vectors, declared graph choices, and the independent validator are retained.

### Independent checks

All three new candidates were verified at **7,001 frequency points per individual listed subband interval** and with a separate **9×9 MNA** solving the four inductor branch currents independently, at **54 representative frequencies per candidate**. For EXP009-01, maximum MNA power budget residual was about **8×10⁻18 W**, and minimum dimensionless k-matrix eigenvalue about **0.43414**. Reproducible from committed records:

```bash
python -m pip install -r requirements.txt
python experiments/chatgpt_topology_search/runs/EXP-009/verify.py
python experiments/chatgpt_topology_search/runs/EXP-009/sweep.py --reference-only
python -m unittest discover -s tests -p 'test_exp009_checkpoints.py' -v
```

The independent circuit formulation checks **numerical implementation, passivity and power conservation within the same lumped-component/Q assumptions**, but not actual part self-resonance, measured Q(f), IC routing parasitics, EM coupling, manufacturing tolerance, or a mathematical guarantee over continuous frequency.

### Further reproducible large-scale exploration

[Sweep engine](sweep.py) defines **38 unique constrained graph/control families** (baseline, alternate Cv2 edges, 2-control subsets, and 25 single-GJM rewires). It accepts deterministic seeds, shard count/index, starting points, optimizer iterations, per-subband grids, and a checkpoint path. It rejects resumes with changed code/design-spec/band/optimization fingerprint; it records both failed starts and uncompleted jobs. This general runnable engine was prepared and **smoke-tested locally**, but a complete large GitHub Actions sweep **has not been launched**. Its future multistart results may differ from the numerical local prototypes above.

[Manual GitHub Actions workflow](../../../../.github/workflows/lpf-exp009.yml) prepares preflight verification, eight sharded optimization jobs with artifacts/resume, and an [aggregate report](aggregate.py) that does not misreport unfinished searches as complete. This workflow is an implementation plan; it has not yet executed. It may need to be merged into the default branch before the manual dispatch is available in the GitHub Actions UI.

### Policy status and next technical priorities

- The user's EXP-008/EXP-009 permission is applied **only as an explicit experimental override**: 3 tunable Cs including one non-ground, and H2/H3≥30 dB. The canonical standard remains **2 grounded variable Cs**, nominal target H2/H3≥35 dB, cost hard cap 6, Phase 3 paused.
- Do **not** replace LPF-007/008 or C6-02 historical benchmarks. The stronger legacy 35 dB constraint is different and must not be mixed into a like-for-like comparison.
- Priority: **SRF/Q(f) realism** of 12–27 nH in the relevant LQP02 package; quantify IL penalty under physically justified L1 restrictions and measured Q. Improve 0.307775 further using multiple coupling orders and multi-edge changes, and test yield margin beyond nominal +0.05 dB.
- Phase **2** continues. **Phase 3 is not authorized**; no code-value discretization, switch topology, or switched capacitor parasitic design is claimed.

