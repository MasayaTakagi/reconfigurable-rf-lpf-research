#!/usr/bin/env python3
"""Generate & restore-test a FULL Git bundle of the current remote branch heads.

Read-only on the actual remote; never deletes a remote ref. Requires full Git
history locally (no shallow objects) and includes main + active draft branches.
Artifacts expire: their production is NOT durable offsite backup.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, stderr=subprocess.PIPE).decode("utf-8").strip()


def remote_heads(root):
    lines = git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/remotes/origin").splitlines()
    refs = {}
    for line in lines:
        name, sha = line.rsplit(" ", 1)
        if name == "refs/remotes/origin/HEAD":
            continue
        if not name.startswith("refs/remotes/origin/") or not SHA.fullmatch(sha):
            raise ValueError("Malformed remote branch")
        refs[name] = sha
    if "refs/remotes/origin/main" not in refs:
        raise ValueError("main tracking ref absent")
    return dict(sorted(refs.items()))


def write_bundle(root, output):
    root, output = Path(root), Path(output)
    if git(root, "rev-parse", "--is-shallow-repository") != "false":
        raise RuntimeError("Shallow repository: fetch complete history before creating backup")
    refs = remote_heads(root)
    if len(refs) < 8:
        raise ValueError("Expected at least main, 6 merged branches and active PR branch")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Explicit branch refs, no ephemeral PR refs or unrelated objects.
    subprocess.run(["git", "bundle", "create", str(output.resolve()), *refs],
                   cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    verified = subprocess.run(["git", "bundle", "verify", str(output.resolve())],
                              cwd=root, check=True, text=True, capture_output=True)
    if "complete history" not in verified.stderr + verified.stdout:
        raise ValueError("The bundle does not assert complete history")
    with tempfile.TemporaryDirectory() as tmp:
        restore = Path(tmp) / "restored"
        subprocess.run(["git", "init", "-q", str(restore)], check=True)
        subprocess.run(["git", "fetch", str(output.resolve()),
                        "+refs/remotes/origin/*:refs/heads/*"],
                       cwd=restore, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for name, sha in refs.items():
            suffix = name.removeprefix("refs/remotes/origin/")
            actual = git(restore, "rev-parse", "refs/heads/" + suffix)
            if actual != sha:
                raise ValueError("Bundle restore ref differs: " + name)
        subprocess.run(["git", "fsck", "--full", "--no-reflogs"],
                       cwd=restore, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with output.open("rb") as fd:
        digest = hashlib.file_digest(fd, "sha256").hexdigest()
    return {
        "schema_version": 1,
        "kind": "phase2_complete_git_history_bundle",
        "source": "fetched refs/remotes/origin/*; no archived ChatGPT attachments",
        "bundle_file": output.name,
        "sha256": digest,
        "bytes": output.stat().st_size,
        "branch_ref_count": len(refs),
        "branch_tip_sha": refs,
        "verification": {
            "git_bundle_verify_complete_history": True,
            "git_fetch_to_fresh_repository": True,
            "restored_all_branch_tips_exactly": True,
            "restored_git_fsck_full": True,
        },
        "remote_ref_changes": 0,
        "remote_ref_deletions": 0,
        "artifact_retention_is_finite": True,
        "durable_offsite_copy_verified": False,
        "qualification": "CI artifact is temporary. Download and securely store the bundle plus manifest; retest SHA-256 and git bundle verify before approving branch deletions.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    args = ap.parse_args()
    result = write_bundle(Path.cwd(), args.output)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS full branch Git bundle restore:", json.dumps({
        "sha256": result["sha256"], "bytes": result["bytes"],
        "branch_refs": result["branch_ref_count"],
        "durable": result["durable_offsite_copy_verified"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
