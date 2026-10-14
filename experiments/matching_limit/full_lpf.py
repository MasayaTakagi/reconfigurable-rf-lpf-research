"""Constrained epigraph minimax refinement for bounded RF-F002 graphs.

This is deliberately separate from P4-A's matching_only objective. It reuses
P4-A's graph instantiation, component bounds, RF policy resolution, common MNA,
frequency-band loader, and independent three-formulation validator.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from lpf.circuit import solve
from lpf.evaluate import CASES, evaluate_settings, load_bands
from lpf.constraint_versions import constraint_fingerprint, load_constraint
from lpf.validation import validate_circuit, validate_inductor_coupling
from instantiate_graph import AREA_THIRDS
from p4_batch import bounds_for, settings_for

ROOT = Path(__file__).resolve().parents[2]
CAP_TYPES = {"GJM01", "PCB_PATTERN_C"}
CHIP_L_TYPES = {"LQP01", "LQP02", "LQP02HV", "LQP02HQ", "LQW04"}
ALGORITHM_VERSION = "rf-f002-full-lpf-epigraph-v2-scaled"


def _frequency_records(rows, region, points):
    """Return distinct samples without joining disjoint CSV band intervals."""
    records = set()
    for row in rows:
        if row["region"] != region:
            continue
        for frequency in np.linspace(float(row["low_mhz"]), float(row["high_mhz"]), points):
            records.add((row["case"], float(frequency) * 1e6))
    return tuple(sorted(records))


def full_lpf_frequency_grid(rows=None, *, passband_points=9, stopband_points=9):
    if passband_points < 2 or stopband_points < 2:
        raise ValueError("Every frequency segment requires at least two samples")
    rows = load_bands() if rows is None else rows
    return {
        "passband": tuple(record for region in ("UL", "DL")
                           for record in _frequency_records(rows, region, passband_points)),
        "stopband": tuple(record for region in ("H2", "H3")
                          for record in _frequency_records(rows, region, stopband_points)),
    }


def _inductor_types(graph):
    return [kind for _, _, kind in graph[1] if kind not in CAP_TYPES]


def _coupling_slots(types, physical_order):
    chips = [index for index in physical_order if types[index] in CHIP_L_TYPES]
    pcbs = [index for index, kind in enumerate(types) if kind == "PCB_L"]
    # Chip inductors occupy a single row; only successive physical neighbors
    # are optimization variables. PCB-to-PCB terms are also independent slots.
    return [("chip", a, b) for a, b in zip(chips, chips[1:])] + [
        ("pcb", a, b) for a, b in combinations(pcbs, 2)
    ]


def _coupling_matrix(base, slots, coefficients):
    matrix = np.asarray(base, dtype=float).copy()
    for (_, a, b), value in zip(slots, coefficients):
        matrix[a, b] = matrix[b, a] = float(value)
    return matrix


@dataclass
class _CircuitMetrics:
    passband_il: np.ndarray
    stopband_attenuation: np.ndarray
    coupling_eigenvalue: float


class FullLPFProblem:
    """One topology/layout/coupling seed with fixed settings and tunable-C values."""

    def __init__(self, graph, variable_layout, initial_coupling, *,
                 constraint_id="RF-F002", passband_points=9, stopband_points=9,
                 physical_order=None, resolved_policy=None):
        self.graph = graph
        self.variable_layout = variable_layout
        self.policy = (load_constraint(constraint_id) if resolved_policy is None
                       else resolved_policy)
        if self.policy.get("active_constraint_id") != constraint_id:
            raise ValueError("Constraint ID and resolved policy do not match")
        self.constraint_id = constraint_id
        self.constraint_sha256 = constraint_fingerprint(self.policy)
        self.types = _inductor_types(graph)
        if not self.types:
            raise ValueError("A full-LPF candidate must contain at least one inductor")
        if np.asarray(initial_coupling).shape != (len(self.types), len(self.types)):
            raise ValueError("Initial coupling matrix dimension differs from inductor count")
        self.physical_order = (list(range(len(self.types))) if physical_order is None
                               else list(physical_order))
        if sorted(self.physical_order) != list(range(len(self.types))):
            raise ValueError("Physical inductor order must be a permutation")
        self.slots = _coupling_slots(self.types, self.physical_order)
        self.initial_coupling = np.asarray(initial_coupling, dtype=float)
        validate_inductor_coupling(
            self.types, [1e-9] * len(self.types), self.initial_coupling,
            physical_order=self.physical_order, resolved_policy=self.policy)
        self.initial_coefficients = np.asarray(
            [self.initial_coupling[a, b] for _, a, b in self.slots], dtype=float)
        self.grid = full_lpf_frequency_grid(
            passband_points=passband_points, stopband_points=stopband_points)
        self.passband_labels = self.grid["passband"]
        self.stopband_labels = self.grid["stopband"]
        self.base_bounds = bounds_for(
            graph, variable_count=len(variable_layout["edges"]),
            resolved_policy=self.policy)
        # P4-A's current sampler has no PCB_PATTERN_C alphabet, but retain the
        # formal 0.02..0.2 pF bounds if an explicitly constructed graph uses it.
        for index, (_, _, kind) in enumerate(graph[1]):
            if kind == "PCB_PATTERN_C":
                self.base_bounds[index] = (
                    float(self.policy["components"][kind]["min_pf_per_component"]),
                    float(self.policy["components"][kind]["max_pf_per_component"]))
        limits = self.policy["coupling_limits"]
        self.coupling_bounds = [
            (-float(limits["chip_chip_strong_adjacent_abs_k_max"]),
             float(limits["chip_chip_strong_adjacent_abs_k_max"]))
            if kind == "chip" else
            (-float(limits["pcb_pcb_abs_k_max_default"]),
             float(limits["pcb_pcb_abs_k_max_default"]))
            for kind, _, _ in self.slots
        ]
        self._cache_key = None
        self._cache_metrics = None

    @property
    def base_dimension(self):
        return len(self.base_bounds)

    def decode(self, vector):
        vector = np.asarray(vector, dtype=float)
        expected = self.base_dimension + len(self.slots) + 1
        if vector.shape != (expected,) or np.any(~np.isfinite(vector)):
            raise ValueError("Invalid full-LPF optimization vector")
        base = vector[:self.base_dimension]
        coefficients = vector[self.base_dimension:-1]
        epigraph = float(vector[-1])
        coupling = _coupling_matrix(self.initial_coupling, self.slots, coefficients)
        return base, coefficients, epigraph, coupling

    def metrics(self, vector):
        vector = np.asarray(vector, dtype=float)
        # The epigraph coordinate does not affect circuit analysis.
        key = vector[:-1].tobytes()
        if key == self._cache_key:
            return self._cache_metrics
        base, _, _, coupling = self.decode(vector)
        eigenvalue = (float(np.linalg.eigvalsh(coupling).min())
                      if len(coupling) else float("inf"))
        if eigenvalue <= 1e-7:
            # Keep the constraint function finite while SLSQP crosses an SPD
            # boundary; such a trial is deliberately far from feasible.
            result = _CircuitMetrics(
                passband_il=np.full(len(self.passband_labels), 1e6),
                stopband_attenuation=np.full(len(self.stopband_labels), -1e6),
                coupling_eigenvalue=eigenvalue,
            )
        else:
            settings = settings_for(
                self.graph, base, coupling, variable_layout=self.variable_layout,
                resolved_policy=self.policy, require_explicit_series=True)
            values = [float(solve(frequency, **settings[case])["il_db"])
                      for case, frequency in self.passband_labels + self.stopband_labels]
            split = len(self.passband_labels)
            result = _CircuitMetrics(
                passband_il=np.asarray(values[:split]),
                stopband_attenuation=np.asarray(values[split:]),
                coupling_eigenvalue=eigenvalue,
            )
        self._cache_key, self._cache_metrics = key, result
        return result

    def inequality_residuals(self, vector, harmonic_target_db):
        """SLSQP c(x)>=0: epigraph, H2/H3 thresholds, and full-L SPD."""
        metrics = self.metrics(vector)
        epigraph = float(vector[-1])
        # K is the normalized inductance correlation matrix; with positive L,
        # SPD(K) is equivalent to SPD(diag(sqrt(L)) K diag(sqrt(L))).
        return np.concatenate((
            epigraph - metrics.passband_il,
            metrics.stopband_attenuation - float(harmonic_target_db),
            np.asarray([metrics.coupling_eigenvalue - 1e-7]),
        ))

    def is_feasible(self, vector, harmonic_target_db, *, tolerance=1e-5):
        residuals = self.inequality_residuals(vector, harmonic_target_db)
        return bool(np.all(np.isfinite(residuals)) and np.min(residuals) >= -tolerance)

    def initial_vector(self, base_values, *, epigraph=None, coupling_values=None):
        base = np.asarray(base_values, dtype=float)
        if base.shape != (self.base_dimension,):
            raise ValueError("Initial component vector dimension mismatch")
        coefficients = (self.initial_coefficients if coupling_values is None
                        else np.asarray(coupling_values, dtype=float))
        if coefficients.shape != (len(self.slots),):
            raise ValueError("Initial coupling vector dimension mismatch")
        probe = np.concatenate((base, coefficients, [0.0]))
        worst = float(np.max(self.metrics(probe).passband_il))
        t0 = worst if epigraph is None else float(epigraph)
        return np.concatenate((base, coefficients, [t0]))

    def _verify_candidate(self, vector, points):
        base, _, _, coupling = self.decode(vector)
        if float(np.linalg.eigvalsh(coupling).min()) <= 1e-7:
            raise ValueError("Final candidate coupling matrix is not SPD")
        settings = settings_for(
            self.graph, base, coupling, variable_layout=self.variable_layout,
            resolved_policy=self.policy, require_explicit_series=True)
        rows = load_bands()
        dense = evaluate_settings(
            lambda case: settings[case], samples_per_segment=points, bands=rows)
        inductor_edges = [(a, b) for a, b, kind in self.graph[1] if kind not in CAP_TYPES]
        capacitor_edges = [(a, b) for a, b, kind in self.graph[1] if kind in CAP_TYPES]
        capacitor_edges.extend(self.variable_layout["edges"])
        reports = {}
        for case in CASES:
            frequencies = [float(f) * 1e6 for row in rows
                           if row["case"] == case and row["region"] in ("UL", "DL", "H2", "H3")
                           for f in np.linspace(float(row["low_mhz"]),
                                                float(row["high_mhz"]), points)]
            reports[case] = validate_circuit(
                settings[case], frequencies,
                expected_inductor_edges=inductor_edges,
                expected_capacitor_edges=capacitor_edges,
                inductor_types=self.types, physical_order=self.physical_order,
                resolved_policy=self.policy)
        return dense, reports

    def optimize(self, initial_vector, *, harmonic_targets=(30.0, 35.0),
                 maxiter=120, ftol=1e-8, feasibility_tolerance=1e-5):
        """Run staged 30->35 dB SLSQP epigraph minimax and revalidate densely."""
        if not harmonic_targets or any(float(x) < 30 for x in harmonic_targets):
            raise ValueError("RF-F002 requires at least 30 dB stop-band attenuation")
        if tuple(sorted(set(map(float, harmonic_targets)))) != tuple(map(float, harmonic_targets)):
            raise ValueError("Harmonic continuation targets must be strictly increasing")
        vector = np.asarray(initial_vector, dtype=float).copy()
        expected = self.base_dimension + len(self.slots) + 1
        if vector.shape != (expected,):
            raise ValueError("Initial full-LPF optimization vector dimension mismatch")
        design_bounds = self.base_bounds + self.coupling_bounds
        lower = np.asarray([item[0] for item in design_bounds], dtype=float)
        upper = np.asarray([item[1] for item in design_bounds], dtype=float)
        widths = upper - lower
        if np.any(widths <= 0):
            raise ValueError("Full-LPF design bounds must have positive width")

        def to_solver_coordinates(physical):
            return np.concatenate((2.0 * (physical[:-1] - lower) / widths - 1.0,
                                   [physical[-1]]))

        def from_solver_coordinates(scaled):
            return np.concatenate((lower + 0.5 * (scaled[:-1] + 1.0) * widths,
                                   [scaled[-1]]))

        bounds = [(-1.0, 1.0)] * len(design_bounds) + [(0.0, 100.0)]
        stages = []
        stage_vectors = []
        started = time.monotonic()
        evaluations = 0
        for target in harmonic_targets:
            def objective(z):
                nonlocal evaluations
                evaluations += 1
                return float(z[-1])

            def objective_jacobian(z):
                gradient = np.zeros_like(z)
                gradient[-1] = 1.0
                return gradient

            result = minimize(
                objective, to_solver_coordinates(vector), jac=objective_jacobian,
                method="SLSQP", bounds=bounds,
                constraints=[{"type": "ineq", "fun": lambda z, h=target:
                              self.inequality_residuals(from_solver_coordinates(z), h)}],
                options={"maxiter": int(maxiter), "ftol": float(ftol)},
            )
            vector = from_solver_coordinates(np.asarray(result.x, dtype=float))
            stage_vectors.append(vector.copy())
            residuals = self.inequality_residuals(vector, target)
            coarse_metrics = self.metrics(vector)
            stages.append({
                "harmonic_target_db": float(target),
                "success": bool(result.success),
                "message": str(result.message),
                "iterations": int(getattr(result, "nit", 0)),
                "function_evaluations": int(getattr(result, "nfev", 0)),
                "finite_difference_policy": "SciPy SLSQP default eps",
                "max_constraint_violation": float(max(0.0, -np.min(residuals))),
                "feasible_on_optimization_grid": bool(np.min(residuals) >= -feasibility_tolerance),
                "epigraph_il_db": float(vector[-1]),
                "coarse_min_harmonic_attenuation_db": float(min(
                    np.min(coarse_metrics.stopband_attenuation), float("inf"))),
                "component_values_internal_units": vector[:self.base_dimension].tolist(),
                "coupling_matrix": self.decode(vector)[3].tolist(),
            })
        elapsed = time.monotonic() - started
        verified_candidates = []
        for index, (stage, stage_vector) in enumerate(zip(stages, stage_vectors)):
            dense, validation = self._verify_candidate(stage_vector, 21)
            h2 = float(dense["min_h2_db"][0])
            h3 = float(dense["min_h3_db"][0])
            verified_candidates.append({
                "stage_index": index,
                "harmonic_target_db": stage["harmonic_target_db"],
                "optimizer_success": stage["success"],
                "optimizer_message": stage["message"],
                "optimization_grid_feasible": stage["feasible_on_optimization_grid"],
                "component_values_internal_units": stage_vector[:self.base_dimension].tolist(),
                "coupling_matrix": self.decode(stage_vector)[3].tolist(),
                "worst_il_db": float(dense["worst_il_db"][0]),
                "worst_il_case": dense["worst_il_db"][1],
                "worst_il_region": dense["worst_il_db"][2],
                "min_h2_db": h2,
                "min_h3_db": h3,
                "mandatory_30db_met_on_dense_grid": min(h2, h3) >= 30.0 - feasibility_tolerance,
                "nominal_35db_met_on_dense_grid": min(h2, h3) >= 35.0 - feasibility_tolerance,
                "il_0p30_target_met_on_dense_grid":
                    float(dense["worst_il_db"][0]) <= 0.30 + feasibility_tolerance,
                "dense_grid_samples_per_segment": 21,
                "independent_validation_by_case": validation,
            })
        best30_indices = [i for i, item in enumerate(verified_candidates)
                          if item["mandatory_30db_met_on_dense_grid"]]
        best35_indices = [i for i, item in enumerate(verified_candidates)
                          if item["nominal_35db_met_on_dense_grid"]]
        best30 = (min(best30_indices, key=lambda i: verified_candidates[i]["worst_il_db"])
                  if best30_indices else None)
        if best35_indices:
            selected_index = min(best35_indices,
                                 key=lambda i: verified_candidates[i]["worst_il_db"])
        elif best30_indices:
            selected_index = best30
        else:
            selected_index = min(range(len(verified_candidates)),
                                 key=lambda i: verified_candidates[i]["worst_il_db"])
        selected = verified_candidates[selected_index]
        vector = stage_vectors[selected_index]
        base, coefficients, _, coupling = self.decode(vector)
        target = float(stages[selected_index]["harmonic_target_db"])
        residuals = self.inequality_residuals(vector, target)
        edges = self.graph[1]
        chip_area = sum(AREA_THIRDS[kind] for _, _, kind in edges) / 3.0
        inductor_values = [float(value) for value, (_, _, kind) in zip(base, edges)
                           if kind not in CAP_TYPES]
        part_counts = {kind: sum(1 for _, _, item_kind in edges if item_kind == kind)
                       for kind in sorted({item[2] for item in edges})}
        variable_values = base[len(edges):].reshape(6, len(self.variable_layout["edges"]))
        return {
            "algorithm_version": ALGORITHM_VERSION,
            "solver_parameterization": "normalized_design_variables_minus1_to_plus1_epigraph_db",
            "finite_difference_policy": "SciPy SLSQP default eps",
            "analysis_mode": "full_lpf",
            "constraint_id": self.constraint_id,
            "effective_constraint_sha256": self.constraint_sha256,
            "graph": [self.graph[0], [list(edge) for edge in self.graph[1]]],
            "variable_cap_edges": [list(edge) for edge in self.variable_layout["edges"]],
            "variable_cap_roles": list(self.variable_layout["roles"]),
            "fixed_component_values": [
                {"edge": [a, b], "type": kind, "value": float(base[index]),
                 "unit": "pF" if kind in CAP_TYPES else "nH"}
                for index, (a, b, kind) in enumerate(edges)
            ],
            "variable_C_pf_by_setting": {
                case: variable_values[index].tolist() for index, case in enumerate(CASES)
            },
            "chip_physical_order_indices": self.physical_order,
            "component_values_internal_units": base.tolist(),
            "coupling_matrix": coupling.tolist(),
            "optimized_adjacent_and_pcb_k": coefficients.tolist(),
            "target_harmonic_attenuation_db": target,
            "continuation_stages": stages,
            "stage_candidate_verification": verified_candidates,
            "selected_stage_index": selected_index,
            "best_found_by_requirement": {
                "mandatory_30db": None if not best30_indices else {
                    "stage_index": best30,
                    "worst_il_db": verified_candidates[best30]["worst_il_db"],
                    "min_h2_db": verified_candidates[best30]["min_h2_db"],
                    "min_h3_db": verified_candidates[best30]["min_h3_db"],
                },
                "nominal_35db": None if not best35_indices else {
                    "stage_index": min(best35_indices,
                        key=lambda i: verified_candidates[i]["worst_il_db"]),
                    "worst_il_db": verified_candidates[min(best35_indices,
                        key=lambda i: verified_candidates[i]["worst_il_db"])]["worst_il_db"],
                },
            },
            "best_found_category": (
                "nominal_35db" if selected["nominal_35db_met_on_dense_grid"] else
                "mandatory_30_to_35db" if selected["mandatory_30db_met_on_dense_grid"] else
                "below_mandatory_30db"),
            "converged": bool(stages[selected_index]["success"]),
            "feasible_on_optimization_grid": bool(stages[selected_index]["feasible_on_optimization_grid"]),
            "max_final_constraint_violation": float(max(0.0, -np.min(residuals))),
            "dense_grid_constraints_met": bool(
                min(selected["min_h2_db"], selected["min_h3_db"])
                >= target - feasibility_tolerance and
                selected["worst_il_db"] <= float(vector[-1]) + feasibility_tolerance),
            "mandatory_30db_met_on_dense_grid": selected["mandatory_30db_met_on_dense_grid"],
            "nominal_35db_met_on_dense_grid": selected["nominal_35db_met_on_dense_grid"],
            "il_0p30_target_met_on_dense_grid": selected["il_0p30_target_met_on_dense_grid"],
            "chip_area_cost": chip_area,
            "part_counts": part_counts,
            "maximum_inductance_nh": max(inductor_values, default=0.0),
            "worst_il_db": selected["worst_il_db"],
            "worst_il_case": selected["worst_il_case"],
            "worst_il_region": selected["worst_il_region"],
            "min_h2_db": selected["min_h2_db"],
            "min_h3_db": selected["min_h3_db"],
            "dense_grid_samples_per_segment": 21,
            "dense_grid_only_not_interval_proof": True,
            "independent_validation_by_case": selected["independent_validation_by_case"],
            "max_independent_gain_mismatch": max(
                row["max_gain_discrepancy"]
                for row in selected["independent_validation_by_case"].values()),
            "max_power_residual_w": max(
                row["max_power_residual_w"]
                for row in selected["independent_validation_by_case"].values()),
            "min_inductance_eigenvalue_h": min(
                row["min_inductance_eigenvalue"]
                for row in selected["independent_validation_by_case"].values()
                if row["min_inductance_eigenvalue"] is not None),
            "elapsed_seconds": round(elapsed, 6),
            "objective_evaluations": evaluations,
            "no_physical_srf_qf_em_or_tolerance_validation": True,
        }


def source_fingerprint(path=None):
    """Small provenance helper for the standalone RF-F002 optimization source."""
    path = Path(__file__) if path is None else Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()
