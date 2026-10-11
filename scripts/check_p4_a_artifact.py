#!/usr/bin/env python3
"""Check whether a previous GitHub Actions run has a restorable shard artifact."""
import argparse
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def find_artifact(run_id, artifact_name, repository, token, opener=urlopen):
    if not re.fullmatch(r"[0-9]+", str(run_id)):
        raise ValueError("run ID must be a positive integer")
    if not re.fullmatch(r"[^/]+/[^/]+", repository):
        raise ValueError("repository must have owner/name form")
    if not token:
        raise ValueError("GITHUB_TOKEN is required to inspect a previous run")

    page = 1
    while True:
        query = urlencode({"per_page": 100, "page": page})
        url = (f"https://api.github.com/repos/{repository}/actions/runs/"
               f"{run_id}/artifacts?{query}")
        request = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with opener(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to inspect resume artifacts: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("GitHub returned a malformed artifacts response")
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            raise RuntimeError("GitHub returned a malformed artifacts response")
        match = next((item for item in artifacts
                      if isinstance(item, dict) and item.get("name") == artifact_name), None)
        if match is not None:
            if match.get("expired") is True:
                return {"found": False, "reason": "artifact_expired", "artifact_name": artifact_name}
            return {
                "found": True,
                "reason": "artifact_available",
                "artifact_name": artifact_name,
                "artifact_id": match.get("id"),
                "expires_at": match.get("expires_at"),
            }
        total_count = payload.get("total_count")
        if len(artifacts) < 100 or (isinstance(total_count, int) and page * 100 >= total_count):
            return {"found": False, "reason": "artifact_missing", "artifact_name": artifact_name}
        page += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--output", default=os.environ.get("GITHUB_OUTPUT"))
    args = parser.parse_args()
    try:
        result = find_artifact(
            args.run_id, args.artifact_name, args.repository,
            os.environ.get("GH_TOKEN"),
        )
    except (ValueError, RuntimeError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    if args.output:
        with open(args.output, "a", encoding="utf-8") as stream:
            stream.write(f"found={'true' if result['found'] else 'false'}\n")
            stream.write(f"reason={result['reason']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
