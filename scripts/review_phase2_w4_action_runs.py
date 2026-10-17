#!/usr/bin/env python3
"""W4: observe GitHub Actions API-visible history for every tracked workflow.

Read-only HTTPS requests. A latest-page sample is not complete run provenance.
Do not authorize deletion on absent/zero currently visible runs.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER_REPO = "MasayaTakagi/reconfigurable-rf-lpf-research"
BASE = "26cacd179146bda5f5ca1cdcf0096dd61eb4faae"
FIELDS = (
    "workflow_path", "workflow_id", "api_registration_state", "manual_dispatch",
    "workflow_mutates_or_pins_branch", "api_visible_run_count", "latest_run_id",
    "latest_event", "latest_status", "latest_conclusion", "latest_created_at",
    "latest_run_url", "latest_head_sha", "latest_three_runs_json",
    "classification", "owner_delete_approval", "deletion_executed",
)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def request_json(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": "Bearer " + token,
        "User-Agent": "phase2-w4-audit-only",
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"GitHub Actions history API status {e.code}: {url.split('?')[0]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError("GitHub Actions history API not reachable") from e
    raise AssertionError("unreachable")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--emit-csv-chunks", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("No authenticated API token; abort rather than claim run-history verification")
    assert git("rev-parse", BASE) == BASE
    assert not git("diff", "--diff-filter=D", "--name-only", BASE, "HEAD")
    tracked = sorted(p for p in git("ls-files").splitlines()
                     if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")))
    assert len(tracked) == 39, ("Workflow scope changed; review before rerunning", len(tracked))
    url_root = "https://api.github.com/repos/" + OWNER_REPO + "/actions/workflows"
    listing = request_json(url_root + "?per_page=100", token)
    all_api = listing.get("workflows", [])
    assert len(all_api) < 100 and listing.get("total_count", 0) < 100, (
        "Workflow API pagination not yet supported; do not claim complete scan"
    )
    path_map = {}
    for w in all_api:
        path_map.setdefault(w.get("path"), []).append(w)
    records = []
    for path in tracked:
        body = (ROOT / path).read_text(encoding="utf-8")
        candidates = path_map.get(path, [])
        active = [w for w in candidates if w.get("state") == "active"]
        workflow = (active or candidates or [None])[0]
        if workflow:
            wid = str(workflow["id"])
            details = request_json(url_root + "/" + wid + "/runs?per_page=3", token)
            recent = details.get("workflow_runs", [])
            visible = details.get("total_count")
            assert isinstance(visible, int)
            reg = workflow.get("state", "unknown")
        else:
            wid, recent, visible, reg = "", [], None, "not_registered_in_actions_api"
        samples = [{
            "id": run.get("id"),
            "event": run.get("event"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "created_at": run.get("created_at"),
            "head_sha": run.get("head_sha"),
            "url": run.get("html_url"),
        } for run in recent]
        newest = samples[0] if samples else {}
        import re
        mutates = (
            bool(re.search(r"(?m)^\s*contents:\s*write\s*$", body))
            or "git push" in body
            or bool(re.search(r"(?:refs/heads/research/|ref:\s*(?:exp/|research/|exp-|exp0))", body))
        )
        is_exp = bool(re.search(r"(?i)(?:exp0[0-9]|lpf-exp0|rft003|lpf-target|lpf-p4-a)", path))
        if mutates:
            decision = "retain_mutating_or_branch_pinned_workflow"
        elif is_exp:
            decision = "retain_until_replay_and_run_history_review"
        else:
            decision = "retain_shared_ci_or_governance"
        records.append({
            "workflow_path": path, "workflow_id": wid, "api_registration_state": reg,
            "manual_dispatch": str(bool(re.search(r"(?m)^\s*workflow_dispatch\s*:", body))).lower(),
            "workflow_mutates_or_pins_branch": str(mutates).lower(),
            "api_visible_run_count": "" if visible is None else visible,
            "latest_run_id": newest.get("id", ""),
            "latest_event": newest.get("event", ""),
            "latest_status": newest.get("status", ""),
            "latest_conclusion": newest.get("conclusion", ""),
            "latest_created_at": newest.get("created_at", ""),
            "latest_run_url": newest.get("url", ""),
            "latest_head_sha": newest.get("head_sha", ""),
            "latest_three_runs_json": json.dumps(samples, separators=(",", ":")),
            "classification": decision,
            "owner_delete_approval": "not_granted",
            "deletion_executed": "false",
        })

    summary = {
        "scope": "main-tracked 39 workflows, GitHub Actions REST current first page",
        "source_main": BASE,
        "checkout": git("rev-parse", "HEAD"),
        "observed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workflow_paths_reviewed": len(records),
        "api_registered": sum(bool(x["workflow_id"]) for x in records),
        "api_not_registered": [x["workflow_path"] for x in records if not x["workflow_id"]],
        "api_visible_runs_total_sum": sum(int(x["api_visible_run_count"]) for x in records
                                          if x["api_visible_run_count"] != ""),
        "with_at_least_one_api_visible_run": sum(
            isinstance(x["api_visible_run_count"], int) and x["api_visible_run_count"] > 0
            for x in records),
        "manually_dispatchable": sum(x["manual_dispatch"] == "true" for x in records),
        "mutating_or_pinned_branch_workflows": [
            x["workflow_path"] for x in records if x["workflow_mutates_or_pins_branch"] == "true"
        ],
        "exp042_workflows": [{
            "path": x["workflow_path"], "api_visible_run_count": x["api_visible_run_count"],
            "latest_run_id": x["latest_run_id"], "latest_conclusion": x["latest_conclusion"],
            "latest_created_at": x["latest_created_at"]
        } for x in records if "exp042" in x["workflow_path"]],
        "classification_counts": dict(sorted(Counter(x["classification"] for x in records).items())),
        "owner_workflow_deletion_approvals": 0,
        "workflows_deleted": 0,
        "limitations": [
            "Current Actions REST runs endpoints are not an eternal immutable history.",
            "Only three most recent API-visible runs per registered workflow sampled.",
            "No run log or uploaded artifact contents verified; user/branch replay still pending.",
            "Zero API-visible runs or no registration is not evidence of no historic use.",
        ]
    }
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(records)
    content = buf.getvalue()
    (out / "w4_actions_run_history.csv").write_text(content, encoding="utf-8")
    (out / "w4_actions_run_history_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("W4_RUN_HISTORY_SUMMARY=" + json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    if args.emit_csv_chunks:
        for i in range(0, len(content), 5000):
            print("W4_RUN_HISTORY_CHUNK=" + json.dumps({
                "seq": i // 5000, "text": content[i:i + 5000]
            }, ensure_ascii=False, separators=(",", ":")))
    print("W4_RUN_HISTORY_PASS: authenticated Actions API query, no workflow removals")


if __name__ == "__main__":
    main()
