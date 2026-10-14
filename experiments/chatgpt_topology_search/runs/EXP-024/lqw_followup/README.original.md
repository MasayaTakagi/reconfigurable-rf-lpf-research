# EXP-017 — RF-T004 Phase-2 L/W3 follow-up (2026-10-14)

**Research status: finite local numerical exploration, saved to independent branch; not merged into main.** No Phase 3. Trial RF-T004 over formal RF-F002. Main reviewed at `e664dd7847d19dc0d02845ccf819815e54183d9e`; RF-F002 formal registry effective SHA256 `f20d27e93451dcec2f823e6f7c3731c06d843050c4d2ace8b0b46ded605542e2`. **Trial effective hash not independently resolved** and full portable code/checkpoint logs remain in the conversation ZIP, not committed here.

## Verified results (constant-Q lumped model)

| Candidate | L series L0,L1,L2,L3 | GJM | PCB-C | Chip area | Worst 6-setting IL dB | H2/H3 min dB |
|---|---|---:|---:|---:|---:|---:|
| EXP016 L baseline (30.01dB target) | HV HV HV HV | 2 | 0 | 5 1/3 | 0.357029 | >=30.01 |
| L reoptimized (30.02dB) | HV HV HV HV | 2 | 0 | 5 1/3 | 0.357180 | >=30.02 |
| W3 reoptimized | HV HV HV LQW04 | 3 | 0 | 8 | 0.309882 | >=30.02 |
| **W3-F4** | **HV HV HV LQW04** | **4** | **0** | **8 2/3** | **0.298355657** | **>=30.02** |
| **W3-F4-k012** | HV HV HV LQW04; mixed chip neighbor k capped 0.12 | 4 | 0 | 8 2/3 | **0.298755352** | >=30.02 |
| W3-PCB-34 | HV HV HV LQW04 | 3 | 1 (0.20pF Q40) | 8 | 0.303430224 | >=30.02 |
| W3-F4-H35 | HV HV HV LQW04 | 4 | 0 | 8 2/3 | 0.364695456 | >=35.02 |

These are **best-found local solutions**, not global minima. W3-F4's IL margin to 0.30dB is only ~0.001644dB, and nominal rejection margin is only ~0.02dB. New fourth GJM (Q80) is placed in parallel with L1 at nodes (3,4); tunable C remains three Q50 branches at (4,0), (5,0), (2,3), each 0–1.5pF. Existing L edges: (1,2), (3,4), (2,5), (2,3), physical row L0-L1-L3-L2; all non-neighbor k=0, neighboring |k|≤0.15. Other RF-F002 constraints preserved.

## Exploration and verification

- Defined 29 structural topologies in first local screening (9 points per continuous subband interval, one start), refined 9 selected structures separately at 30.02 and 35.02dB with multiple starts and 31-point frequency grids; screened 19 fixed PCB-C additions with two starts each and refined three by 12 starts. All are finite non-exhaustive local SLSQP runs.
- Candidate report values checked at 7,001 samples per individual subband interval, plus bounded internal extrema search and an independent 9x9 current-augmented MNA versus 5x5 nodal reduction. For W3-F4: max voltage diff ~3.04e-15V, max power residual ~3.69e-18W, normalized inductance K SPD minimum eigenvalue ~0.81398. W3-F4-k012: voltage diff ~2.17e-15V, residual ~5.20e-18W, SPD min ~0.82574. Independent MNA uses same constant-Q ideal lumped physics; EM/SRF is not verified.
- Artificial one-at-a-time parameter perturbations at fixed tuning (L and GJM C +/-1%, and neighboring k +/-0.005; 22 cases) caused **all 22** to violate at least one H2/H3>=30dB condition; worst H about 28.003dB. This is an *exploratory sensitivity*, not an approved manufacturing tolerance study.
- In a local mixed-chip coupling sweep |k|<=0.05, 0.10, 0.12, 0.15 on the same W3-F4 graph: best-found 30dB-condition IL ~0.33594, 0.30254, 0.29876, 0.29836dB. Re-optimizing with LQP02-LQW04 couplings fixed zero gave best-observed IL ~0.33264dB (8 starts). Dependence on physically realizable mixed-package coupling is substantial.
- W3-F4 refined harmonic-IL tradeoff (1201 points per band, separate from certified shortlist): Hmin~30.102dB -> IL~0.299317; Hmin~30.202 -> IL~0.300496; Hmin~30.502 -> IL~0.304074. At dense-verified 35.02dB target, W3-F4-H35 IL~0.364695, failing IL target.

## Limitations and promotion gates

LQW04 Q33 is an approved Phase-2 **numerical assumption**, but its actual inductance product range, Q(f), SRF, proximity loss and LQP02–LQW04 magnetic coupling are **not validated**. Numerical exploration applied an extra *provisional* LQW04 range 0.4–27nH; this must not be misrepresented as approved component availability. W3-F4 has HV L1=27nH at the specified upper bound, raising SRF concern especially to 2.745GHz. PCB physical area and Q(f) remain unvalidated. Additional exact full trial-hash audit, realistic EM/component proof, retuning/tolerance studies and continuous-frequency certification remain open. Do not promote these to RF-F002 formal candidates; Phase 3 remains paused.

**Reproduction artifacts:** source, detailed local search and independent verifier, original input files, exact candidates for 6 settings and manifests are in the EXP017_RFT004_L_W3_followup.zip supplied in the research conversation; the two key complete numerical vectors are preserved as JSON here.
