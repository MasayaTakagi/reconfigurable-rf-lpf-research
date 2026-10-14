#!/usr/bin/env python3
"""EXP-017: verify fixed RF-T004 numerical checkpoint, not physical SRF/EM."""
import csv
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]  # repository root: EXP-017/runs/chatgpt_topology_search/experiments/repo


def incidence(edges, nodes=5):
    d = np.zeros((len(edges), nodes), float)
    for i, (a, b) in enumerate(edges):
        if a:
            d[i, a-1] += 1
        if b:
            d[i, b-1] -= 1
    return d


def verify(candidate, bands, points=14001):
    d = json.loads(Path(candidate).read_text(encoding="utf-8"))
    t = d["topology"]
    L = np.asarray(t["inductor_L_nH"], dtype=float) * 1e-9
    Q = np.asarray(t["inductor_Q"], dtype=float)
    assert d["constraint_id"] == "RF-T004"
    assert len(L) == 5 and len(t["variable_C_edges"]) == 3
    assert len(t["fixed_GJM01_edges"]) == 4
    K = np.eye(len(L))
    M = np.diag(L)
    for i, k in enumerate(t["signed_neighbor_k"]):
        a, b = t["physical_row_inductor_indices"][i:i+2]
        assert abs(k) <= 0.150000001
        K[a, b] = K[b, a] = k
        M[a, b] = M[b, a] = k * np.sqrt(L[a] * L[b])
    lam_min = float(np.linalg.eigvalsh(K).min())
    assert lam_min > 0
    B = incidence(t["inductor_edges"]).T
    D = incidence(t["fixed_GJM01_edges"] + t["variable_C_edges"])
    qC = np.asarray([80] * 4 + [50] * 3)
    ycoef = 1 / (1/qC - 1j)
    ports = np.zeros((5, 5), complex)
    ports[0, 0] = 1 / 50
    ports[2, 2] = 1 / (60 - 40j)
    source = np.array([1/50, 0, 0, 0, 0], complex)
    segs = list(csv.DictReader(Path(bands).open(encoding="utf-8")))
    per = {}
    max_diff, max_power, ncheck = 0., 0., 0
    for case, Cv in t["variable_C_by_setting_pF"].items():
        assert len(Cv) == 3 and all(0 <= c <= 1.5 for c in Cv)
        C = np.r_[t["fixed_GJM01_C_pF"], Cv] * 1e-12
        ybase = C * ycoef
        yc = D.T @ np.diag(ybase) @ D
        Zbase = np.diag(L/Q) + 1j * M
        yin = B @ np.linalg.solve(Zbase, B.T)
        metrics = {"pass": [], "H2": [], "H3": []}
        for seg in (r for r in segs if r["case"] == case):
            low, high = float(seg["low_mhz"]), float(seg["high_mhz"])
            ws = np.linspace(low, high, points) * (2 * np.pi * 1e6)
            # Five-node nodal Schur complement, all samples in this segment.
            A = ports[None, :, :] + ws[:, None, None] * yc[None, :, :] + yin[None, :, :] / ws[:, None, None]
            V = np.linalg.solve(A, np.broadcast_to(source, (len(ws), 5))[..., None])[..., 0]
            IL = -10 * np.log10(np.maximum(200*60/5200 * np.abs(V[:, 2])**2, 1e-300))
            reg = "pass" if seg["region"] in ("UL", "DL") else seg["region"]
            metrics[reg].append(float(IL.max() if reg == "pass" else IL.min()))
            # Independent 10x10 branch-current MNA at 3 spots per segment.
            for f in np.linspace(low, high, 3):
                w = 2 * np.pi * f * 1e6
                y = w * ybase
                Ys = ports + D.T @ np.diag(y) @ D
                ZL = w * Zbase
                full = np.block([[Ys, B], [B.T, -ZL]])
                sol = np.linalg.solve(full, np.r_[source, np.zeros(len(L))])
                v, coil_i = sol[:5], sol[5:]
                v_reduced = np.linalg.solve(Ys + B @ np.linalg.solve(ZL, B.T), source)
                max_diff = max(max_diff, float(np.max(np.abs(v-v_reduced))))
                Pav = 1/(4*50)
                Pref = np.abs(v[0]-0.5)**2/50
                Pload = np.abs(v[2])**2*60/5200
                Pcoil = float(np.sum(w*L/Q * np.abs(coil_i)**2))
                Pcap = float(np.sum(y.real * np.abs(D @ v)**2))
                max_power = max(max_power, float(abs(Pav-Pref-Pload-Pcoil-Pcap)))
                ncheck += 1
        per[case] = (max(metrics["pass"]), min(metrics["H2"]), min(metrics["H3"]))
    observed = (
        max(p[0] for p in per.values()),
        min(p[1] for p in per.values()),
        min(p[2] for p in per.values()),
    )
    expected = d["performance"]
    assert np.allclose(observed, [
        expected["maximum_worst_IL_db"],
        expected["minimum_H2_db"],
        expected["minimum_H3_db"],
    ], rtol=0, atol=1e-6)
    assert ncheck == 84 and max_diff < 1e-11 and max_power < 1e-11
    assert observed[0] < .30 and observed[1] > 35 and observed[2] > 35
    print("PASS", "IL/H2/H3:", observed, "SPD eigmin:", lam_min,
          "independent MNA:", ncheck, "dV:", max_diff, "power residual:", max_power)
    print("WARNING: nominal lumped constant-Q only; LQW04/SRF/EM/robustness unverified.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default=str(HERE / "EXP017-35P008.json"))
    ap.add_argument("--bands", default=str(ROOT / "data/bands.csv"))
    ap.add_argument("--points", type=int, default=14001)
    a = ap.parse_args()
    verify(a.candidate, a.bands, a.points)
