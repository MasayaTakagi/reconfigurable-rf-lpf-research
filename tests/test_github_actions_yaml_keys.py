"""Regression checks for duplicate inputs in GitHub Actions workflow YAML.

The CI runtime deliberately does not depend on PyYAML. Check the action `with:`
mappings directly so duplicate keys such as if-no-files-found cannot silently
reappear and invalidate a workflow before any job starts.
"""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
WITH_KEY = re.compile(r"^(?P<indent> *)with:\s*(?:#.*)?$")
MAPPING_KEY = re.compile(r"^(?P<indent> *)(?P<key>[A-Za-z0-9_-]+)\s*:")


class GitHubActionsWorkflowKeysTests(unittest.TestCase):
    def test_all_action_with_sections_have_unique_keys(self):
        workflows = sorted(WORKFLOWS.glob("*.yml"))
        self.assertTrue(workflows, "No GitHub Actions workflows discovered")

        for workflow in workflows:
            lines = workflow.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                with_section = WITH_KEY.match(line)
                if not with_section:
                    continue
                section_indent = len(with_section.group("indent"))
                key_indent = None
                seen = {}
                for following in range(index + 1, len(lines)):
                    raw = lines[following]
                    if not raw.strip() or raw.lstrip().startswith("#"):
                        continue
                    indent = len(raw) - len(raw.lstrip(" "))
                    if indent <= section_indent:
                        break
                    entry = MAPPING_KEY.match(raw)
                    if entry is None:
                        continue
                    if key_indent is None:
                        key_indent = indent
                    if indent != key_indent:
                        continue
                    key = entry.group("key")
                    with self.subTest(workflow=workflow.name, line=following + 1, key=key):
                        self.assertNotIn(
                            key,
                            seen,
                            f"Duplicate GitHub Actions with key {key!r} in "
                            f"{workflow.name}, lines {seen.get(key)} and {following + 1}",
                        )
                    seen[key] = following + 1


if __name__ == "__main__":
    unittest.main()
