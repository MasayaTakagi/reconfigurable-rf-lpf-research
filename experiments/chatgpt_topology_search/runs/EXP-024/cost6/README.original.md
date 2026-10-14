# EXP-018 — RF-T004 cost-six miniaturization study (Phase 2, 2026-10-14)

**Result: numerical chip-area cost 6 has been achieved, but IL ≤ 0.30 dB has not.**
The best finite local result is **0.330120277920 dB IL with H2 and H3 ≥ 30.10 dB**, using four LQP02HV inductors, three GJM fixed capacitors, three PCB pattern capacitors and three IC variable capacitors. This is **not a manufacturable/physical verification**, nor a proof of optimality.

## RF policy and provenance

- Authorized trial: RF-T004 over formal RF-F002, explicitly opted in, Phase 2 only. Main branch source snapshot inspected at `e664dd7847d19dc0d02845ccf819815e54183d9e`; official merged effective RF-T004 policy SHA256 has **not** been recalculated by the repository loader in this trial, so official candidate promotion awaits that audit.
- 50 Ω source, constant 60−j40 Ω load; B71, B12, B28, B13+B14 common, B26, B8. Evaluate each separate UL/DL/H2/H3 interval from `data/bands.csv`; B13+B14 gaps remain disconnected.
- Fixed all-band chip L/C topology and inductive coupling. Three independently variable IC capacitor branches `(4,0), (5,0), (2,3)` have setting-specific values, each 0–1.5 pF, Q=50.
- Four HV inductors, constant Q=25, 0.4–27 nH; GJM constant Q=80, ≤100 pF; PCB-pattern fixed C constant Q=40, each 0.02–0.2 pF, max three. Chip L layout `L0–L1–L3–L2`, nearest-neighbor signed k limited to ±0.15, non-neighbor nominal k=0; full K positive definite.
- **Chip-cost** = four LQP02HV packages (4) + three GJM packages (3×2/3)=**6**. PCB-pattern C, IC C, routing, board area and assembly resources are *not* included in the chip-footprint cost model. Thus equal cost-six is **not** proof of equal physical footprint.

## Saved candidate comparison (30 dB required attenuation)

| Candidate | Chip cost | PCB-pattern C count | Worst IL [dB] | Min H2 [dB] | Min H3 [dB] | Role |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| EXP-017 W3-F4 | 8⅔ | 0 | 0.298355657 | ≥30.02 | ≥30.02 | Parent, L3=LQW04 (manufacturer L/Q(f)/SRF unverified) |
| EXP-016 V | 6 | 0 | 0.352300316 | 30.009999999 | 30.009962507 | Earlier cost-six baseline |
| [C6_1PCB_H30p1.json](C6_1PCB_H30p1.json) | **6** | 1 | **0.338966441** | 30.09999999997 | 30.09999999995 | PCB C placed across L1 (3–4) |
| [C6_2PCB_H30p1.json](C6_2PCB_H30p1.json) | **6** | 2 | **0.337201958** | 30.09999999997 | 30.09999999999 | Add PCB bridge (4–5) |
| **[C6_3PCB_H30p1.json](C6_3PCB_H30p1.json)** | **6** | **3** | **0.330120278** | **30.09999999983** | **30.09999999996** | Add PCB bridge (1–5), best found |

The best cost-six candidate improves the older cost-six V by about 0.022180 dB, but **misses the 0.30 dB IL target by 0.030120 dB**. A separate 35.02 dB harmonic-constrained local optimization of the *1-PCB* graph achieved IL≈0.416688 dB; nominal 35 dB and 0.30 dB are **not both met**.

## Best topology: three PCB pattern capacitors

- Inductor edges: `L0=(1,2)` 3.354649 nH, `L1=(3,4)` 27 nH, `L2=(2,5)` 6.329805 nH, `L3=(2,3)` 5.036803 nH. All HV with Q=25.
- Physical row `L0-L1-L3-L2` with signed adjacent coupling `[+0.150000, -0.039913, -0.150000]` and nonadjacent k=0.
- Fixed GJM caps Q80: `(1,2)=2.001929pF`, `(5,0)=0.728399pF`, `(2,3)=0.837325pF`.
- Fixed PCB C caps Q40: `(3,4)=0.105980pF`, `(4,5)=0.046807pF`, `(1,5)=0.158347pF`.
- Tunable caps Q50 (all settings): branches `Cv0=(4,0)`, `Cv1=(5,0)`, `Cv2=(2,3)`. Setting-dependent values are saved in the JSON, with B71 Cv2=1.5pF limit. All three tune positions are shunts or bridges, not the sole series conduction route, so zero capacitance does not interrupt the principal L0/L3 path.

## Verification and numerical status

- Optimization: nonconvex SLSQP constrained epigraph IL minimax, fixed element/Q/connection limits, 6 setting-specific C vectors, multi-start and coarse-to-fine grids. Candidate values with `success=True` were checked at **7,001 samples per each of 28 separate frequency intervals**, with interior-frequency bounded extremum optimization; the saved 3-PCB worst case is IL=0.330120277919636 dB at **B28 DL 803 MHz**. H2=30.099999999826586 dB at **B71 H2 1396 MHz**; H3=30.09999999995685 dB at **B28 H3 2244 MHz**.
- **Independent 9×9 current-augmented MNA**, including all frequency samples; comparison with 5×5 reduced nodal method at representative frequency points: max voltage difference **3.02e−15 V**, max power-balance residual **4.34e−18 W**, min normalized magnetic coupling eigenvalue **0.82872**, confirming passivity/SPD in this lumped fixed-Q model.
- [verify.py](verify.py) reproduces full independent-current-MNA **7,001-point per-band grid** for the three saved candidates directly from this branch and its own `data/bands.csv` file. Fine local extrema refinement is separately included in the downloadable full experiment ZIP. This is *not* mathematical certification of all continuous frequencies.
- **Not verified:** true selected-part SRF, manufacturer Q(f), frequency-dependent parasitics, simultaneous physical layout of k≈0.15 neighbor pairs, chip/PCB/IC total occupied area, PCB C fabrication/tolerances, high-power RF, real switched-cap parasitics, proof of global optimality. Initial trial effective policy fingerprint not officially checked. Phase 3 remains paused.

## Scope completed vs incomplete

- Initial all-HV/3GJM/extra-PCB-C-or-PCB-L class: 25/25 topologies ×2 starts. Mixed W/LQP01 class: 15/15×3; conditional LQP01 L interval remains unverified.
- Three-chip L and W3 reduced structures: 37/40 started topologies, remaining three **not evaluated**. W with zero GJM exploratory breadth: 44/158 sampled plus focused 29/29 W3 and 14/14 W3+LQP01 runs. Distinct starts and topologies overlap; do not add these counts as unique structures. Several wider campaigns were interrupted; incomplete groups are explicitly **not exhaustive**.
- W3-F4 warm-conversion (13/40), V single-connection changes (47/76), and PCB3 circuit rewire (46/55) were partially run; missing cases remain unevaluated.
- 1-PCB refinement of 5 graph variants ×10 starts; then 30.02, 30.10 and 35.02 dB threshold continuations; 2nd PCB C placements 11 cases, best 3×10 starts; 3rd PCB C placements 10 cases, best 3×12 starts. The recorded selected best checkpoints are complete and independently checked; stalled variants are not interpreted as physical limits.

## Reproduce

```bash
uv run python experiments/chatgpt_topology_search/runs/EXP-018/verify.py
```

The selected physical/technical risks and all failure/incomplete statuses must be reviewed before any promotion to `candidates/` or the main candidate index. The full screening/optimizer histories are bundled separately with the EXP018 search archive rather than automatically committed as raw results.

**Next Phase-2 direction:** retain 1/2/3-PCB solutions as a *chip-cost/IL vs board-resource* comparison, then seek lower main-path loss for L0/L3 using circuit graph redesign, not prohibited coupling or capacitor-limit relaxations. Preserve formal RF-F002 and stop before Phase 3.
