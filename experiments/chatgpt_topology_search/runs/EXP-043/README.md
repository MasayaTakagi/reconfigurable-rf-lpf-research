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
