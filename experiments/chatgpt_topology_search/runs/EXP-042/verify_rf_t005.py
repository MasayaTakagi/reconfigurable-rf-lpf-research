#!/usr/bin/env python3
"""EXP-042 reproducible RF-T005 finite-grid + independent network verification.

Uses the *fixed, hash-verified* GitHub S2P inputs; does not reconstruct their RLC.
Not a continuous-band extremum, part-level SRF, EM, or manufacturing validation.
This checker was added after the numerical exploration and has not yet been CI-run.
"""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RIN = 50.0
ZLOAD = 60.0 - 40.0j
YLOAD = 1.0 / ZLOAD
EXPECTED = {
    "data/parasitics/circuit1_ant_coupler_0_6ghz.s2p":
        "ad266111ba1dc2b92f235d39f4a647ff271050bc11941c217661dd299ee59945",
    "data/parasitics/circuit2_poc_through_0_6ghz.s2p":
        "b3cfc861bc0c8221f49328598c9d7d0766a6e94e42e990b6a50f6c90bf9a84da",
}
CASES = ["B71", "B12", "B28", "B13+B14", "B26", "B8"]


def load_s2p(name):
    path = ROOT / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED[name], name
    arr = np.loadtxt(path, comments=["!", "#"])
    assert arr.shape == (6001, 9)
    assert np.allclose(arr[:, 0], np.arange(6001) * 1e6, atol=0.5)
    s = np.empty((6001, 2, 2), complex)
    s[:, 0, 0] = arr[:, 1] + 1j * arr[:, 2]
    s[:, 1, 0] = arr[:, 3] + 1j * arr[:, 4]
    s[:, 0, 1] = arr[:, 5] + 1j * arr[:, 6]
    s[:, 1, 1] = arr[:, 7] + 1j * arr[:, 8]
    return s


def sample_s(s, f_mhz):
    f = np.asarray(f_mhz, float)
    assert np.all((f >= 0) & (f <= 6000))
    lo = np.floor(f).astype(int)
    hi = np.minimum(lo + 1, 6000)
    w = (f - lo)[..., None, None]
    return (1 - w) * s[lo] + w * s[hi]


def s_to_y(s):
    identity = np.eye(2, dtype=complex)
    return ((identity - s) @ np.linalg.inv(identity + s)) / 50.0


def s_to_abcd(s):
    s11, s12, s21, s22 = s[..., 0, 0], s[..., 0, 1], s[..., 1, 0], s[..., 1, 1]
    a = ((1+s11)*(1-s22)+s12*s21)/(2*s21)
    b = 50*((1+s11)*(1+s22)-s12*s21)/(2*s21)
    c = ((1-s11)*(1-s22)-s12*s21)/(100*s21)
    d = ((1-s11)*(1+s22)+s12*s21)/(2*s21)
    return np.stack((np.stack((a,b),-1), np.stack((c,d),-1)), -2)


def incidence(edges):
    b = np.zeros((5, len(edges)), float)
    for j, (u,v) in enumerate(edges):
        b[u,j] += 1
        if v >= 0:
            b[v,j] -= 1
    return b


def prepare_candidate(c):
    top = c["topology"]
    assert len(top["L"]) == 4 and len(top["F"]) == 6 and len(top["V"]) <= 3
    assert all(0.4 <= x <= 27 for x in c["L_nH"])
    assert all(0 < x <= 100 for x in c["fixed_C_pF"])
    assert len(c["variable_C_by_setting_pF"]) == 6
    assert all(len(row) == len(top["V"]) for row in c["variable_C_by_setting_pF"])
    assert all(0 <= x <= 3.0 for row in c["variable_C_by_setting_pF"] for x in row)
    assert all(abs(k) <= .10000000001 for k in c["k_adjacent"])
    assert len(c["k_adjacent"]) == 3 and set(c["Q_L"]).issubset({25,33})
    assert len(top["L"]) == len(c["L_nH"]) == len(c["Q_L"])
    L = np.array(c["L_nH"], float)
    matrix = np.diag(L)
    for j,k in enumerate(c["k_adjacent"]):
        matrix[j,j+1] = matrix[j+1,j] = k * np.sqrt(L[j] * L[j+1])
    min_eig = float(np.linalg.eigvalsh(matrix).min())
    assert min_eig > 0.0, "Inductance matrix not positive definite"
    H = np.diag(L / np.asarray(c["Q_L"], float)) + 1j * matrix
    BL = incidence(top["L"])
    K = BL @ np.linalg.inv(H) @ BL.T
    BC = incidence(top["F"] + top["V"])
    C = []
    for row in c["variable_C_by_setting_pF"]:
        vals = np.r_[c["fixed_C_pF"], row]
        q = np.r_[np.full(len(top["F"]), 80.0), np.full(len(top["V"]), 35.0)]
        y_coeff = 1e-12 * vals / (1 / q - 1j)
        C.append((BC * y_coeff[None,:]) @ BC.T)
    return K, np.stack(C), min_eig


def lpf_y(K, C, settings, fs):
    om = 2 * np.pi * fs * 1e6
    return K[None,:,:] / (om[:,None,None] * 1e-9) + C[settings] * om[:,None,None]


def full_mna(Y, sp_in, sp_out):
    n = Y.shape[0]
    mat = np.zeros((n,7,7), complex)
    mat[:,:5,:5] = Y
    for s, ports in ((sp_in, (5,0)), (sp_out, (3,6))):
        y = s_to_y(s)
        for i in range(2):
            for j in range(2):
                mat[:, ports[i], ports[j]] += y[:,i,j]
    mat[:,5,5] += 1 / RIN
    mat[:,6,6] += YLOAD
    rhs = np.zeros((n,7), complex)
    rhs[:,5] = 1 / RIN
    voltage = np.linalg.solve(mat, rhs[...,None])[...,0]
    GT = 4*RIN*YLOAD.real * np.abs(voltage[:,6])**2
    IL = -10*np.log10(GT)
    Isrc = (1-voltage[:,5])/RIN
    source_delivered = Isrc.real - RIN*np.abs(Isrc)**2
    Pload = YLOAD.real*np.abs(voltage[:,6])**2
    return IL, np.min(source_delivered-Pload)


def cascade_abcd(Y, sp_in, sp_out):
    p = [0,3]
    i = [1,2,4]
    yred = Y[:,p][:,:,p] - (
        Y[:,p][:,:,i] @ np.linalg.solve(Y[:,i][:,:,i], Y[:,i][:,:,p])
    )
    y11,y12,y21,y22 = yred[:,0,0],yred[:,0,1],yred[:,1,0],yred[:,1,1]
    a = -y22/y21
    b = -1/y21
    c = -(y11*y22-y12*y21)/y21
    d = -y11/y21
    mid = np.stack((np.stack((a,b),-1),np.stack((c,d),-1)),-2)
    sys = s_to_abcd(sp_in) @ mid @ s_to_abcd(sp_out)
    den = sys[:,0,0]*ZLOAD+sys[:,0,1]+RIN*(sys[:,1,0]*ZLOAD+sys[:,1,1])
    return -10*np.log10(4*RIN*ZLOAD.real/np.abs(den)**2)


def main():
    raw = json.loads((ROOT/"data/constraints/trial/RF-T005.json").read_text())
    assert raw["base_constraint_id"] == "RF-F003" and raw["study_authorized"]
    paras_in, paras_out = [load_s2p(path) for path in EXPECTED]
    bands = list(csv.DictReader((ROOT/"data/bands.csv").open()))
    candidates = []
    for filename in ("phase2_refinement_checkpoint.json", "phase2_q33_checkpoints.json"):
        doc = json.loads((HERE/filename).read_text())
        candidates.extend(doc["results"])
    baseline = json.loads((HERE/"baseline_hv35_clipped.json").read_text())
    candidates.append(dict(source="EXP021-HV35 clipped baseline", target=30.0,
                           candidate=baseline["candidate"]))
    for result in candidates:
        c = result["candidate"]
        K, Cs, eig = prepare_candidate(c)
        worst,h2,h3 = -np.inf, np.inf, np.inf
        mismatch=0.0
        dissip_min=np.inf
        probes=0
        for band in bands:
            f=np.linspace(float(band["low_mhz"]),float(band["high_mhz"]),2001)
            si=CASES.index(band["case"])
            ss=np.full(len(f),si,dtype=int)
            Y=lpf_y(K,Cs,ss,f)
            pin=sample_s(paras_in,f)
            pout=sample_s(paras_out,f)
            il,loss=full_mna(Y,pin,pout)
            dissip_min=min(dissip_min,float(loss))
            if band["type"]=="pass":
                worst=max(worst,float(il.max()))
            elif band["region"]=="H2":
                h2=min(h2,float(il.min()))
            else:
                h3=min(h3,float(il.min()))
            ix=[0,1000,2000]
            other=cascade_abcd(Y[ix],pin[ix],pout[ix])
            mismatch=max(mismatch,float(np.max(np.abs(other-il[ix]))))
            probes+=3
        stored = result.get("dense201")
        if stored is not None:
            assert abs(stored["worst"]-worst)<2e-4
            assert abs(stored["h2"]-h2)<2e-4
            assert abs(stored["h3"]-h3)<2e-4
        assert mismatch < 1e-8
        assert dissip_min >= -1e-10
        print(json.dumps(dict(source=result.get("source", result.get("original")),target=result["target"],
            worst_IL_dB=worst,min_H2_dB=h2,min_H3_dB=h3,
            SPD_min_eig_nH=eig,MNA_ABCD_max_error_dB=mismatch,
            independent_probes=probes,minimum_network_loss_W=dissip_min)))
    print("PASS: RF-T005 finite-grid nominal model only; physical feasibility unverified")


if __name__ == "__main__":
    main()
