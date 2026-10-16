# EXP-042 — RF-T005 on C-H30p0002 (EXP-021 figure)

**Phase 2 only.** RF-T005 is the authorized three-variable-C trial of RF-F003; it is not the active formal condition. EXP-042 was reserved in the central `main` ledger (request key `rft005-exp21-bsf-20261016`).

## Circuit source and critical correction

The topology originated from the **user-supplied image** titled "EXP-021 面積6 有望LPF回路 (C-H30p0002)", not from the four selected candidates in `EXP-021/selected_checkpoints.json`. Its old RF-T004 reported performance of worst IL 0.30548 dB and H2/H3 approximately 30.0002 dB must **not** be interpreted as RF-T005 performance.

Image-node notation: L0 (1,2), L1 (2,4), L2 (2,5), L3 (2,3). Magnetic physical sequence is L0-L1-L3-L2; its only nominal mutual couplings are the three adjacent pairs. Fixed capacitors Cf0 (1,2), Cf1 (5,GND), Cf2 (2,3), PCB-pattern Cp (1,4). Tunables Cv0 (4,GND), Cv1 (5,GND), Cv2 (2,3). **Cf2 and Cv2 are parallel**, not series. Applying the rounded drawing values under the historical conditions reproduces its 0.30548-dB maximum-IL datum for the parallel circuit, whereas the series circuit loses the reported harmonic suppression. Image values are rounded and no original full-precision C-H30p0002 checkpoint has been recovered.

Elements: LQP02HV x4, Q25 each, 0.4..27nH; GJM01 x3 Q80; PCB pattern C x1 Q40, 0.02..0.2pF; variable C x3 Q35, each 0..3pF; chip cost 4+3*(2/3)=6. Physical non-neighbor mutual k=0. RF-T005 only permits |k|<=0.10 for designated adjacent pairs. All fixed elements and nominal couplings are shared across six settings.

The mandatory RF-F003 input and output Touchstone networks were read from:
- `data/parasitics/circuit1_ant_coupler_0_6ghz.s2p` with SHA256 `ad266111ba1dc2b92f235d39f4a647ff271050bc11941c217661dd299ee59945`
- `data/parasitics/circuit2_poc_through_0_6ghz.s2p` with SHA256 `b3cfc861bc0c8221f49328598c9d7d0766a6e94e42e990b6a50f6c90bf9a84da`

Both mandatory two-ports are cascaded to the LPF without artificial 50-ohm internal terminations. External transducer power uses source 50ohm, load 60-j40ohm. Frequency interpolation is linear on complex S-parameter real and imaginary parts, without extrapolation.

## Executed observations (not convergence or physical realization)

Evidence:
- `preliminary_js_5pt.json`: fixed topology local coordinate-penalty search, **1,336 candidate evaluations**, 5 points per each of 28 CSV segments. Initial RF-T005 value: IL 0.907156 dB, H2 25.469513 dB, H3 30.429995 dB; after local search: worst IL **0.866435981 dB**, min H2 **30.050925119 dB**, min H3 **30.121928876 dB**. This is a coarse-grid 30-dB feasibility candidate, not IL target achievement.
- `dense_1001_independent_check.json`: the same frozen vector verified on **1,001 points per segment**, identical worst IL/H2/H3. Separate **9x9 explicit branch-current MNA** on three probes per segment (84 total), maximum IL disagreement **1.34e-12 dB**, power-balance residual **1.13e-17 W**, no negative constituent dissipation within checked samples.

The 1,001-point worst-IL location is B13+B14 798MHz; worst H2 B13+B14 1554MHz; worst H3 B26 2547MHz. Numeric mandatory 30-dB is passed on that finite mesh, nominal 35-dB is not. **IL <=0.30dB not reached**. Rounded checkpoint for permanent comparison must not be replaced with higher-performing old RF-T004 data.

## New optimization code; execution state

- `optimize.py`: SLSQP epigraph constrained minimax, multiple initial states, distinct H2/H3 target levels **30** and **35** dB, fully cached hash-verified original RF-F003 S2P, and 301-point/segment post-optimization verification.
- `.github/workflows/exp042_rf_t005.yml`: proposed controlled GitHub Actions jobs for both target levels. The existence of the script and workflow does **not** mean the SLSQP runs were executed. Completion requires job logs and artifacts.
- Expected CLI: `OPENBLAS_NUM_THREADS=1 uv run --frozen python experiments/chatgpt_topology_search/runs/EXP-042/optimize.py --target 30 --starts 3 --maxiter 140 --grid 9 --verify-grid 301`. The 35-dB study is invoked with `--target 35` and separate output.

## Open items

New SLSQP solver execution and convergence evidence; dense 7,001-per-segment verification of any improved candidate; continuous-band stationary extrema; independent branch-MNA verification of the **final optimized vector**; S2P power balance, physical simultaneous k feasibility, PCB area, component part-number-specific Q(f)/SRF, EM, tolerances, switch/IC implementation. Phase 3 is **not** authorized.

## 2026-10-16 update — GitHub Actions SLSQP and independent verification COMPLETED

This dated addendum supersedes the earlier "SLSQP run not executed" statement above; the earlier statement is retained as an accurate historical status prior to execution.

- SLSQP source: `optimize.py`. Three starts per harmonic target, 9-point/segment optimization and 1,001-point/segment post-check, actual frozen SHA-verified S2P, pinned `uv.lock`. First run [Actions 38773925329](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38773925329) detected insufficient raw slack at exact 30/35dB boundary; not recorded as strict successes.
- Repeated with **internal 0.05dB safety margin** in [Actions 38774357292](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38774357292). Exact 29-parameter vectors archived in `selected_checkpoints_rft005.json` with original artifacts 11992827824 and 11992608049. The 30dB-margin SLSQP run did not report solver convergence; the 35dB-margin selected SLSQP run reported convergence.
- Dense final check [Actions 38774922692](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38774922692), verified in `verify.py`, proof `verified_7001.json`, raw artifact 11992359539: **28 individual `bands.csv` frequency segments ×7,001 points per candidate** plus **84 independent full 9×9 branch-current MNA points per candidate**. Both pass their *original* 30 and 35 dB harmonic requirements and remain Phase-2 constant-Q idealized numeric candidates.

| Selected candidate | worst UL/DL IL (dB) | min H2 (dB) | min H3 (dB) | area | MNA maximum IL difference | power-balance residual |
|---|---:|---:|---:|---:|---:|---:|
| EXP042-30m005 (SLSQP **nonconverged**) | **0.805148668214** | **30.049999992664** | **30.049999999108** | 6 | 3.41e-12 dB | 1.47e-17 W |
| EXP042-35m005 (SLSQP **converged**) | **0.878223792180** | **35.049999998367** | **35.049999996794** | 6 | 1.56e-12 dB | 1.04e-17 W |

L matrix is SPD: minimum eigenvalues 2.06441687nH and 2.99143488nH respectively. Physical simultaneous coupling realization, real component SRF/Q(f), PCB parasitic tolerance, EM and measurements have **not** been tested. These are **finite-mesh** validations, not mathematical continuous-frequency extremum proofs or global-optimum guarantees.

### Additional model-level feasibility finding

See `external_s2p_MAG_bound.md`: Using **only** the fixed external input and output S2P (no LPF losses) at B8-DL 960MHz, independent passive-network maximum-available-gain (MAG) analysis yields an optimistic system insertion-loss floor of **0.385849404 dB**, with input/output individual minimum losses 0.245776952/0.140072452dB. Consequently the formal **IL<=0.30dB** target cannot be met under the current mandatory S2P model by *any passive LPF*, even one with ideal lossless matching. This is a **model-specific theoretical bound**, not a physical measurement. The approved RF-F003/RF-T005 constraints remain unchanged and Phase 3 remains paused.


## RF-T005 interim objective and area Pareto (2026-10-15 UTC; executed)

User-authorized **EXP-042/RF-T005 interim** worst-case full-band IL goal **0.8 dB**; the formal RF-F003 objective **0.3 dB** and H2/H3 mandatory **30 dB**, nominal **35 dB**, remain unchanged. Numerical analysis always includes frozen mandatory external input/output S2P and 50-ohm source / 60-j40-ohm load, 28 disconnected CSV intervals. Original 4L bridge topology, 3 tunable C branches Q35 each 0..3pF, and physical strong-neighbor k<=0.10 are unchanged.

Actions runs:
- [original 30/35dB SLSQP](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38773925329) — 30dB IL 0.804524449 dB, H2 29.999980852dB / H3 29.999976614dB, numerically slightly infeasible and solver nonconverged. 35dB branch best IL 0.877414399dB, harmonic limits within <1e-8dB of 35dB but slightly below; do not claim strict 35dB.
- [fixed GJM deletion study](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38775558755) — fixed Cf1/Cf2 absorbed into parallel variable C and removed from cost.
- [fixed GJM to Q40 PCB pattern substitution](https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research/actions/runs/38775559008) — converted Cf1 and/or Cf2 from GJM01 Q80 to 0.02–0.2pF PCB-pattern C Q40, with residual capacitance absorbed by the parallel tunable. Existing Cp already occupies one of three PCB pattern C slots.

| topology/variant | chip area | PCB-C count | finite-grid worst IL dB | min H2 dB | min H3 dB |
|---|---:|---:|---:|---:|---:|
| 4HV/3GJM baseline, SLSQP30 | 6 | 1 | 0.804524449 | 29.999980852 | 29.999976614 |
| remove Cf1 GJM, use Cv1 | 5⅓ | 1 | 0.812877054 | 30.020000 | 30.020000 |
| remove Cf2 GJM, use Cv2 | 5⅓ | 1 | 0.813554271 | 30.020000 | 30.020000 |
| remove Cf1 and Cf2 | 4⅔ | 1 | 0.822191335 | 30.020000 | 30.020000 |
| replace Cf1 GJM with PCB Q40 | **5⅓** | 2 | **0.811306586** | 30.020000 | 30.020000 |
| replace Cf2 GJM with PCB Q40 | 5⅓ | 2 | 0.812800269 | 30.020000 | 30.020000 |
| replace both Cf1 and Cf2 with PCB Q40 | **4⅔** | 3 | **0.819564515** | 30.020000 | 30.020000 |

The six area variants were SLSQP optimized and assessed on 1,001 points **per separate band interval**, with independent explicit 9×9 branch-current MNA at 84 points each. For the selected 5⅓-PCB-Cf1 variant, worst MNA-ABCD discrepancy **1.54e-12dB** and max power-balance residual **1.30e-17W**, full L matrix SPD. All six independent checks PASS (no negative constituent dissipation). These are finite-grid **best-found local solutions**, not global bounds and not continuous-band proofs.

**Interpretation:** Reducing chip area from 6 to 5⅓ (11.1%) and 4⅔ (22.2%) is numerically possible under RF-T005 30dB conditions, but **no area-optimized candidate meets the interim 0.8dB IL goal yet**. Best observed at area 5⅓ is 0.811306586dB; best at 4⅔ is 0.819564515dB. PCB-C replacements increase separate PCB pattern occupation; zero chip-cost is not zero RF parasitic/physical layout cost. Capacitor Q(f), exact PCB geometry/EM, L SRF, simultaneous k, robustness and variable IC implementation remain open.

Permanent selected vectors have been curated under `checkpoints/pcb_cf1.json`, `checkpoints/pcb_both.json`, `checkpoints/cf1.json`. Trial resolved hash is held in `manifest.json`; complete candidate histories remain available as the cited time-limited Actions artifacts, not claimed as permanent Git source.


## 2026-10-16 passband effective magnetic Q of 4L pcb_cf1 (driven L/R, not resonance mode Q)

User follow-up: check the 4L winner's passband driven inductor effective Q, resistive power, harmonic attenuation and matching under mutual coupling. Original **chip area 5⅓**, H2/H3 ≥30dB, worst external-port IL **0.811306586dB** on 28×1001 saved grid. Under the physical chip row L0–L1–L3–L2, the adjacent k are **(+0.100000, +0.06018549, −0.100000)**: two of the three already saturate |k|=0.10.

Driven passband Q definition (at fixed S2P, load, Vsource and RF-T005 Q25 chip L model): Q_L_eff = omega Re(I^H Lmatrix I)/(I^H Rmatrix I), Rii=omega Li/25. This is neither undriven LC modal Q nor overall loaded Q. The calculation uses independent **9×9 branch-current MNA** and exact saved 29-element checkpoint, with separate C Q80,Q40,Q80,Q40; Q35 tunables. Source numerical JSON **`passband_magnetic_q_probe.json`**, reproducibility source **`analyze_passband_q.py`** (its initial Actions workflow run 38822400076 **FAILED**, and log was unavailable; **do not** report that independent Python CI as PASS). The original checkpoint prior 9×9 independent 84-sample checks passed.

| Pass sample | k(L1,L3) | Q_L_eff | coil ohmic dissipation mW | total external-port IL dB |
|---|---:|---:|---:|---:|
| B71 698MHz | 0.060185 original | 25.506389 | 0.236728 | 0.796022 |
| B71 698MHz | 0.100000 forced | **25.714124** | 0.238496 | **0.794318** |
| B28 803MHz | 0.060185 original | 25.482128 | 0.305714 | **0.811307** |
| B28 803MHz | 0.100000 forced | **25.682031** | **0.308175** | 0.814157 |
| B8 960MHz | 0.060185 original | 25.415969 | 0.309924 | **0.811307** |
| B8 960MHz | 0.100000 forced | **25.550239** | **0.311184** | 0.815403 |

Thus the original owner's thesis is **correct**: mutual k can raise passband energy-based Q above each L's Q25. Nevertheless its effect on actual I and total power loss is non-monotone: at 803/960MHz coil absolute dissipation and full-network IL grow when k(L1,L3) is forced to 0.1. At 698MHz the loaded IL locally improves despite bigger coil loss, due total matching redistribution. At B28 803MHz input S2P dissipates **0.293622mW**, output S2P **0.170445mW**, chip L **0.305714mW**, fixed C **0.021363mW**, IC C **0.056831mW**, reflection **0.004021mW**, output delivered **4.148006mW**, totalling **5mW** source available. The 9×9 power balance residual was <1e-14mW.

28×31 grid with **no C/L retuning**, changing only k(L1,L3): original worst IL=0.811307, min H2/H3=30.02/30.02; forced +0.1 => worst IL=0.815403 and H2/H3 minima **21.355/23.254dB**, strictly **fails RF-T005 mandatory ≥30dB**. Middle-k=0 also fails 18.988/24.996dB; all k=0 has worst IL=0.803760 but H2/H3=15.080/17.232dB. This does **not** prove no retuned +0.1 design can work; only that mutual coupling is pivotal for stopband interference, not simply loss minimization.

At B28 803MHz baseline RMS currents through (L0,L1,L2,L3) are approximately (12.415, 1.791, 0.714, 12.763)mA. The two smaller shunt branch currents imply limited mutual magnetic-energy contribution in this specific bridge topology. All results are Phase2 constant-Q lumped-model estimates, not measured part/SRF/EM performance. Phase3 remains paused.
