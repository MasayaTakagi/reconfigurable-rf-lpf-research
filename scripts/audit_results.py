#!/usr/bin/env python3
"""Lightweight audit of active Phase 2 policy, bands, and baseline metadata."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ("B71", "B12", "B28", "B13+B14", "B26", "B8")


def audit(detail=False):
    issues = []
    policy = json.loads((ROOT / "data/design_constraints.json").read_text(encoding="utf-8"))
    if policy.get("phase3") != "paused_until_explicit_owner_approval":
        issues.append("Phase 3 unexpectedly enabled")
    if policy["area_budget"]["hard_cap"] != 6:
        issues.append("Chip area cap changed")
    if policy["components"]["IC_VARIABLE_C"]["max_branches_principle"] != 2:
        issues.append("Variable C branch limit changed")
    if policy.get("canonical_docs") != "docs/specification.md":
        issues.append("Specification link is not canonical")
    if not (ROOT / "docs/specification.md").is_file():
        issues.append("Specification document missing")

    with (ROOT / "data/bands.csv").open(newline="", encoding="utf-8") as stream:
        bands = list(csv.DictReader(stream))
    for case in CASES:
        for region in ("UL", "DL", "H2", "H3"):
            if not any(x["case"] == case and x["region"] == region for x in bands):
                issues.append(f"Missing {case}/{region}")
        ul = [x for x in bands if x["case"] == case and x["region"] == "UL"]
        for multiple, region in ((2, "H2"), (3, "H3")):
            harmonics = [x for x in bands if x["case"] == case and x["region"] == region]
            if len(ul) != len(harmonics):
                issues.append(f"Invalid {case}/{region} segment count")
                continue
            for a, b in zip(ul, harmonics):
                for end in ("low_mhz", "high_mhz"):
                    if abs(float(b[end]) - multiple * float(a[end])) > 1e-8:
                        issues.append(f"Invalid {case}/{region}/{end}")

    with (ROOT / "data/candidate_index.csv").open(newline="", encoding="utf-8") as stream:
        index = list(csv.DictReader(stream))
    if {x["candidate_id"] for x in index} != {"LPF-007", "LPF-008"}:
        issues.append("Active candidate index must contain LPF-007/008 only")
    for row in index:
        name = row["candidate_id"]
        path = ROOT / "candidates" / (name + ".json")
        if not path.is_file():
            issues.append(f"Candidate JSON missing: {name}")
            continue
        item = json.loads(path.read_text(encoding="utf-8"))
        if item["candidate_id"] != name or item["objective"] != "full_lpf":
            issues.append(f"Candidate identity or objective mismatch: {name}")
        if item["spec_id"] != policy["policy_version"]:
            issues.append(f"Candidate spec mismatch: {name}")
        perf = item["performance"]
        for col, key in (("max_il_db", "worst_IL_db"), ("min_h2_db", "min_H2_db"), ("min_h3_db", "min_H3_db")):
            if abs(float(row[col]) - float(perf[key])) > 1e-6:
                issues.append(f"Candidate performance mismatch: {name} {key}")
        if item["area_units"] > policy["area_budget"]["hard_cap"]:
            issues.append(f"Candidate area cap exceeded: {name}")
        if len(item["topology"]["variable_caps"]) > 2:
            issues.append(f"Candidate variable C count exceeded: {name}")
    if detail:
        print("Cases:", len(CASES), "band segments:", len(bands), "active candidates:", len(index))
    return issues


if __name__ == "__main__":
    errors = audit(detail=True)
    if errors:
        raise SystemExit("FAILED:\n- " + "\n- ".join(errors))
    print("PASS: active policy, band definitions and baseline metadata")
