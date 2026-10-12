"""Read immutable formal constraints and explicit trial overrides, never auto-promote trials."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/constraints/registry.json"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _same_kind(existing, replacement):
    """Require type-compatible trial values, including nested list members."""
    if isinstance(existing, bool):
        return type(replacement) is bool
    if isinstance(existing, (int, float)):
        return type(replacement) in (int, float)
    if isinstance(existing, list):
        return isinstance(replacement, list) and (
            not existing or all(
                any(_same_kind(template, item) for template in existing)
                for item in replacement))
    return type(replacement) is type(existing)


def _merge(base, overrides):
    if not isinstance(overrides, dict):
        raise ValueError("Trial overrides must be an object")
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key not in result:
            raise ValueError(f"Unknown constraint override key: {key}")
        existing = result[key]
        if isinstance(value, dict):
            if not isinstance(existing, dict):
                raise ValueError(f"Not an object in base constraints: {key}")
            result[key] = _merge(existing, value)
        elif isinstance(existing, dict) or not _same_kind(existing, value):
            raise ValueError(f"Constraint override type mismatch: {key}")
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
