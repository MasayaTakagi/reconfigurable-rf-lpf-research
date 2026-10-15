# EXP-043 | RF-T005 — one-shunt-L multi-resonant RF LPF area/IL research

Phase **2**; RF-T005 is a **trial** (3 variable-C branches) atop immutable formal RF-F003. The owner-set **interim** worst-case IL target is **0.8dB**, not a change to the nominal formal RF-F003 0.3dB target. Mandatory H2/H3 >=30dB remains; nominal 35dB remains a separate objective. Fixed mandatory RF-F003 two S2P networks and the complex 60-j40ohm load are present in *all* calculations.

EXP-043 was independently reserved on main before exploration; pre-run manifest and experiment inventory were generated and audited. No Phase 3 implementation work is authorized.

## Research question

Can EXP-042's **two shunt inductors** be replaced by one shunt L while controlling multiple resonances and preserving as much RF-T005 performance as possible? The canonical EX042 comparison is the 4L/2GJM/2PCB solution at chip area 5⅓, worst IL **0.811306586dB**, min H2/H3 near 30.02dB, independently verified. This is compared only under the same RF-T005 condition.

## Most promising discovered topology: 3L, chip area **3**

Electrical nodes: IN=0, junction=1, OUT=2, shunt-resonant node=3, ground=-1.

- **Inductors:** L0(0,1)=3.343636859nH, L1(1,2)=7.753566019nH, Ls(1,3)=4.643489988nH. LQP02HV Q25×3. **Exactly one shunt inductor Ls**, series L0 and L1.
- **Physical row:** L0–Ls–L1. Adjacent k(L0,Ls)=+0.079369537; k(Ls,L1)=−0.084297401; non-neighbor k(L0,L1)=0. Full L matrix SPD.
- **Fixed C:** Cf0(0,1)=0.2pF, Cf1(1,2)=0.2pF, Cp(3,GND)=0.2pF. All three are PCB pattern C, modeled Q40, max three, 0.02..0.2pF each; **no GJM01**.
- **Tunable Cv:** Cv0(3,GND), Cv1(0,1), Cv2(1,2), each Q35, 0..3pF. All fixed L/C/k are common across settings.

| setting | Cv0 pF | Cv1 pF | Cv2 pF |
|---|---:|---:|---:|
| B71 | 1.653754961 | 3.000000000 | 1.049628937 |
| B12 | 1.488098056 | 2.671539700 | 1.117055348 |
| B28 | 1.314446666 | 2.866980453 | 0.924062047 |
| B13+B14 | 1.269347631 | 2.528383136 | 0.680653176 |
| B26 | 1.180177414 | 1.763196389 | 0.437563657 |
| B8 | 1.003901000 | 1.510565108 | 0.261533076 |

Exact 26-value vector is preserved at `checkpoints/zero_gjm_double.json`, sourced from original Actions artifact 11993948699. Under 28 CSV segments, **701 samples per segment**:
- **Worst IL=0.944268363dB** (B8 960MHz).
- Min H2 attenuation **30.020000000dB** (B71 1326MHz).
- Min H3 attenuation **30.019923243dB** (B8 around 2691.3MHz).
- Mandatory 30dB PASS on finite grid, interim 0.8dB **FAIL**.

Compared with EXP-042 area5⅓/IL0.811307, area falls **43.75%**, while worst IL increases **0.132962dB**. Area is component-footprint objective, not geometric PCB area or manufacturing feasibility.

**Independent check:** [GitHub Actions 38779436797](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38779436797) ran explicit **7×7 branch-current MNA**, separately from optimizer's reduced nodal-Y+ABCD, at **84 frequencies**. Max IL discrepancy **1.386e−13dB**, max power conservation residual **7.806e−18W**, all passive component powers nonnegative in checked samples.

### Can one shunt L create several resonant modes?

**Yes, because resonances are properties of the complete L/C network rather than a 1:1 count of shunt inductors.** In this 3L winner, Cf0+Cv1 across series L0, Cf1+Cv2 across series L1 and Cp+Cv0 in the shunt return permit at least two finite positive eigenmodes under the undamped/unloaded LC pencil. Numerical generalized eigenvalues using the *full signed 3×3 coupled-L matrix* and all C values:

| state | ideal undamped finite resonances |
|---|---|
| B71 | 1.53863, 1.61688 GHz |
| B8 | 2.10446, 2.66053 GHz |

**These values are not loaded S21 transmission zeros**, and should not be used as proof that rejection is 30dB across the stop regions; external-port transducer attenuation is evaluated separately.

Cross-coupling a tunable C between shunt node3 and node0/node2 can increase the capacitance matrix rank from 3 to 4 and support a **third** positive finite resonance for some settings, but the third mode often lies well above the intended H2/H3 regions, while settings with nearly-zero bridge C lose that mode (or yield numerically unstable, extremely high singular eigenvalues). In the directly tested zero-GJM input-bridge candidate (`checkpoints/zero_trap_in.json`), area=3, IL=**1.073373dB**, H2/H3>=30dB; nominal third-mode control was *not maintained in all six settings*. The best tested third-mode topology did not beat the two-mode 0.944dB winner.

## Actual Phase2 execution evidence — **21 topology variants**, 4 starts each

Sources: [3L central search](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38778406907), [4L exactly one-shunt control](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38778917206), [3L relocation](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38779344067), and [third-mode attempt](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38779860466). For complete finite-grid outcomes and correctly classified strict numeric failures see `run_summary.json`.

| subfamily representative | chip area | local best worst IL dB | H2/H3 minimum |
|---|---:|---:|---|
| 3L center, PCB×3 no GJM, both series L capacitively tuned | **3** | **0.944268** | 30.019923 |
| 3L center, GJM×2 + PCB×1 | 4⅓ | 0.946949 | 30.020000 |
| 3L center, one GJM + PCB×2 | 3⅔ | 1.416757 | 30.020000 |
| 3L input-bridge attempt at 3 finite modes | 3 | 1.073373 | 30.020000 |
| 3L two GJM with additional third-mode bridge | 4⅓ | 1.048333 | 30.020000 |
| 4L with exactly one shunt, GJM×1 + PCB×3 | 4⅔ | 3.533747 | 30.020000 |

Some other topologies gave substantially worse IL and **some fail 30dB**; consult `run_summary.json` before comparisons. All results are **finite-grid local best-found**, not global performance bounds, and a solver exit success alone does not mean RF specification pass. Q(f), part-specific L SRF, manufacturing/coupling, PCB fringing and tolerance remain unverified. The three PCB C values and one tunable C hit their formal upper bounds; margin to uncertainty is poor.

## Conclusion and next research

**Numerical area reduction is possible:** one shunt-L can support **two useful tunable eigenmodes** with no GJM and chip cost 3. However, with the present topology family, **worst IL <= 0.8dB has not been attained** (best found 0.944dB). A third positive eigenmode is theoretically accessible by capacitive feedback into the shunt node, but our finite exploratory placements did not improve IL, and effective modal placement across all settings remains unsolved.

Further Phase2 study should separate electrical model constraints from physical feasibility: optimization of *where* two or three transfer zeros appear over H2/H3 rather than unconstrained eigenmode count; active-selection of bridge C positions and nonzero-range requirements; Monte Carlo margins/3pF upper-bound sensitivity; and LQP01/PCB_L area reduction only under their existing Q/range/SRF policies. No assertion of exhaustive topology optimum or physical implementation readiness.


## RF-T005 adjacent mutual coupling: why the selected 3L solution does not saturate |k|=0.10

User question and controlled study: [GitHub Actions 38782551270](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38782551270), source `diagnose_k_vs_C.py`, archived numerical summary `k_vs_C_sensitivity_verified_summary.json`, full run artifact 11996901214. This is an *EXP-043 sensitivity* on `zero_gjm_double`, not a separate new experiment. 28 frequency intervals ×1,001 points each; four local SLSQP retunes; H2/H3 retune target 30.01dB.

- Saved k=(+0.07936954,-0.08429740): worst IL **0.94426836dB**, H2/H3 minimum 30.0199+dB.
- Both k pushed to (+0.10,-0.10) with all other components **fixed**: worst IL **0.95029046dB**, H2 **27.038dB**, H3 **27.665dB** (infeasible). Zero k reduces IL to 0.93705dB but destroys harmonics (15.918/18.869dB).
- **After numerical reoptimization**, k free, IC C≤3pF: worst IL **0.94408044dB**, H2/H3 >30.0099dB, best k=(+0.07940407,-0.08436595). This retune uses **3.0pF on B71 Cv1** and hence has an active C bound.
- Reoptimize with k pinned (+0.10,-0.10) and IC C≤3pF: worst IL **0.96990904dB**, H2/H3 ≥30.0099dB. Largest IC C is **2.86991pF**, so the 3pF ceiling is **not binding** for this full-k solution.
- Reoptimize same pinned k but *diagnostically* relax IC C≤4pF: worst IL remains **0.96990904dB**; utilized maximum C 2.94123pF. This hypothetical bound change has **no IL benefit**.
- Relax C≤4pF with k **free** (outside RF-T005): IL **0.93876531dB**, k=(+0.08003985,-0.05773506), B71 Cv1=4.0pF, B28 Cv1=3.74328pF. The allowable 3pF ceiling **does** limit some loss reduction, but increased C does **not** favor saturated |k|.

**Conclusion**: The variable-C ceiling partly constrains the optimum, but does not explain why |k|<0.1: at forced full mutual coupling the optimizer finds admissible ≤3pF values and worse IL. In the constant-Q model, increased coupling affects the imaginary mutual term, *not* Rii=ωLi/25. It may help some modes' effective Q while degrading passband power match or placing harmonic transmission zeros wrongly. PCB fixed-capacity limit of 0.2pF is also binding (all three fixed Cs), and was **not** relaxed by this study, so its separate effect remains open. The experiment establishes local finite-grid comparisons, **not** a global proof about every 3L graph or all k branches.


## 2026-10-15: EXP-043 PCB fixed-C ceiling and GJM Q80 replacement executed

Nine cases ran in [Actions 38783493014](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38783493014). The script is `diagnose_pcb_gjm.py`; full results and provenance in `pcb_Q40_vs_GJM_Q80_comparison.json`. All nine passed 28 separate bands ×1001-point finite-mesh H2/H3≥30dB and independent 7×7 branch-current MNA on 84 points per candidate with passive power-conservation checks. These are local candidate optima, NOT global bounds.

| Fixed C variant | Chip area | Worst IL dB | H2/H3 strict ≥30dB |
|---|---:|---:|---|
| Three PCB Q40 C ≤0.2pF | 3 | 0.944268 | PASS |
| Three PCB Q40 C ≤0.3pF **OFF-SPEC** | 3 | 0.940583 | PASS |
| Three PCB Q40 C ≤0.5pF **OFF-SPEC** | 3 | 0.935978 | PASS |
| Replace Cf0 PCB with GJM Q80 | 3⅔ | 0.919130 | PASS |
| Replace Cf1 PCB with GJM Q80 | 3⅔ | 0.929790 | PASS |
| **Replace Cp PCB with GJM Q80** | **3⅔** | **0.896104** | PASS |
| Replace Cf0 and Cf1 with GJM Q80 | 4⅓ | 0.909912 | PASS |
| **Replace Cf0 and Cp with GJM Q80** | **4⅓** | **0.879245** | PASS |
| Replace Cf1 and Cp with GJM Q80 | 4⅓ | 0.884267 | PASS |

All **permitted** candidates still miss interim IL≤0.8dB. The best area 4⅓ uses Cf0_GJM=2.494893pF, Cf1_PCB=0.200pF, Cp_GJM=1.348066pF, with k=(+0.073804,-0.024308), maximum used IC C=2.61921pF. Complete vector: `checkpoints/gjm_cf0_cp.json`; best area 3⅔: `checkpoints/gjm_cp.json`. The dominant design improvement comes from allowing the *shunt ground capacitor Cp* to be substantially larger, BUT GJM substitution simultaneously alters fixed capacitance and component Q (40→80). These effects are **not yet isolated**.

Further Q-versus-capacity contrasts were scripted in `diagnose_GJM_Q_vs_C.py` and submitted in [Actions 38784302819](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38784302819), but jobs **failed with no verified numerical output** (log fetch 404 BlobNotFound). The independent power-budget script `analyze_loss_budget.py` was submitted in [Actions 38784302918](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38784302918), also FAILED with no validated output. These are uncompleted controlled contrasts, not executed findings.

### Intrinsic modal-Q examination of the baseline 3L network

Independent unloaded lossless eigenanalysis finds the two positive finite eigenmodes correspond to currents in *L0 alone* and *L1 alone* (shunt Ls current practically zero), despite off-diagonal mutual inductance. The current eigenvectors and intrinsic mode Q remain unchanged when k is varied within model limits. B71 resonances: 1.538635GHz with Q≈14.631 and 1.616884GHz with Q≈14.706; B8: 2.104460GHz with Q≈14.673 and 2.660529GHz with Q≈14.920. For each local bypass mode, 1/Qinternal=1/25+1/Q_Ceff, Q_Ceff=(Cf+Cv)/(Cf/40+Cv/35). These numbers are **not externally loaded Q** and not full-filter attenuation. Changing k primarily affects driving-point response, transmission and matching; claiming that bigger k lowers component loss directly is unsupported under the specified constant-Q mutual model.

Numeric limitations: finite-grid local optimizers only; 30dB margin ≈0.02dB; source S2P are fixed **models**, not measurement; no component SRF, Q(f), tolerance, simultaneous sign-valid k geometry or PCB EM. Trial RF-T005 and Phase 2 remain unchanged; no Phase 3 authorization.


## 2026-10-15 owner question: passband effective L/R and mutual-coupling loss effect

**Correction to the eigenmode-only explanation above:** the driven passband magnetic-group Q, defined as `Q_L,eff(f) = omega Re[I^H Lmatrix I] / (I^H Rmatrix I)` with `Rii = omega Lii / Q25`, **does change with mutual k**. The two undriven individual resonator eigenmodes having unchanged Q is not a proof about driven passband effective Q. Mutual coupling can raise magnetic Q above each coil's Q25 when signed k × relative phase of branch currents adds magnetic stored energy.

A direct independent 7x7 branch-current MNA using both frozen external S2Ps yielded `passband_magnetic_Q_probe.json`. At **B28 803MHz**, adjusting *only* adjacent k to (+0.1,-0.1) while fixing all other C/L values:

| RF-T005 3L variant | k original -> forced | magnetic Q original -> forced | chip-L resistive dissipation original -> forced | full loaded transducer IL original -> forced |
|---|---|---|---|---|
| area3 zero GJM | (+0.07937,−0.08430) -> (+0.1,−0.1) | 25.30112 -> 25.38176 | 0.372492 -> 0.373518mW | 0.944268 -> 0.948560dB |
| area4⅓ GJM Cf0+Cp | (+0.07380,−0.02431) -> (+0.1,−0.1) | 25.13634 -> 25.29995 | **0.363526 -> 0.362269mW** | **0.879245 -> 0.885434dB** |

Thus **the owner's intuition that coupling improves passband magnetic effective Q is correct**, and in the GJM candidate the coil's *absolute* resistive loss actually decreases at this frequency. Nevertheless the system IL worsens because matching/reflection, capacitor current losses and the frozen external two-port dissipations/referred load power also change. An increase of `Q=omega*W_mag/P_L` may also result from increased magnetic energy without decreased `P_L` (area3 counterexample). The full objective is externally terminated minimax IL with H2/H3 constraints; no fixed stored magnetic energy or fixed inductor current is assumed.

In addition, previous controlled whole-band experiment `k_vs_C_sensitivity_verified_summary.json` shows reoptimized forced |k|=.1 (H2/H3>=30) has IL 0.969909dB, compared to free-k 0.944080dB, so it cannot be inferred that saturation helps the mandatory full-band objective. These observations are point-frequency and finite-grid model results, not hardware proof. New Python reproduction `analyze_passband_q.py` and its Actions job were added but **the initial workflow failed**; its failure is kept separate from independently executed JS numeric probes. The 7x7 JS probes conserve power to <4e-15mW on reported samples. More physical Q(f), true SRF and EM remain unverified.


## 2026-10-16 EXP-043 area3⅔ single-GJM-Cp IL reduction continuation

The owner requested improvement of `checkpoints/gjm_cp.json` (RF-T005 compliant chip-area **3⅔**, worst IL **0.896103794338dB**, H2/H3 ≥30.019999dB on 28×1001; independently validated 84-point 7×7 MNA). The current graph has 3 LQP02HV Q25, Cf0/Cf1 fixed PCB Q40 both 0.2pF, GJM Cp Q80 1.161299974pF, and six independently selected sets of three 0..3pF Cv Q35. Magnetic neighbor k(L0,Ls)=+0.10000, k(Ls,L1)=−0.071531. The first k and some Cs are at physical upper bounds.

**Executed independent numerical follow-up:** direct reduced-Y and required fixed input/output S2P analysis with a 28 bands ×301 samples check and bounded 9-point-per-segment coordinate search of the six independent 3-Cv groups only. Detail: `area3p667_cv_only_diagnostic.json`. The setting-specific worst IL before retuning was: B71 0.8495211, B12 0.8853195, **B28 0.8961038**, B13+B14 0.8277000, B26 0.8902799, **B8 0.8961038** dB. The B28 and B8 0.8961dB peaks are shared; H2 and/or H3 already operate near the 30.02dB numerical margin. Cv-only changes to B12 (0.885320→0.883082dB) and B13+B14 (0.827700→0.820039dB) reduce local IL but **do not improve global worst IL**. No new global candidate is claimed; the new Cv-only vector is not independently 7×7 MNA-checked.

**Designed and registered, NOT COMPUTATIONALLY EXECUTED:** `refine_one_gjm_cp.py` and `.github/workflows/exp043_one_gjm_cp_refinement.yml` implement additional multis start constrained epigraph searches with all L/C/k reoptimization, two frequency-mesh stages (9 and 31 samples per each of 28 segments), 1001-point dense verification, and explicit independent 84-point branch-current MNA. Eight first-pass branches retain fixed one GJM Cp and two PCB fixed capacitors, but rearrange tunable/non-GJM PCB positions; all are chip-area 3⅔ and RF-T005 component/Q/bound policies. [Actions 38823582063](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38823582063) **all eight jobs failed before reporting any validated circuit data**. Retrying the baseline job also failed; no valid improved IL exists from these jobs. No cause was established because redirected job logs were unavailable. The script/workflow existence must not be misconstrued as executed optimization.

**Next technical step:** diagnose GitHub Actions pre-run failures, run the existing 8-case matrix with retained error artifacts, inspect/verify best numerical vector by independently constructed 7×7 MNA and a denser critical-stopband 7001-point grid, then add adversarial adjacent-k/PCB tolerance analysis. The owner's interim IL≤0.8 goal remains unmet and cannot be claimed. Phase 3 remains **not authorized**.


### Actual passband dissipation limits of the area3⅔ circuit (independent 7×7 MNA)

Directly evaluated the unchanged `checkpoints/gjm_cp.json` with both mandatory S2P models, 50Ω source and 60−j40Ω load. Numerical proof and full five-setting point budget: `area3p667_passband_loss_budget.json`. This *numerical probing* succeeded separately from failed multi-topology GitHub Actions. Normalization Pavs=5.000mW for 1Vrms 50Ω source. Power conservation residual <4e-15mW.

| power component | B28 803MHz mW | B8 960MHz mW |
|---|---:|---:|
| chip-L resistors Q25 | 0.370445 | 0.375984 |
| input fixed S2P | 0.292735 | 0.299450 |
| output fixed S2P | 0.167149 | 0.167151 |
| fixed PCB Cs Q40 | 0.006977 | 0.010357 |
| GJM Cp Q80 | 0.027601 | 0.036242 |
| three IC Cv Q35 | 0.065031 | 0.028189 |
| reflection | 0.002262 | 0.014826 |
| **delivered Pload** | **4.067800** | **4.067800** |
| **IL** | **0.8961038 dB** | **0.8961038 dB** |
| driven magnetic Q_L_eff | 25.28988 | 25.33627 |

Both 803MHz B28 and 960MHz B8 tie the worst IL. Chip L is the largest *adjustable* loss group (~0.37mW); input external S2P and output external S2P losses are immutable model components. At B28 the reflected power is only 0.00226mW, so reducing reflection alone cannot meaningfully reach 0.8dB. To beat 0.8961 while maintaining H2/H3≥30dB, a viable optimization should lower actual L currents and L resistor power at both limiting settings. All calculations are on ideal constant-Q RF-T005; component Q(f)/SRF and EM remain open.
