"""Read immutable formal constraints and explicit trial overrides, never auto-promote trials."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/constraints/registry.json"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _merge(base, overrides):
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key not in result:
            raise ValueError(f"Unknown constraint override key: {key}")
        if isinstance(value, dict):
            if not isinstance(result[key], dict):
                raise ValueError(f"Not an object in base constraints: {key}")
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_constraint(constraint_id=None, *, root=ROOT, allow_trial=False):
    """Return resolved constraints; trials require explicit opt-in and registry approval."""
    root = Path(root)
    registry = _read(root / "data/constraints/registry.json")
    cid = constraint_id or registry["active_formal_id"]
    if cid in registry["formal"]:
        payload = _read(root / registry["formal"][cid]["file"])
        if payload.get("active_constraint_id") != cid:
            raise ValueError("Formal snapshot identity mismatch")
        return payload
    if cid not in registry["trial"] or not allow_trial:
        raise ValueError(f"Unknown or unapproved constraint ID: {cid}")
    entry = registry["trial"][cid]
    if entry.get("state") != "study_authorized":
        raise ValueError(f"Trial not authorized: {cid}")
    trial = _read(root / entry["file"])
    if trial.get("constraint_id") != cid or trial.get("status") != "trial":
        raise ValueError("Trial snapshot identity mismatch")
    base_id = trial["base_constraint_id"]
    if base_id not in registry["formal"]:
        raise ValueError("Trial base must be an immutable formal version")
    base = load_constraint(base_id, root=root)
    result = _merge(base, trial["overrides"])
    result["active_constraint_id"] = cid
    result["active_constraint_status"] = "trial"
    result["trial_base_constraint_id"] = base_id
    return result


def constraint_fingerprint(resolved_policy):
    """SHA-256 of canonical resolved JSON, suitable for a run manifest."""
    encoded = json.dumps(resolved_policy, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
