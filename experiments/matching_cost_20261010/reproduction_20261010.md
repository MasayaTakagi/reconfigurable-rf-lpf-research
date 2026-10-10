# Matching-only reproducibility, 2026-10-10

**Scope**: six-setting minimax UL/DL transducer IL. H2/H3 constraints deliberately omitted. One series row of LQP02 (Q25), adjacent k=+0.4, no other coupling, two shunt IC C (Q80, 0–4pF) per setting, Rs=50Ω, Zload=60−j40Ω. L>=0.4nH is a provisional search floor, not a catalog approval.

| Chip area | Historical IL (dB) | Fresh local SciPy IL (dB) |
|---:|---:|---:|
| 2 | 0.131991212 | 0.131991216 |
| 3 | 0.122209045 | 0.122209276 |
| 4 | 0.118042384 | 0.118042391 |
| 5 | 0.115868661 | 0.115868558 |
| 6 | 0.114837004 | 0.114837274 |

The local trial used SciPy SLSQP with 13 samples per passband segment during optimization and approximately 0.02 MHz for final verification. All five optimizers reported success. Differences are below 3e-7 dB; the tiny nominal improvement at area 5 is not considered a material discovery.

Run `python experiments/matching_cost_20261010/reoptimize_lqp02.py` to reproduce with repository data. This is one seeded local optimization per area, not a multistart topology search, continuous-frequency certificate, catalog/SRF validation, or globally optimal bound. The older independent 8-candidate MNA verifier remains available as `verify_adjacent_1d.py`. No full-LPF attenuation compliance is claimed.
