#!/usr/bin/env python3
"""Lightweight metadata audit of active Phase 2 policy, bands and candidates.

Not an EM verification or a substitute for numerical circuit regression.
LPF-007/008 remain mandatory baseline entries; additional current-policy
candidates can be registered without changing this script.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.lpf.experiment_manifest import audit_provenance
CASES = ("B71", "B12", "B28", "B13+B14", "B26", "B8")
REQUIRED_BASELINES = {"LPF-007", "LPF-008"}


def read_csv(path):
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def audit(detail=False):
    issues = []
    policy = json.loads((ROOT / "data/design_constraints.json").read_text(encoding="utf-8"))
    if policy.get("phase3") != "paused_until_explicit_owner_approval":
        issues.append("Phase 3 unexpectedly enabled")
    if policy["area_budget"]["hard_cap"] is not None:
        issues.append("Formal RF policy unexpectedly imposes a chip-area cap")
    registry_path = ROOT / "data/constraints/registry.json"
    if not registry_path.is_file():
        issues.append("Constraint version registry missing")
    else:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        active_id = registry["active_formal_id"]
        record = registry["formal"].get(active_id)
        if active_id != policy.get("active_constraint_id") or record is None:
            issues.append("Active formal constraint version mismatch")
        elif json.loads((ROOT / record["file"]).read_text(encoding="utf-8")) != policy:
            issues.append("Active snapshot does not match compatibility constraints")
    if policy["components"]["IC_VARIABLE_C"]["max_branches_principle"] != 2:
        issues.append("Variable C branch limit changed")
    if policy.get("canonical_docs") != "docs/specification.md":
        issues.append("Specification link is not canonical")
    if not (ROOT / "docs/specification.md").is_file():
        issues.append("Specification document missing")
    if not (ROOT / "docs/historical_results.md").is_file():
        issues.append("Historical research index missing")

    bands = read_csv("data/bands.csv")
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

    index = read_csv("data/candidate_index.csv")
    ids = [row["candidate_id"] for row in index]
    seen = set()
    for name in ids:
        if name in seen:
            issues.append(f"Duplicate candidate in index: {name}")
        seen.add(name)
    for name in sorted(REQUIRED_BASELINES - seen):
        issues.append(f"Required baseline missing: {name}")

    for row in index:
        name = row["candidate_id"]
        # Avoid path traversal when interpreting the machine-readable index.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            issues.append(f"Invalid candidate ID: {name}")
            continue
        path = ROOT / "candidates" / (name + ".json")
        if not path.is_file():
            issues.append(f"Candidate JSON missing: {name}")
            continue
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if item["candidate_id"] != name or item["objective"] != row["objective"]:
                issues.append(f"Candidate identity or objective mismatch: {name}")
            if row["objective"] != "full_lpf":
                issues.append(f"Active candidate is not full_lpf: {name}")
            expected_spec = (policy["policy_version"] if name in {"LPF-007", "LPF-008", "LPF-009"}
                             else policy["active_constraint_id"])
            if item["spec_id"] != expected_spec or row["spec_id"] != expected_spec:
                issues.append(f"Candidate spec mismatch: {name}")
            perf = item["performance"]
            for col, key in (("max_il_db", "worst_IL_db"),
                             ("min_h2_db", "min_H2_db"),
                             ("min_h3_db", "min_H3_db")):
                a, b = float(row[col]), float(perf[key])
                if not math.isfinite(a) or not math.isfinite(b) or abs(a - b) > 1e-6:
                    issues.append(f"Candidate performance mismatch: {name} {key}")
            area = float(item["area_units"])
            if not math.isfinite(area) or area < 0:
                issues.append(f"Candidate area cap exceeded: {name}")
            variable_caps = item["topology"]["variable_caps"]
            cpolicy = (json.loads((ROOT / "data/constraints/formal/RF-F001.json").read_text(encoding="utf-8"))
                       if row.get("constraint_class") == "historical" else policy)["components"]["IC_VARIABLE_C"]
            if len(variable_caps) > cpolicy["max_branches_principle"]:
                issues.append(f"Candidate variable C count exceeded: {name}")
            for cap in variable_caps:
                if (cap["b"] != 0 or cap["Q"] != cpolicy["q"] or
                    cap["min_pF"] < cpolicy["min_total_variable_pf_per_branch"] or
                    cap["max_pF"] > cpolicy["max_total_variable_pf_per_branch"]):
                    issues.append(f"Candidate variable C policy mismatch: {name}")
            settings = item["ic_variable_C_pf_by_setting"]
            if set(settings) != set(CASES):
                issues.append(f"Candidate setting list mismatch: {name}")
            for case, cc in settings.items():
                if len(cc) != len(variable_caps) or any(
                    not math.isfinite(float(v)) or
                    float(v) < cpolicy["min_total_variable_pf_per_branch"] or
                    float(v) > cpolicy["max_total_variable_pf_per_branch"] for v in cc
                ):
                    issues.append(f"Candidate variable C values invalid: {name}/{case}")
            if row["evidence"] != "candidates/" + name + ".json":
                issues.append(f"Candidate index evidence path mismatch: {name}")
            if row["status"] != "grid_verified_nonconverged_IL_target_fail" and name in REQUIRED_BASELINES:
                issues.append(f"Baseline verification label changed: {name}")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            issues.append(f"Invalid candidate schema: {name}: {exc}")

    issues.extend(audit_provenance(root=ROOT))

    if detail:
        print("Cases:", len(CASES), "band segments:", len(bands),
              "active candidates:", len(index))
    return issues


if __name__ == "__main__":
    errors = audit(detail=True)
    if errors:
        raise SystemExit("FAILED:\n- " + "\n- ".join(errors))
    print("PASS: active policy, band definitions, baseline presence, candidate metadata and experiment provenance")
