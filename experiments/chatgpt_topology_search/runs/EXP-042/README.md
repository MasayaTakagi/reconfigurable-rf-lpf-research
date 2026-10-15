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
