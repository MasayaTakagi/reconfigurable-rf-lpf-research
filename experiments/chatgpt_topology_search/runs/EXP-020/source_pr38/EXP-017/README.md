# EXP-017 — RF-T004 Phase 2 continuation: Q-series and 5-L topology exploration

**Study status:** locally executed finite SLSQP topology / Q-family search; only numerical constant-Q model verification. Trial **RF-T004** pinned to formal base RF-F002. **Phase 3 not started.**

## Constraint provenance

- Formal immutable `RF-F002` effective SHA256: `f20d27e93451dcec2f823e6f7c3731c06d843050c4d2ace8b0b46ded605542e2`.
- Trial overlay `RF-T004` **resolved effective SHA256:** `c66302a281a1fdb88da355fc44dac1ef3b1c4e18e8ff297db9e842b219b5b0c4`, computed from the **official** `constraint_fingerprint` algorithm (sorted-key compact UTF-8 JSON; formal value recomputed and exactly matched the registered formal fingerprint). Specific file blobs unchanged from EXP-016.
- 50Ω source; constant 60−j40Ω load; `data/bands.csv` exact six setting segments, no joining B13/B14 sub-bands.
- Variable-C branches at most 3, 0–1.5 pF each, Q50. LQP02HV Q25; LQW04 **Q33 assumed**, chip area3, **actual part-number availability / inductance range not verified**. GJM01 Q80, chip area2/3. Chip physical row adjacent-coupling |k|≤0.15, non-neighbors nominal zero. No PCB-L.

## Additional finite exploration (executed)

- 4-L rewire / 5-L addition: 22 topology variants, 59 local SLSQP runs (14 + 45). No all-HV improvement proven above previous 4-L best.
- 4-L Q33 placement / 2GJM vs 3GJM: 34 local runs.
- 5-L Q33 / physical layout / edge placement: 64 local runs.
- 5-L fourth fixed GJM location screen: 22 local runs; promising position 3–4.
- Continuation on H2/H3 targets 35.025, 35.015, 35.008, 35.001 dB: 20 local runs.
- 30/33 dB continuation: 20 local runs.
- **Total EXP-017: 219** local optimizations. All are finite starts and finite frequency grids; not a complete topology search and no mathematical lower bound.
- Validation: 7,001 points/continuous segment on selected candidates, increased to 14,001 for final nominal-35 candidate, 84 independent branch-current 10×10 MNA spots, energy balance and positive-definite inductance matrices.

## Distinct 35dB nominal model observations

| Inductors | Fixed GJM | Chip area | Worst IL | Minimum H2/H3 | Status |
|---|---:|---:|---:|---:|---|
| 4 LQP02HV | 3 | 6 | 0.422904 dB | ≥35.01 dB | historical EXP-016 |
| 2 LQW04 + 2 HV | 3 | 10 | 0.349849 dB | ≥35.0336 dB | new, dense verified |
| 4 LQW04 | 3 | 14 | 0.334375 dB | ≥35.0342 dB | new, dense verified |
| 5 LQW04 | 4 | 17⅔ | **0.299962482 dB** | **H2 35.00799686 dB / H3 35.00800 dB** | new, 14,001-point/grid and independent MNA verified |

**Checkpoint:** [EXP017-35P008.json](EXP017-35P008.json). Five LQW04 Q33 numerical model, L edge list L0(1–2), L1(3–4), L2(2–5), L3(2–3), L4(2–3) (the last two are parallel branches). Chip physical row index [0,1,3,4,2]. Four fixed GJM branches at 1–2, 5–GND, 2–3, 3–4; three variable-C branches 4–GND, 5–GND, 2–3. Chip area=5×3+4×2/3=17⅔. Numeric minimum coupling-matrix eigenvalue 0.785127584. 84 independent 10×10 MNA spots: largest voltage mismatch 5.56e−15V, power discrepancy 1.38e−17W.

For the **30dB minimum-only** research tier, 4-L 2 LQW04 + 2 HV at area10 attained **IL 0.294008244dB, minimum H2/H3≥30.02998dB** (7,001 pts/continuous interval, 84 independent spots). A 4-L 4-LQW variant at area14 attained IL 0.276932845dB, H2/H3≥30.02926dB. These are **not 35dB-achieving designs**.

## Risks and interpretation

- 0.299962482dB model IL leaves **0.000037518dB** margin. Harmonic margin only **0.007997dB**. This is a **mathematical simulation checkpoint**, not an implementable robust RF-LPF declaration.
- L1 is **27nH LQW04**, for which actual catalog range, Q(f), parasitics and SRF have **not been checked**. Five LQW04 packages and four GJM01 cost 17⅔, far larger than legacy 6-unit candidates.
- Strong neighboring signed couplings reach ±0.15; geometry/dot orientation/simultaneous k not physically established.
- Exploratory unrecalibrated tolerance screen: 200 independently drawn cases with L/C 0.1% Gaussian sigma, k sigma=0.001 (clipped to ±0.15), fixed variable-C codes and 101 points/segment yielded **0/200** fully satisfying both IL≤0.30 and min attenuation≥35dB. **This is not a statistical manufacturing yield estimate** and does not permit extrapolation to re-tuned hardware.
- A coarser 30dB low-IL solution and high-area 35dB nominal solution must not be conflated.
- Local project source code, per-run solver outputs, sensitivity records and independent checks are preserved in the companion **EXP-017 local archive**. GitHub Actions, device-model/SRF, EM, lot variation and robustness optimization are **not executed**.
- Formal RF-F002 not changed; trial checkpoint never automatically promoted; Phase 3 remains paused.

**Next development gate:** Verify candidate with reproducible pinned source, identify actual LQW04-compatible L values/S-parameters at 0.6–2.75GHz, then seek lower-area robust 3C topologies; target margin needs to be materially larger before any implementation claim.
