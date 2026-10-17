"""Regression guardrails for immutable LPF baselines and extensible index."""
import csv
import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.lpf.experiment_manifest import RUNS, experiment_index, new_manifest, write_manifest
from src.lpf.legacy_manifest_adapter import legacy_exp047_index_view
from src.lpf.constraint_versions import load_constraint, constraint_fingerprint
from scripts import audit_results
from scripts import verify_no_pcb_tunable_candidates as baseline

ROOT = Path(__file__).resolve().parents[1]


class BaselinePolicyGuardrails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = baseline.read_policy()
        cls.reference = baseline.read_candidate("LPF-007")

    def test_q_model_regression_is_rejected(self):
        candidate = deepcopy(self.reference)
        candidate["topology"]["inductors"][0]["Q"] = 26
        with self.assertRaisesRegex(AssertionError, "Q changed"):
            baseline.check_baseline_metadata(candidate, self.policy)

    def test_fixed_cap_q_regression_is_rejected(self):
        candidate = deepcopy(self.reference)
        candidate["topology"]["fixed_caps"][0]["Q"] = 81
        with self.assertRaisesRegex(AssertionError, "fixed capacitor Q"):
            baseline.check_baseline_metadata(candidate, self.policy)

    def test_variable_cap_connection_and_limit_are_rejected(self):
        candidate = deepcopy(self.reference)
        candidate["topology"]["variable_caps"][0]["b"] = 1
        with self.assertRaises(AssertionError):
            baseline.check_baseline_metadata(candidate, self.policy)
        candidate = deepcopy(self.reference)
        candidate["ic_variable_C_pf_by_setting"]["B8"][0] = 4.1
        with self.assertRaises(AssertionError):
            baseline.check_baseline_metadata(candidate, self.policy)

    def test_saved_performance_cannot_be_rebaselined_silently(self):
        candidate = deepcopy(self.reference)
        candidate["performance"]["worst_IL_db"] += 0.0001
        with self.assertRaisesRegex(AssertionError, "saved reference metric"):
            baseline.check_baseline_metadata(candidate, self.policy)


class CandidateIndexGuardrails(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path in ("data/design_constraints.json", "data/constraints/registry.json",
                     "data/constraints/formal/RF-F001.json", "data/bands.csv",
                     "data/candidate_index.csv", "data/experiment_index.csv", "docs/specification.md",
                     "docs/historical_results.md"):

            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, target)
        # Registry verification requires every registered trial snapshot.
        shutil.copytree(ROOT / "data/constraints", self.root / "data/constraints",
                        dirs_exist_ok=True)
        shutil.copytree(ROOT / RUNS, self.root / RUNS, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "data/parasitics", self.root / "data/parasitics")
        overlay = "data/validation/exp047_legacy_manifest_adapter_20261017.json"
        (self.root / overlay).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / overlay, self.root / overlay)
        shutil.copytree(ROOT / "data/validation/rf_f002_phase2_20261013",
                        self.root / "data/validation/rf_f002_phase2_20261013")
        for validation_dir in (
            "rf_f002_full_lpf_manager_benchmark_20261014",
            "rf_f002_convergence_20261014",
            "rf_f002_recovery_20261014",
            "rf_f002_parallel_benchmark_20261014",
            "rf_f002_warm_start_refinement_20261014",
            "rf_f002_checkpoint_warmstarts_20261014",
            "rf_f002_grid_refinement_20261014",
            "rf_f002_solver_ablation_20261014",
            "rf_f002_unscaled_followup_20261014",
        ):
            shutil.copytree(ROOT / "data/validation" / validation_dir,
                            self.root / "data/validation" / validation_dir)
        for relative in (
            "data/validation/rft003_20261013/five_L_cost6p33_candidates.json",
            "experiments/matching_limit/full_lpf.py",
            "scripts/reopt_lpf007_rf_f002.py",
            "scripts/reopt_rft003_5l_rf_f002.py",
            "scripts/reopt_rft004_seed_rf_f002.py",
        ):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        # Mirror all registered candidates so additional active candidates can
        # be audited in the temporary root without hardcoded fixture IDs.
        with (ROOT / "data/candidate_index.csv").open(newline="", encoding="utf-8") as handle:
            candidate_ids = [row["candidate_id"] for row in csv.DictReader(handle)]
        for candidate_id in candidate_ids:
            source = ROOT / "candidates" / (candidate_id + ".json")
            destination = self.root / "candidates" / (candidate_id + ".json")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def _audit(self):
        with patch.object(audit_results, "ROOT", self.root):
            return audit_results.audit()

    def _add_candidate(self, name):
        item = json.loads((self.root / "candidates/LPF-007.json").read_text())
        item["candidate_id"] = name
        item["spec_id"] = "RF-F003"
        for cap in item["topology"]["variable_caps"]:
            cap["Q"] = 35
            cap["max_pF"] = 3.0
        item["ic_variable_C_pf_by_setting"] = {
            k: [min(float(x), 3.0) for x in values]
            for k, values in item["ic_variable_C_pf_by_setting"].items()
        }
        (self.root / "candidates" / (name + ".json")).write_text(json.dumps(item))
        index = self.root / "data/candidate_index.csv"
        with index.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        m = new_manifest("EXP-999", "Synthetic candidate metadata fixture", {},
                         objective="full_lpf", seed=1)
        # Use the copied fixture policy to derive the temporary candidate
        # identity; never rely on another root's fingerprint for a new row.
        resolved = load_constraint("RF-F003", root=self.root)
        m["constraints"]["effective_constraints"] = resolved
        m["constraints"]["effective_constraint_sha256"] = constraint_fingerprint(resolved)
        directory = self.root / RUNS / "EXP-999"
        directory.mkdir()
        write_manifest(directory / "manifest.json", m, root=self.root)
        manifests = []
        for p in (self.root / RUNS).glob("EXP-*/manifest.json"):
            m = (legacy_exp047_index_view(root=self.root) if p.parent.name == "EXP-047"
                 else json.loads(p.read_text()))
            manifests.append((p.relative_to(self.root).as_posix(), m))
        (self.root / "data/experiment_index.csv").write_text(experiment_index(manifests))
        rows.append(dict(rows[0], candidate_id=name, spec_id="RF-F003",
                         evidence=f"candidates/{name}.json", constraint_class="formal",
                         constraint_id="RF-F003", historical_registry_key="",
                         effective_constraint_sha256=m["constraints"]["effective_constraint_sha256"],
                         manifest=f"{RUNS}/EXP-999/manifest.json"))
        with index.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_additional_current_policy_candidate_does_not_require_audit_edit(self):
        self._add_candidate("LPF-TEST-ADDED")
        issues = self._audit()
        with (self.root / "data/candidate_index.csv").open(newline="", encoding="utf-8") as stream:
            row = [x for x in csv.DictReader(stream)
                   if x["candidate_id"] == "LPF-TEST-ADDED"][0]
        current = load_constraint("RF-F003", root=self.root)
        self.assertEqual(issues, [], {
            "kind": row["constraint_class"], "id": row["constraint_id"],
            "spec_id": row["spec_id"],
            "row_digest": row["effective_constraint_sha256"],
            "expected_digest": constraint_fingerprint(current),
            "policy_status": current["active_constraint_status"],
        })

    def test_historical_candidate_cannot_claim_formal_spec(self):
        self._add_candidate("LPF-TEST-ADDED")
        index = self.root / "data/candidate_index.csv"
        with index.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows[-1]["constraint_class"] = "historical"
        rows[-1]["constraint_id"] = ""
        rows[-1]["effective_constraint_sha256"] = ""
        rows[-1]["manifest"] = ""
        with index.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        self.assertTrue(any("Historical candidate relabelled" in msg for msg in self._audit()))

    def test_candidate_hash_must_match_its_manifest(self):
        self._add_candidate("LPF-TEST-ADDED")
        index = self.root / "data/candidate_index.csv"
        index.write_text(index.read_text().replace(
            json.loads((self.root / "data/constraints/registry.json").read_text())["formal"]["RF-F003"]["effective_constraint_sha256"], "0" * 64))
        self.assertTrue(any("Candidate constraint fingerprint" in msg for msg in self._audit()))

    def test_manifest_index_drift_is_rejected(self):
        path = self.root / "data/experiment_index.csv"
        path.write_text(path.read_text().replace("reported_in_sources", "passed"))
        self.assertTrue(any("Experiment index differs" in msg for msg in self._audit()))

    def test_duplicate_index_row_is_rejected(self):
        index = self.root / "data/candidate_index.csv"
        with index.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows.append(dict(rows[0]))
        with index.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        self.assertTrue(any("Duplicate candidate" in msg for msg in self._audit()))

    def test_missing_required_baseline_is_rejected(self):
        index = self.root / "data/candidate_index.csv"
        with index.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        with index.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerow(rows[0])
        self.assertTrue(any("Required baseline missing" in msg for msg in self._audit()))


if __name__ == "__main__":
    unittest.main()
