# RF-F003 external S2P: optimistic lossless-interstage insertion-loss bound

## Status and applicability
Phase 2 analytical result for the **fixed, model-derived** RF-F003 external S2P files, inherited unchanged by RF-T005. This document does not alter RF constraints, does not establish measured circuit feasibility and is **not** a bound on actual manufactured hardware absent measurement/model validation.

At 960 MHz (upper B8 downlink edge in `data/bands.csv`), inspect the 50-ohm normalized S2P files on main:
- input `data/parasitics/circuit1_ant_coupler_0_6ghz.s2p` SHA256 `ad266111ba1dc2b92f235d39f4a647ff271050bc11941c217661dd299ee59945`
- output `data/parasitics/circuit2_poc_through_0_6ghz.s2p` SHA256 `b3cfc861bc0c8221f49328598c9d7d0766a6e94e42e990b6a50f6c90bf9a84da`

Both are reciprocal and passive in the approved model. For a **passive, unconditionally stable** bilateral 2-port define `Delta=S11*S22-S12*S21`, `K=(1-|S11|^2-|S22|^2+|Delta|^2)/(2*|S12*S21|)`. The simultaneously conjugate-matched maximum available power transfer is

`G_MAG=|S21/S12|*(K-sqrt(K^2-1))`, with K>1.

The maximum available power delivered through a sequence of passive 2-ports cannot exceed the product of their individually attainable available-power gains; an inserted passive LPF can match the networks but cannot compensate dissipative energy lost in either fixed network. The product is an **optimistic** bound because it assumes lossless and individually optimal interstage matching, unconstrained reactive matching and no LPF loss. The fixed external 50-ohm generator and 60-j40-ohm load can only further restrict achievable transfer.

At 960 MHz:

| Network | K | Ideal MAG | Minimum loss (dB) |
|---|---:|---:|---:|
| Input S2P | 1.001601767936 | 0.944979320692 | 0.245776952027 |
| Output S2P | 1.000520169029 | 0.968261702943 | 0.140072451884 |
| Passive cascade bound | — | approximately 0.9150 | **0.385849403911** |

The two independent numerical optimizations of the exact two-ports' complex source/load reflection coefficients (4 real variables per network, passive |Γ|<1) reproduce their MAG respectively as 0.944979320682 and 0.968261702938 (differential evolution; no fixed-LPF model used). This independently checks the analytical MAG expressions.

Therefore **the RF-F003/RF-T005 full-system worst passband insertion loss cannot reach 0.30 dB** within this fixed S2P passive network model: the lower bound at 960MHz already exceeds 0.30dB, even with a hypothetical lossless and ideal matching LPF. This is a model-level feasibility conclusion, **not** a demonstrated optimum of the C-H30p0002 topology. EXP-042 should still optimize attainable Pareto performance and nominal 30/35dB harmonic suppression. Official IL target remains unchanged unless the user explicitly approves an RF constraint revision.

Unresolved: original input S2P topology provenance and port reference-plane uncertainty; part-level Q(f), SRF; EM, tolerance, actual measured two-port. No direct claim on hardware.
