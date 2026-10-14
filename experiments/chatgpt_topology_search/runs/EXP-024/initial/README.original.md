# EXP-016 — ChatGPT RF-T004 Phase 2 initial topology and LQW04 study (2026-10-14)

**Status:** experimental branch checkpoint only. Not merged into main. No change to formal RF-F002, trial RF-T004, canonical candidate_index, or Phase 3 authorization.

## Provenance and RF policy

- Read GitHub main at commit `cf990d3eba625affb8e65da95b7c4f5ac4ec4be4`; formal RF-F002 registry effective SHA256 `f20d27e93451dcec2f823e6f7c3731c06d843050c4d2ace8b0b46ded605542e2`; trial RF-T004 on that fixed base, explicit opt-in.
- **RF-T004 resolved effective SHA256 not independently computed in this initial local script**; mandatory before production candidate promotion/reuse in official local-P4 infrastructure. The independent trial blob SHA as fetched: `765d0dd14d88bb7c91d1303ed896ae69132997f6`.
- 50 Ω source; 60−j40 Ω constant load; six bands and all separate UL/DL/H2/H3 intervals from `data/bands.csv`; max IL, minimum H2/H3 over each individual interval.
- Fixed chip L/ C, chip row and coupling shared across all six settings; variable capacitor values only are band dependent; IC C Q50, each 0–1.5 pF, exactly three independently variable branches; GJM Q80, chip HV Q25, selected LQW04 Q33; physical neighbor |k|≤0.15; k=0 for all nonneighbors. Full inductance matrix positive definite.
- For LQW04, **numerical exploration used an extra provisional `0.4–27 nH` search interval**, NOT an approved manufacturer inductance range. LQW04 Q=33 is an approved Phase-2 assumption; actual part availability/Q(f)/SRF and mixed package coupling are unverified.

## Previously saved results are NOT RF-T004 baselines

EXP011-01 0.293821739dB used old Q25 for 56nH and |k|~0.4; EXP015 HQ3C-01 0.301945379dB used old C 0–4pF/Q80 and |k|~0.4; do not promote these as RF-T004 compatible.

## Executed finite-search results

| Checkpoint | L series L0,L1,L2,L3 | GJM | Chip area | worst IL dB | min H2 dB | min H3 dB | Harmonic target |
|---|---|---:|---:|---:|---:|---:|---|
| A | HV,HV,HV,HV | 1 | 4⅔ | 0.370469383 | 30.0099999998 | 30.0100000000 | 30 |
| L | HV,HV,HV,HV | 2 | 5⅓ | 0.357028797 | 30.0099999942 | 30.0099999999 | 30 |
| V | HV,HV,HV,HV | 3 | 6 | 0.352300316 | 30.0099999988 | 30.0099625070 | 30 |
| W3 | HV,HV,HV,LQW04 | 3 | 8 | 0.309881825 | ≥30.01999 | ≥30.01999 | 30 |
| **W03** | **LQW04,HV,HV,LQW04** | 3 | **10** | **0.290637633** | **30.0199999981** | **30.0199057780** | 30 |
| **W023** | **LQW04,HV,LQW04,LQW04** | 3 | **12** | **0.280576126** | **30.0199999999** | **30.0199999998** | 30 |
| V-H35 | HV,HV,HV,HV | 3 | 6 | 0.423067442 | ≥35.01999 | ≥35.01999 | 35 |
| W03-H35 | LQW04,HV,HV,LQW04 | 3 | 10 | 0.354545048 | ≥35.01999 | ≥35.01999 | 35 |
| W023-H35 | LQW04,HV,LQW04,LQW04 | 3 | 12 | 0.339519213 | ≥35.01999 | ≥35.01999 | 35 |

All are **best found finite local solutions, not certified global minima or real-part performance**. LQW04 candidates are *conditional* and not qualified as physically verified. Chip area is package-footprint metric only, not PCB or IC resource area.

Search: 20 topologies ×4 initializations (80); 10 extended topologies ×5 starts (50); continuations (3×15 at 30dB, 2×12 at 35dB), series substitution searches and follow-up. Structures and choices are a finite selected set; no exhaustive topology theorem. SLSQP analytic Jacobian, epigraph IL minimax with harmonic inequalities, multi-start and continued finer frequency mesh.

## Common circuit graph for V / W03 / W023

- Nodes: `1=IN, 3=OUT, 0=GND`.
- L branches `L0=(1,2), L1=(3,4), L2=(2,5), L3=(2,3)`.
- Physical chip row `L0–L1–L3–L2`. Only row-neighbor magnetic pairs may be coupled.
- Fixed GJM C branches `Cf0=(1,2), Cf1=(5,0), Cf2=(2,3)`, each Q80.
- Independently tuned IC capacitors `Cv0=(4,0), Cv1=(5,0), Cv2=(2,3)`, each Q50, 0–1.5pF. The Cv2 branch is in parallel with a fixed L current path, so setting Cv2=0 does not open the signal line.
- Variable C and GJM C on the same branch must NOT be merged by a simple equal-Q identity: Q50 differs from Q80.

For candidate V at B8 960MHz, IL=0.352300316dB. The dB proportional loss accounting assigns L0 ~0.09877dB and L3 ~0.14446dB, together ~0.24323dB; their higher-Q substitutions motivate W03. This accounting is NOT the causal effect of replacing an individual L.

## Verification done

Representative candidates evaluated with **7,001 points per separate band interval** and local bounded searches at internal extrema; the 5×5 reduced nodal admittance solution was compared with a **9×9 current-augmented MNA** at representative frequencies. For W03, worst B8 UL/DL IL=0.29063763326343dB at **960 MHz**, minimum H2=30.0199999981dB, minimum H3=30.0199057780dB; maximum MNA voltage difference ~3.97e−15V, power balance residual ~4.34e−18W and SPD eigenvalue ~0.78498. W023: voltage difference ~3.97e−15V, power residual ~3.90e−18W, SPD eigenvalue ~0.79770. Model uses constant-Q series R-L and capacitor admittance `omega*C/(1/Q − j)`.

Verification **not done**: exact manufacturer LQW04 L range and Q(f)/SRF, EM and physical mixed-component coupling, tolerances, high-power, capacitor switch parasitics, mathematical continuous-frequency certification, global optimality. 30dB harmonic headroom only ~0.02dB for W03/W023, and W03 IL margin only ~0.00936dB.

### Next Phase-2 work

1. Verify explicit LQW04 part values, self resonance / S-parameter Q(f) and physically realizable mutual couplings; if not, reject the conditional W03/W023 candidates.
2. Reproduce official resolved RF-T004 policy hash and bring numerical experiments under the standard `src/lpf`/manifest model, with a fresh nonconflicting experiment ID if appropriate.
3. Independently rerun high-density verifier from committed exact checkpoint values; sample weak unwanted coupling and capacitor/inductor tolerances; do not start Phase 3.
4. Continue current-density and topology-directed losses minimization; optimize full 35dB targets and chip area/IL Pareto with verified L series. Preserve all legacy checkpoints.

**Repository status:** branch-only preliminary research record, pending independent integration and physical validation.