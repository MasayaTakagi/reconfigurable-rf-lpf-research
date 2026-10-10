#!/usr/bin/env python3
"""Enumerate physically-adjacent strong-chip coupling layouts (proposal, not approved).

Each physical row has n chip inductors. Only immediate-neighbor pairs are eligible
to be 'strong' (abs(k) <= 0.4). All other pairs are weak or zero, according to
a separately defined physical/EM model. Does NOT prove the physical k is feasible.

Run:
  python scripts/enumerate_chip_adjacent_couplings.py
  python scripts/enumerate_chip_adjacent_couplings.py --max-n 6 --csv > adjacency_masks.csv

Requires NumPy for eigenvalue passivity checks.
"""
import argparse
import csv
import math
import sys
from collections import defaultdict
import numpy as np


def block_lengths(mask, n):
    """Connected paths in a row: multiset of sizes, sorted in descending order."""
    sizes = []
    length = 1
    for i in range(n - 1):
        if (mask >> i) & 1:
            length += 1
        else:
            sizes.append(length)
            length = 1
    sizes.append(length)
    return tuple(sorted(sizes, reverse=True))


def normalized_K(mask, n, k_strong=0.4, k_weak=0.0):
    """Toy magnetic model for the 1-row topology; k_weak is NOT an approved bound."""
    K = np.eye(n)
    for i in range(n):
        for j in range(i+1, n):
            k = k_strong if j == i+1 and (mask >> i) & 1 else k_weak
            K[i,j] = K[j,i] = k
    return K


def enumerate_layout_masks(n):
    if n < 1:
        raise ValueError("n must be >=1")
    for mask in range(1 << (n-1)):
        strong_edges = [(i+1,i+2) for i in range(n-1) if (mask>>i)&1]
        yield {
            "n":n,
            "mask":format(mask,f"0{n-1}b") if n > 1 else "",
            "strong_pairs_count":len(strong_edges),
            "strong_pairs_1indexed":strong_edges,
            "blocks":block_lengths(mask,n),
            "lambda_min_k0p4_else0":float(np.linalg.eigvalsh(normalized_K(mask,n))[0]),
            "q_eff_if_identical_series_LQP02_k0p4":25*(1+2*len(strong_edges)*0.4/n),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-n", type=int, default=6)
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_n <= 6:
        parser.error("max-n must be in [1,6] for the current chip-area study")

    if args.csv:
        w=csv.writer(sys.stdout)
        w.writerow(("n","adjacency_mask","strong_pair_count","strong_pairs",
                    "block_sizes","normalized_K_min_eigenvalue",
                    "Q_eff_series_identical_LQP02"))
    for n in range(1,args.max_n+1):
        shapes=defaultdict(set)
        count=defaultdict(int)
        for r in enumerate_layout_masks(n):
            m = r["strong_pairs_count"]
            shapes[m].add(r["blocks"])
            count[m] += 1
            assert m <= n-1
            assert r["lambda_min_k0p4_else0"] > 0.0
            if args.csv:
                w.writerow([n,r["mask"],m,str(r["strong_pairs_1indexed"]),
                            "+".join(map(str,r["blocks"])),
                            f'{r["lambda_min_k0p4_else0"]:.9f}',
                            f'{r["q_eff_if_identical_series_LQP02_k0p4"]:.6f}'])
        assert sum(count.values()) == 2**(n-1)
        for m in range(n):
            assert count[m]==math.comb(n-1,m)
        if not args.csv:
            print(f'n={n}: {2**(n-1)} adjacency masks; '
                  f'{sum(map(len, shapes.values()))} unlabeled path-partition shapes; '
                  f'count by strong edges={dict(sorted(count.items()))}')
        if n==6:
            assert sum(map(len,shapes.values()))==11
            assert dict(count)=={0:1,1:5,2:10,3:10,4:5,5:1}


if __name__ == "__main__":
    main()
