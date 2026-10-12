# EXP-008 — Non-ground third tunable capacitor / 35→30 dB sensitivity (Phase 2, 2026-10-12)

## Result and interpretation

**Two additional relaxed-rule local numerical checkpoints satisfy the finite-grid full-LPF requirement with chip area cost 6.0.** The experimental rule change is **three independent IC variable capacitances (0–4 pF, Q=80), of which one may bridge two non-ground nodes**. This experiment does **not** amend the canonical default limit (2 grounded tunables) in `data/design_constraints.json` or authorize Phase 3.

| Checkpoint | Attenuation constraint (both UL H2/H3, all six settings) | Worst passband IL | H2 min | H3 min | Chip area | Verification |
|---|---:|---:|---:|---:|---:|---|
| Legacy policy-compatible [LPF-007](../../../../candidates/LPF-007.json) | ≥35 dB | 0.513168 dB | 35.070 dB | 35.070 dB | 6 | Saved separate baseline; not superseded |
| Historical experimental [A7-04](../EXP-006/A7-04.json) | ≥35 dB | 0.506951 dB | 35.002 dB | 35.002 dB | 6⅔ | Existing 2 grounded tunables |
| [C6-35](C6-35.json) | ≥35 dB | **0.444485 dB** | 35.000410 dB | 35.004999 dB | **6** | Dense + independent MNA |
| [C6-01](C6-01.json) | ≥30 dB | **0.340985 dB** | 30.020000 dB | 30.020000 dB | **6** | Dense + independent MNA |
| [C6-02](C6-02.json) | ≥30 dB | **0.339093 dB** | 30.030001 dB | 30.029976 dB | **6** | Dense + independent MNA |

**Comparison of best-found solutions in this same 4-L / 3-GJM / 3-variable-C circuit family:** C6-35 vs C6-02 gives 0.105392 dB IL improvement for the 35→30 dB attenuation relaxation **with fixed element values independently reoptimized in each case**. This is an observed finite-search result, neither a causal attribution to attenuation alone nor a global bound. The 0.30 dB target remains **unmet**, with 0.039093 dB remaining at best. The margin to the 30 dB requirement at C6-02 is only about 0.03 dB, not robust.

### Circuit topology

All six settings use the **same** L, fixed C, and mutual coupling. Only Cv0/Cv1/Cv2 change by setting.

- Input node 1 (50 Ω source), output node 3 (60−j40 Ω constant load), ground node 0.
- L0: nodes 1–2, L1: nodes 3–4, L2: nodes 2–5, L3: nodes 2–3; all LQP02, Q=25.
- Fixed Cf1: 1–3, Cf2: 5–0, Cf3: 1–2; all GJM01, Q=80.
- Tunable Cv0: 4–0, Cv1: 5–0, and **Cv2: 2–3 (non-ground, parallel to L3)**; Q=80, range 0–4 pF for each branch.
- Physical chip row L1–L2–L3–L0; signed neighboring k values in each JSON. All non-neighbor nominal k=0. K positive definite.
- Area: 4×LQP02 + 3×GJM01 = 4 + 3(2/3) = **6**. IC variable C IC/routing/PCB area excluded from chip area metric under the project's standard cost convention.

### How C6-01 was derived

A7-04 had two grounded IC tunables. A local pilot with its fixed L/C/k **unchanged** (6 per-setting C retunings, 19-point optimization grid, independently checked at 7001 points per subband) showed 35 dB IL≈0.506970 and 30 dB IL≈0.497039. Adding a third variable C parallel to its Cf0/Cf1/Cf3 *without fixed-network reoptimization* did not improve the limiting B8 IL (≈0.497039 at 30 dB). This does **not** imply those topologies are limited to that performance.

Joint SLSQP minimax reoptimization of fixed L, fixed C, permitted neighbor k, and per-setting Cv identified a 4-L/4-GJM/3-variable-C local solution at 30 dB. Per-setting retuning restored nominal attenuation and gave 0.340985 dB worst IL.

Cf0 of that circuit was 0.100 pF **in parallel** with Cv2, with both Q=80. Removing Cf0 and adding 0.100 pF to each band setting's Cv2 retains the *identical lumped RF admittance*: all resulting Cv2 settings remain 0–4 pF. The circuit thus uses **3 GJM instead of 4, cost decreases from 6⅔ to 6**, with worst IL unchanged (numerical difference <4e-14 dB). This reduced model is saved as C6-01 and independently MNA checked.

Further local SLSQP continuation (31 and 91 points per frequency interval during optimization) produced C6-02, with full 7001-point per-interval verification. C6-35 was obtained by independent 35 dB local optimization/6-setting retuning and the same exact identical-Q parallel-capacitance elimination.

### Reproduction and verification

```bash
python -m pip install -r requirements.txt
python experiments/chatgpt_topology_search/runs/EXP-008/verify_candidates.py
```

The verifier calculates all six-setting UL/DL pass intervals and UL H2/H3 stop intervals from `data/bands.csv`, with **7001 points per individual interval**; the maximum passband IL and minimum H2/H3 attenuation use all six settings. It independently forms a **9×9 current-augmented MNA** on 54 representative frequencies per candidate, checks the power budget (source available vs load + reflected + inductor + capacitor loss), and confirms positive-definite inductance matrix and capacitor range.

Observed independent MNA max power-balance residuals: C6-01 ≈8.7e−18 W, C6-02 ≈6.9e−18 W, C6-35 ≈1.13e−17 W. These are **numerical** checks of the same lumped component assumptions, not independent component physics/EM evidence or proof over continuous frequency.

The saved `C6-*.json` files contain the full physical row, circuit edges, fixed L/C/k, **six sets of all three variable capacitors**, model Q values, status, and independently checked metrics. The local iterative optimizer was run in a temporary numerical environment; **its complete search history, source, and random seed provenance have not yet been imported into this repository**. Saved solutions and the independent regression verifier *are* reproducible.

### Boundaries and recommended follow-up

- All optimizers were nonconvex and did not formally converge; **global optimum is not proven**. Failed searches and unconverged trials are not lower bounds.
- Strong neighboring k near 0.4, part-value realizability, actual Q(f), self-resonance, PCB/IC routing, switch/IC parasites, and tolerance sensitivity are not validated.
- New variable-C placement and a third branch are **experiment-specific approved relaxations**. The current **formal 2-grounded-variable-C baseline** remains LPF-007; do not overwrite its reference or silently modify the canonical policy.
- C6-02's very small rejection margin needs explicit robustness study. Explore other non-ground branches and 2-vs-3 independently tunable topology families at exactly the same 50 Ω / 60−j40 Ω, Q, area 6, 6-band metrics. Re-run optimization from more starts and use adaptive grid worst-frequency enrichment.
- Research stays **Phase 2**. Phase 3 implementation is **not authorized**.
