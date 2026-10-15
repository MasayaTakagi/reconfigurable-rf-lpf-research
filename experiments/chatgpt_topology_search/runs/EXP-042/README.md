# EXP-042 — EXP-021 bridge/BSF-type 4L optimization under RF-T005 (Phase 2)

**Status: exploratory local optimizations executed; 2001-point/CSV-segment evaluation and independent 7-node MNA completed in the chat tool environment.** A portable Python checker and PR-triggered workflow are included, but the Python checker has not been asserted PASS until its CI run is observed. **Phase 3 not started.**

## Central reservation and RF conditions

The ID EXP-042 was reserved on main before the new optimization (commit `56bfb70908fa7f5613692a577733bf809d962ebc`, manually via GitHub connector because the existing workflow's `constraint_id` choice list had not yet been updated for RF-T005; main reservation re-fetched and confirmed). Never conflate this with EXP-021 under RF-T004.

- Trial **RF-T005**: RF-F003 base, up to **three** continuous IC variable-C branches per setting, **0–3pF per branch / Q35**. No changes to fixed L/C or physical topology across six settings, other than each setting's three C values.
- Four chip inductors in a single physical row, only signed *adjacent* pairs coupled and `abs(k)<=0.10`, other pairs nominal zero. In addition, full inductance matrix SPD required.
- Mandatory input S2P `data/parasitics/circuit1_ant_coupler_0_6ghz.s2p` (SHA256 `ad266111ba1dc2b92f235d39f4a647ff271050bc11941c217661dd299ee59945`); output S2P `data/parasitics/circuit2_poc_through_0_6ghz.s2p` (SHA256 `b3cfc861bc0c8221f49328598c9d7d0766a6e94e42e990b6a50f6c90bf9a84da`).
- Full external input-S2P → LPF → output-S2P cascade, 50Ω generator and frequency-independent 60−j40Ω load, `IL=-10log10(Pload/Pavs)`. Model-derived S2P (not measured); off-grid interpolate complex S real/imag linearly; do not recalculate parasitic RLC.
- Full `data/bands.csv`: **28 discontinuous CSV segments** for all 6 settings, UL/DL pass and UL H2/H3 stop, with B13+B14 sharing a setting.
- Area has no formal hard cap. 4×HV plus 6×GJM01 = **8** units, 4×LQW04 plus 6×GJM01 = **16** units; four chip L plus six fixed chip C plus three IC variable-C branches. PCB/IC physical area separate.

## Circuit definitions

Nodes 0=LPF input, 3=LPF output, 4=internal resonant node, −1=GND. In both EXP-021 layouts, `L0(0,1), L1(1,2), L2(2,3), L3(2,4)`, all with consecutive physical neighboring arrangement L0–L1–L2–L3.

- **EXP021-HV35 / Q33x4-35 source**: fixed-C edges `(1,GND),(2,GND),(4,GND),(0,2),(1,2),(2,3)`; variable-C edges `(0,1),(2,3),(1,4)`.
- **EXP021-HV30 / Q33x4-30 source**: different fixed-C and variable-C wiring, preserved in the old EXP-021 archive. For this exploratory optimization, only the **35-layout** wiring was actively optimized. The four previously saved EXP-021 candidates were separately screened at k clipped to 0.10 to understand baseline differences; the 30-layout was not optimized here.

Capacitor admittance `Yc=omega*C/(1/Q - j)`; 4-inductor coupled impedance `ZL=omega*[diag(L/Q)+j*M]` using nH times 1e−9. This is a constant-Q model, not a part-specific model.

## Executed local search

For the 35-layout, 31 real variables were adjusted: four fixed L values, six fixed GJM C values, three adjacent signed k values, and 6×3 setting-dependent variable C values. Constrained numerical search included per-chip HV inductance 0.4–27nH and fixed C exploratory bound 0.02–10pF (a **search bound**, not a new RF limit). Per-branch variable C 0–3pF, k within ±0.10. All-HV (Q25) and all-LQW04 (Q33 assumed) alternatives were compared.

Projected finite-difference Adam under a soft-min/soft-max penalty objective and 5 frequencies per CSV segment was used to make *bounded exploratory local* improvements; target levels included around 30.2–30.3dB and 35.15–35.2dB. These were NOT converged constrained SLSQP solutions or comprehensive topology/multistart searches. Refined candidates were evaluated on 201 and **2001 frequencies per CSV segment** after the fact.

**Results for 35-layout under RF-T005** (2001 frequencies per each of 28 CSV segments, full external S2P):

| Candidate | Area | Worst IL dB | Minimum H2 dB | Minimum H3 dB | Status |
|---|---:|---:|---:|---:|---|
| 4×HV, 30dB local refinement | 8 | 0.980241107 | 33.270613 | 30.344321 | ≥30dB finite mesh |
| 4×HV, 35dB local refinement | 8 | 1.051818010 | 35.213162 | 35.413974 | ≥35dB finite mesh |
| 4×LQW04, nominal 30dB starting value | 16 | 0.846099817 | 33.955844 | 30.154320 | ≥30dB finite mesh; best iteration was the start |
| 4×LQW04, 35dB local refinement | 16 | **0.911530726** | **35.200904** | **35.876103** | ≥35dB finite mesh |

A separate **4×HV, initial EXP021-HV35 values with k clipped to ±0.10**, had 15-point/segment metrics `IL 0.9595893 / H2 33.9188 / H3 31.2495 dB` and is retained in `baseline_hv35_clipped.json`. This initial candidate is lower IL than the subsequently saved HV 30dB refinement; do **not** mislabel that refinement as the best area-8/30dB result. It needs the same reproducible high-density Python checker before quantitative ranking.

**No candidate approaches the 0.30dB IL objective under this completed bounded search.** The Q33 candidate is a cost–IL trade-off, not a practical implementation recommendation. The historical RF-T004 EXP-020 0.297114dB is not an RF-T005 result.

### Independent numerical cross-checks already executed

The primary electrical metric was evaluated via (i) coupled 5-node LPF nodal admittance reduced to LPF-2port, then input/LPF/output ABCD multiplication, and (ii) independent coupled **7-node full nodal admittance**, attaching the original S2P two-port admittances directly without implicit 50Ω terminations. Each of four optimized/re-screened rows used **84 independent frequencies** (three per CSV segment) and 2001 points/segment across the 28 intervals.

Maximum observed ABCD-vs-7-node IL mismatch: **4.83×10⁻¹³dB** for HV and **1.71×10⁻¹³dB** for Q33. Series-matrix SPD checked by positive Gershgorin lower bound; all four checked rows were positive (>1.38nH), and the source-delivered-minus-load power was nonnegative. See `verify_2001_results.json` and `verify_q33_2001_results.json`. These are executed chat-runtime results; `verify_rf_t005.py` is newly authored separately for reproduction and has not yet been considered CI-PASS.

### Selected Q33×4, 35dB numerics

The full-precision values, six 3-C settings, all edges, coupling, series assumptions are in `phase2_q33_checkpoints.json`. Rounded key values:
- `L_nH = [2.3236453, 1.6352683, 7.1510405, 9.0765660]`
- `GJM_C_pF = [1.5115678, 0.6704189, 0.7246191, 1.7311888, 1.8923947, 0.6599467]`
- Adjacent `k = [+0.1000000, +0.0151661, -0.0263065]` (k01 is exactly at RF-T005 limit).
- `V_C_pF` by B71/B12/B28/B13+B14/B26/B8:
  `[[1.387800,1.255367,0.457380],[1.393642,1.248551,0.479792],[1.030654,0.878980,0.386432],[0.718743,0.742181,0.215378],[0.452835,0.448932,0.154244],[0.179321,0.078835,0.079873]]`.

## Reproduce / next work

```bash
uv sync --frozen
OPENBLAS_NUM_THREADS=1 uv run python experiments/chatgpt_topology_search/runs/EXP-042/verify_rf_t005.py
```

The checker loads original S2P from GitHub checkout and fails on SHA mismatch; it validates candidate dimensionality/bounds, SPD, the 2001-point all-segment response, 84 independent points/candidate, and nonnegative energy dissipated. Its execution status must be determined from CI evidence, not presumed from its existence.

**Unresolved:** independent CI check pending; finite mesh not a continuous-band proof; no complete local multistart, no 7001-point repeat, no robust parasitic/coupling/tolerance analysis; `LQW04 Q=33` is not verified from a particular part's Q(f)/SRF; adjacent coupling simultaneity and exact dot polarity unproven. S2P are schematic-derived rather than measured. Phase 2 only, Phase 3 stopped. Optimize alternate EXP-021 wiring and EXP-020 5L topology later if needed; keep numerical and physical conclusions separate.
