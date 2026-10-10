# External review / contribution guide

Please use Issues for model concerns, missing physical effects, reproduction mismatches, or topology suggestions. Use PRs for documented fixes. Do not treat an optimizer's `success` flag as mathematical proof.

A reproducible performance claim should state: (1) topology/netlist, (2) all component and coupling values, (3) element loss model, (4) power-wave reference planes and normalization, (5) all band frequency ranges, (6) numerical constraints and min/max frequencies, (7) raw data and execution command, (8) energy-balance/passivity checks, (9) uncertainty or failure cases.

Out-of-scope without explicit project-owner approval: Phase 3 switched-capacitor bit/code optimization, public release of any private third-party model, changes to the required 30 dB attenuation, and claiming physical manufacturability solely from positive-definite inductance matrices.
