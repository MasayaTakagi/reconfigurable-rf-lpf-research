# Phase 2: matching-only intermediate shunt-C screening (2026-10-10)

## Question
Can adding a fixed shunt capacitor at the midpoint of two series LQP02 inductors reduce the six-setting worst-case UL/DL transducer insertion loss?

## Setup
- Rs=50Ω, Zload=60−j40Ω; LQP02 Q=25; fixed C Q=80; two setting-specific shunt IC C, Q=80, 0–4pF.
- Two series chip L, physically adjacent, mutual k=+0.4; fixed middle shunt C in 0–5pF.
- L bounds 0.4–8nH (provisional, not catalog verified).
- Six UL/DL band segments from data/bands.csv. Five randomized SLSQP starts; five frequency samples per segment in the objective.
- Branch-admittance formulation uses the coupled 2×2 inductor impedance matrix Z=jωM+diag(ωL/Q), with Y=B Z^-1 B^T, and capacitor admittance Yc=ωC/(1/Q−j). No H2/H3 constraints.

## Observations
- The best of five starts converged to approximately 0.1319912168dB, L1≈2.83573nH, L2≈2.83844nH, fixed middle C≈0pF.
- The historical no-middle-C two-L solution is 0.131991212dB (verified independently on a 0.02MHz grid).
- The five optimization results ranged from 0.1319912168 to 0.1319922068dB; each middle C converged to approximately zero.
- Chip area: 2 without fixed middle C; 2+2/3 if a nonzero GJM01 middle capacitor were populated.

## Interpretation and limitations
The proposed midpoint shunt C did not improve matching-only IL in this restricted experiment. The comparison is exploratory: the new trial used a **coarse five-point-per-segment grid**, not the 0.02MHz dense verification applied to the historical candidate. No global optimality claim. This result is **not** evidence that all fixed-C, multi-path, or coupled topology alternatives are inferior. Do not promote this trial to a verified performance frontier or a harmonic-compliant LPF candidate.

Recommended next experiment: add a genuinely alternative current path (not merely a shunt C), preserve shared fixed components across settings, use the common MNA solver and 0.02MHz passband verification, then compare at equal chip area.
