# P4 A status and A+ comparison gate

The user approved A: up to four internal nodes and eight circuit branches. **Do not expand the limits yet.** The comparison to expanded bounds (A+) is meaningful only after a sufficiently converged A baseline under identical objective, sample density, Q models, physical coupling rules, and numerical budget.

A remains incomplete. The local 15-cell smoke test covers exactly one selected graph per cell with one start, nominal coupling, three SLSQP iterations and three passband samples per segment. It is **not** a performance limit. A larger run (2 starts, 2 layouts, 15 iterations, 21-point validation) exceeded the interactive runtime budget and did not finish; partial data was not retained as a verified result.

New coupling pilot includes k=0, individual adjacent-chip +/-0.4 and individual PCB-PCB +/-0.6 patterns, and checks SPD. It still does not optimize continuous k, chip-to-PCB weak coupling, arbitrary chip row permutation, or physical polarity. Full A completion needs: (1) reproducible bounded compute budget and time; (2) convergence/multistart diagnostics per cost; (3) high-density worst-IL validation; (4) independent solver and passivity checks; (5) matching-only cost–IL Pareto frontier; (6) stable frontier on increasing samples/starts; (7) clearly disclosed unsampled graph classes.

Once A is complete, compare A+ with 5 or 6 internal nodes and/or 9-10 branches **one axis at a time**. Retain the same fixed chip cost<=6, PCB-L<=3, two IC C branches, and coupling bounds. Compare improvement in worst six-band UL/DL IL at equal area; a larger graph count alone is not evidence of improvement. Do not start Phase 3.
