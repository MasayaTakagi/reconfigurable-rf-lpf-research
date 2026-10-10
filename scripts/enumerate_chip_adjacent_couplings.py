#!/usr/bin/env python3
"""Enumerate approved 1-D chip coupling masks for Phase-2 cost studies.

Only physical neighbors in ONE ROW may be selected as strongly coupled
(|k|<=0.4). Nonstrong pairs: nominal k=0; weak sensitivity |k|<=0.1.
The complete inductance matrix must be positive definite.

Run:
    python scripts/enumerate_chip_adjacent_couplings.py
    python scripts/enumerate_chip_adjacent_couplings.py --max-n 9 --csv
    python scripts/enumerate_chip_adjacent_couplings.py --max-n 9 --weak-k 0.1 --csv

This is a connectivity/PSD check, NOT a demonstration of physical k feasibility.
"""
import argparse
import csv
import math
import sys
from collections import defaultdict
import numpy as np


def block_lengths(mask, n):
    """Multiset of path-component sizes for a fixed physical row."""
    sizes = []
    current = 1
    for i in range(n - 1):
        if (mask >> i) & 1:
            current += 1
        else:
            sizes.append(current)
            current = 1
    sizes.append(current)
    return tuple(sorted(sizes, reverse=True))


def normalized_K(mask, n, k_strong=0.4, k_weak=0):
    """Normalized symmetric L-matrix for selected nearest-neighbor strong pairs."""
    if n < 1 or not (0 <= abs(k_strong) <= 0.4) or not (0 <= abs(k_weak) <= 0.1):
        raise ValueError("requires n>=1, |k_strong|<=0.4, |k_weak|<=0.1")
    if not (0 <= mask < (1 << (n - 1))):
        raise ValueError("invalid adjacency mask")
    K = np.full((n, n), k_weak, dtype=float)
    np.fill_diagonal(K, 1.0)
    for i in range(n - 1):
        if (mask >> i) & 1:
            K[i, i+1] = K[i+1, i] = k_strong
    return K


def enumerate_layout_masks(n, weak_k=0.0, strong_k=0.4):
    """Every physically realizable one-row strong-edge subset at fixed order."""
    for mask in range(1 << (n-1)):
        edges = [(i+1, i+2) for i in range(n-1) if (mask >> i) & 1]
        K = normalized_K(mask, n, k_strong=strong_k, k_weak=weak_k)
        lam = float(np.linalg.eigvalsh(K)[0])
        yield {
            "n": n,
            "mask": format(mask, f"0{n-1}b") if n > 1 else "",
            "strong_pairs_count": len(edges),
            "strong_pairs_1indexed": edges,
            "block_sizes": block_lengths(mask,n),
            "lambda_min": lam,
            # Applies ONLY to equal-Q, equal-L, series-aiding coils with equal branch current:
            "Q_eff_if_identical_series_LQP02": 25*(1 + 2*len(edges)*strong_k/n) if weak_k==0 else None,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-n", type=int, default=9, help="maximum chip L count (<=9 with LQP01 at area 6)")
    parser.add_argument("--strong-k", type=float, default=0.4)
    parser.add_argument("--weak-k", type=float, default=0.0)
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_n <= 9:
        parser.error("--max-n must lie in [1,9]")
    if abs(args.strong_k)>0.4 or abs(args.weak_k)>0.1:
        parser.error("requires |strong-k|<=0.4 and |weak-k|<=0.1")
    writer=None
    if args.csv:
        writer=csv.writer(sys.stdout)
        writer.writerow(["n","adjacency_mask","strong_count","strong_pairs",
                         "block_sizes","min_normalized_L_eigenvalue","weak_k"])
    for n in range(1,args.max_n+1):
        by_count=defaultdict(int)
        shapes=defaultdict(set)
        for row in enumerate_layout_masks(n,weak_k=args.weak_k,strong_k=args.strong_k):
            m = row["strong_pairs_count"]
            by_count[m] += 1
            shapes[m].add(row["block_sizes"])
            if row["lambda_min"]<=0:
                raise RuntimeError(f"non-passive coupling matrix for n={n}, mask={row['mask']}")
            if writer is not None:
                writer.writerow([n,row["mask"],m,row["strong_pairs_1indexed"],
                                 "+".join(map(str,row["block_sizes"])),
                                 f'{row["lambda_min"]:.9f}',args.weak_k])
        assert sum(by_count.values())==2**(n-1)
        assert all(by_count[m]==math.comb(n-1,m) for m in range(n))
        if writer is None:
            print(f"n={n}: masks={2**(n-1)}; "
                  f"unlabeled component patterns={sum(map(len,shapes.values()))}; "
                  f"strong-edge histogram={dict(sorted(by_count.items()))}")
        if n==6:
            assert sum(map(len,shapes.values()))==11
        if n==9:
            assert sum(map(len,shapes.values()))==30


if __name__=="__main__":
    main()
