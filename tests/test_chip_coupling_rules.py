"""Stdlib-only regression checks for owner-approved single-row coupling rules."""
import json
import math
import unittest
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT / "data/design_constraints.json").read_text())

def block_sizes(mask,n):
    sizes=[]
    size=1
    for i in range(n-1):
        if mask & (1<<i): size+=1
        else:
            sizes.append(size)
            size=1
    sizes.append(size)
    return tuple(sorted(sizes,reverse=True))

def is_positive_definite_tridiagonal_model(n,mask,kweak):
    # Positive definiteness of dense coupled L matrix via elementary Cholesky.
    M=[[1.0 if i==j else float(kweak) for j in range(n)] for i in range(n)]
    for i in range(n-1):
        if mask & (1<<i):
            M[i][i+1]=M[i+1][i]=0.15
    C=[[0.0]*n for _ in range(n)]
    for i in range(n):
        x=M[i][i]-sum(C[i][r]**2 for r in range(i))
        if x<=0: return False
        C[i][i]=math.sqrt(x)
        for j in range(i+1,n):
            C[j][i]=(M[j][i]-sum(C[j][r]*C[i][r] for r in range(i)))/C[i][i]
    return True

class ApprovedChipCouplingRules(unittest.TestCase):
    def test_policy(self):
        c=POLICY["coupling_limits"]
        l=POLICY["chip_inductor_placement"]
        self.assertIsNone(POLICY["area_budget"]["hard_cap"])
        self.assertEqual(POLICY["area_budget"]["historical_hard_cap"],6)
        self.assertEqual(c["chip_chip_strong_adjacent_abs_k_max"],0.15)
        self.assertEqual(c["chip_chip_nonstrong_abs_k_max"],0.03)
        self.assertEqual(c["chip_chip_nonstrong_nominal_k"],0)
        self.assertFalse(c["chip_chip_allow_2d_layout"])
        self.assertEqual(l["approved_layout"],"single_linear_row")
        self.assertEqual(l["strong_neighbor_degree_max"],2)
        self.assertEqual(c["pcb_pcb_abs_k_max_default"],0.15)
        self.assertEqual(c["chip_pcb_abs_k_max"],0)
        self.assertEqual(POLICY["phase3"],"paused_until_explicit_owner_approval")

    def test_adjacent_masks_and_group_shapes(self):
        for n in range(1,10):
            counts=defaultdict(int)
            shapes=defaultdict(set)
            for mask in range(1<<(n-1)):
                m=mask.bit_count()
                counts[m]+=1
                shapes[m].add(block_sizes(mask,n))
                self.assertLessEqual(m,n-1)
            self.assertEqual(sum(counts.values()),2**(n-1))
            self.assertTrue(all(counts[k]==math.comb(n-1,k) for k in range(n)))
            if n==6:self.assertEqual(sum(map(len,shapes.values())),11)
            if n==9:self.assertEqual(sum(map(len,shapes.values())),30)

    def test_model_psd_at_representative_weak_limits(self):
        # These are physical-model examples, NOT a proof that arbitrary sign
        # assignments or EM layouts with these pairwise maxima are PSD.
        for n in range(1,10):
            for mask in range(1<<(n-1)):
                for weak in (-0.03,0.0,0.03):
                    self.assertTrue(is_positive_definite_tridiagonal_model(n,mask,weak))

    def test_nine_LQP01_fit_area_six(self):
        self.assertEqual(POLICY["components"]["LQP01"]["area_units_fraction"],"2/3")
        self.assertEqual(9*2/3,6.0)

if __name__=="__main__":
    unittest.main()
