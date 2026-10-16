"""EXP-044 fair comparison policy (user approved 2026-10-16).

This checks configuration gates, not RF numeric performance.
"""
from pathlib import Path
import importlib.util
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "experiments" / "chatgpt_topology_search" / "runs" /
          "EXP-044" / "search_pi3l.py")
spec = importlib.util.spec_from_file_location("exp044_pi3l_fair", SOURCE)
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / "src"))
spec.loader.exec_module(mod)


def test_fair_inductor_family_is_q25_only():
    for qs in ((33.,25.,25.), (25.,33.,25.), (25.,25.,33.),
               (33.,33.,33.)):
        with pytest.raises(ValueError, match="FAIR_COMPARISON"):
            mod.search("two_gjm_pi", None, starts=0, inductor_q=qs)


def test_gjm_three_is_rejected_before_run():
    with pytest.raises(ValueError, match="FAIR_COMPARISON"):
        mod.search("three_gjm_pi", None, starts=0,
                   inductor_q=(25.,25.,25.))


def test_allowed_pi_gjm_counts_and_area():
    for config in ("two_gjm_pi", "one_gjm_pi", "zero_gjm_pi",
                   "two_gjm_cross", "one_gjm_cross", "two_gjm_fork"):
        types, _ = mod.CONFIGS[config]
        assert sum(c == "GJM" for c in types) <= 2
        bounds, _, area, _ = mod.bounds_and_q(config)
        assert np.allclose(bounds[:3], [[.4,27]] * 3)
        assert np.isclose(area, 3 + (2/3)*sum(t == "GJM" for t in types))
        assert np.all(bounds[-18:,1] == 3.0)


def test_two_coupling_pairs_have_passive_L_matrix():
    L = np.array([9.492910336309764,8.671144999615636,
                  7.249106612243031])
    ka,kb=-.030759463646654286,-.023312444116701095
    M = np.diag(L)
    M[0,1]=M[1,0]=ka*np.sqrt(L[0]*L[1])
    M[0,2]=M[2,0]=kb*np.sqrt(L[0]*L[2])
    assert np.linalg.eigvalsh(M).min() > 0
    assert abs(ka) <= .1 and abs(kb) <= .1
    assert M[1,2] == 0.
