"""Policy-scoped variable-C layouts and explicit inductor graph alphabets."""
from itertools import combinations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lpf.constraint_versions import validate_variable_c_connections
from lpf.topology import validate_bridge_topology


def inductor_types(series_mode=None):
    """Return the fixed-element alphabet; None preserves the original P4-A set."""
    if series_mode in (None, "legacy"):
        return ("LQP01", "LQP02", "PCB_L", "GJM01")
    if series_mode == "HV":
        return ("LQP01", "LQP02HV", "PCB_L", "GJM01")
    if series_mode == "HQ":
        return ("LQP01", "LQP02HQ", "PCB_L", "GJM01")
    if series_mode == "both":
        return ("LQP01", "LQP02HV", "LQP02HQ", "PCB_L", "GJM01")
    raise ValueError(f"Unknown LQP02 search series mode: {series_mode!r}")


def enumerate_variable_c_layouts(graph, resolved_policy, *, max_layouts=None):
    """Enumerate policy-authorized shunts/bridges on terminals and internal nodes.

    A non-ground bridge is retained only when the fixed, ground-excluded graph
    already connects input to output and both bridge endpoints belong to that
    fixed signal component. A cap that supplies the only signal path is rejected.
    """
    n_nodes, fixed_edges = graph
    if type(n_nodes) is not int or n_nodes < 3:
        raise ValueError("A grounded graph needs ground and two terminals")
    if max_layouts is not None and (type(max_layouts) is not int or max_layouts < 1):
        raise ValueError("max_layouts must be a positive integer or None")
    layout = resolved_policy.get("trial_variable_c_layout")
    if layout is None:
        branch_count = resolved_policy["components"]["IC_VARIABLE_C"]["max_branches_principle"]
        shunt_count, bridge_count = branch_count, 0
    else:
        branch_count = layout["branch_count"]
        shunt_count = layout["shunt_to_ground"]
        bridge_count = layout["non_ground_bridge"]
    active_nodes = tuple(range(1, n_nodes))
    def generate():
        for shunts in combinations(active_nodes, shunt_count):
            shunt_edges = tuple((node, 0) for node in shunts)
            if bridge_count == 0:
                yield {"edges": shunt_edges,
                       "roles": (None,) * branch_count}
                continue
            for a, b in combinations(active_nodes, 2):
                edges = shunt_edges + ((a, b),)
                roles = (None,) * shunt_count + ("bridge",)
                metadata = tuple({"a": x, "b": y, **({"role": "bridge"}
                                if role == "bridge" else {})}
                                 for (x, y), role in zip(edges, roles))
                try:
                    validate_variable_c_connections(metadata, resolved_policy)
                    validate_bridge_topology(
                        [(x, y) for x, y, _ in fixed_edges], metadata,
                        1, 2, n_nodes - 1)
                except ValueError:
                    continue
                yield {"edges": edges, "roles": roles}

    if max_layouts is None:
        return list(generate())
    if max_layouts == 1:
        first=next(generate(),None)
        return [] if first is None else [first]
    # Two bounded-memory passes preserve even coverage of the full ordered
    # class without retaining every candidate layout in memory.
    total=sum(1 for _ in generate())
    if total<=max_layouts:
        return list(generate())
    indices={round(i*(total-1)/(max_layouts-1)) for i in range(max_layouts)}
    return [candidate for index,candidate in enumerate(generate())
            if index in indices]
