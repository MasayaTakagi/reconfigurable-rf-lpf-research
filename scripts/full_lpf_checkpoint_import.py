#!/usr/bin/env python3
"""Import an RF-F002 saved checkpoint as a canonical Full-LPF manager task.

Saved historical graphs may use a different terminal numbering convention.
This importer remaps ground/input/output to 0/1/2 before creating a task, and
keeps the source JSON as a warm-start reference rather than a performance claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "matching_limit"))

from lpf.constraint_versions import constraint_fingerprint, load_constraint  # noqa: E402
from lpf.evaluate import CASES  # noqa: E402
from p4_batch import bounds_for  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checkpoint_to_task(path: Path, *, perturb_fraction: float = 0.0,
                       perturbation_seed: int | None = None) -> dict:
    """Convert an archived EXP-017/023-style checkpoint to a manager task.

    ``perturb_fraction`` scales independent deterministic perturbations by each
    component's bounded design range. Coupling coefficients remain unchanged.
    The returned graph uses manager terminals ground=0, source=1, load=2.
    """
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("constraint_id") != "RF-F002" or data.get("objective") != "full_lpf":
        raise ValueError("Only saved formal RF-F002 full_lpf checkpoints can be imported")
    if not 0.0 <= float(perturb_fraction) <= 0.05:
        raise ValueError("perturb_fraction must be in [0, 0.05]")
    if perturb_fraction and perturbation_seed is None:
        raise ValueError("A deterministic perturbation_seed is required when perturbing")

    topology = data["topology"]
    components = data["components"]
    source_node = int(topology["input_node"])
    load_node = int(topology["output_node"])
    ground_node = int(topology["ground_node"])
    if len({source_node, load_node, ground_node}) != 3:
        raise ValueError("Checkpoint input, output, and ground nodes must be distinct")

    inductor_edges = topology["inductor_edges"]
    fixed_gjm_edges = topology.get("fixed_gjm_edges", topology.get("fixed_GJM_edges"))
    pcb_edge = topology.get("pcb_pattern_capacitor_edge", topology.get("PCB_PATTERN_C_edge"))
    variable_edges = topology.get("variable_capacitor_edges", topology.get("IC_VARIABLE_C_edges"))
    if fixed_gjm_edges is None or pcb_edge is None or variable_edges is None:
        raise ValueError("Checkpoint is missing fixed or variable capacitor edges")

    old_edges = list(inductor_edges) + list(fixed_gjm_edges) + [pcb_edge] + list(variable_edges)
    old_node_count = max(max(map(int, edge)) for edge in old_edges) + 1
    node_map = {ground_node: 0, source_node: 1, load_node: 2}
    for old_node in range(old_node_count):
        if old_node not in node_map:
            node_map[old_node] = max(node_map.values()) + 1

    def remap(edge):
        return [node_map[int(edge[0])], node_map[int(edge[1])]]

    inductor_types = components.get("series", ["LQP02HV"] * len(inductor_edges))
    if len(inductor_types) != len(inductor_edges):
        raise ValueError("Inductor series/type count differs from inductor edges")
    graph_edges = [remap(edge) + [str(kind)]
                   for edge, kind in zip(inductor_edges, inductor_types)]
    graph_edges += [remap(edge) + ["GJM01"] for edge in fixed_gjm_edges]
    graph_edges += [remap(pcb_edge) + ["PCB_PATTERN_C"]]
    mapped_variable_edges = [remap(edge) for edge in variable_edges]
    roles = [None if 0 in edge else "bridge" for edge in mapped_variable_edges]

    inductance_values = components.get("LQP02HV_nH", components.get("L_nH"))
    if inductance_values is None:
        raise ValueError("Checkpoint is missing inductor values")
    base_values = list(map(float, inductance_values))
    base_values += list(map(float, components["GJM01_pF"]))
    base_values += [float(components["PCB_PATTERN_C_pF"])]
    variable_by_setting = components.get(
        "variable_C_by_setting_pF", components.get("IC_VARIABLE_C_by_setting_pF"))
    if variable_by_setting is None:
        raise ValueError("Checkpoint is missing six-setting variable-C values")
    for case in CASES:
        values = variable_by_setting.get(case)
        if values is None or len(values) != len(mapped_variable_edges):
            raise ValueError(f"Checkpoint has invalid variable-C values for {case}")
        base_values.extend(map(float, values))

    physical_order = topology.get("chip_physical_order")
    if physical_order is None:
        physical_row = topology.get("physical_row")
        if physical_row is None:
            physical_order = list(range(len(inductor_edges)))
        else:
            physical_order = [int(str(item).removeprefix("L")) for item in physical_row]
    physical_order = list(map(int, physical_order))
    coupling_values = components.get("chip_neighbor_k", components.get("chip_adjacent_k"))
    if coupling_values is None or len(coupling_values) != max(0, len(physical_order) - 1):
        raise ValueError("Checkpoint adjacent coupling values do not match its physical row")
    coupling_matrix = np.eye(len(inductor_edges), dtype=float)
    for index, coefficient in enumerate(coupling_values):
        left, right = physical_order[index:index + 2]
        coupling_matrix[left, right] = coupling_matrix[right, left] = float(coefficient)

    policy = load_constraint("RF-F002")
    if data.get("effective_constraint_sha256", data.get("constraint_sha256")) != constraint_fingerprint(policy):
        raise ValueError("Checkpoint RF-F002 fingerprint does not match the active formal policy")
    graph = (old_node_count, tuple(tuple(edge) for edge in graph_edges))
    bounds = bounds_for(graph, variable_count=len(mapped_variable_edges), resolved_policy=policy)
    values = np.asarray(base_values, dtype=float)
    if values.shape != (len(bounds),) or np.any(~np.isfinite(values)):
        raise ValueError("Checkpoint base vector is incomplete or non-finite")
    if any(value < low - 1e-10 or value > high + 1e-10
           for value, (low, high) in zip(values, bounds)):
        raise ValueError("Checkpoint components fall outside current RF-F002 design bounds")
    if perturb_fraction:
        rng = np.random.default_rng(int(perturbation_seed))
        for index, (low, high) in enumerate(bounds):
            values[index] = np.clip(
                values[index] + rng.uniform(-perturb_fraction, perturb_fraction) * (high - low),
                low, high)

    candidate_id = str(data.get("candidate_id", path.stem))
    label = candidate_id if not perturb_fraction else f"{candidate_id}-perturbed-{perturb_fraction:g}"
    return {
        "seed_label": label,
        "source_checkpoint": str(path.relative_to(ROOT)),
        "source_checkpoint_sha256": _sha256(path),
        "source_candidate_id": candidate_id,
        "source_stored_metrics": data.get("metrics", data.get("evaluation")),
        "canonical_terminal_map": {"ground": 0, "source": 1, "load": 2,
                                    "source_checkpoint_nodes": {
                                        "ground": ground_node, "source": source_node,
                                        "load": load_node}},
        "graph": [old_node_count, [list(edge) for edge in graph_edges]],
        "variable_layout": {"edges": mapped_variable_edges, "roles": roles},
        "physical_order": physical_order,
        "initial_coupling": coupling_matrix.tolist(),
        "initial_coupling_values": list(map(float, coupling_values)),
        "initial_base_values": values.tolist(),
        "perturbation_fraction_of_component_bound": float(perturb_fraction),
        "perturbation_seed": perturbation_seed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--perturb-fraction", type=float, default=0.0)
    parser.add_argument("--seed", type=int)
    options = parser.parse_args()
    task = checkpoint_to_task(options.checkpoint, perturb_fraction=options.perturb_fraction,
                              perturbation_seed=options.seed)
    print(json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
