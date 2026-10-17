"""EXP number reservation is main-backed, monotone and race-resistant."""
import csv
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.experiment_id_registry import (
    PATH, as_csv, next_reservation, read_ledger, validate,
)

ROOT = Path(__file__).resolve().parents[1]


def allocate(rows, owner="tester", purpose="Phase 2 RF LPF", key="request-001",
             constraint_id="RF-F002"):
    return next_reservation(
        rows, owner=owner, purpose=purpose, request_id=key,
        constraint_id=constraint_id, reserved_at_utc="2026-10-15T08:00:00Z")


class ExperimentNumberLedgerTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / PATH).read_text(encoding="utf-8")
        self.rows = read_ledger(self.source)
        next_n = int(self.rows[-1]['experiment_id'].split('-')[1]) + 1
        self.next_id = f'EXP-{next_n:03d}'
        self.following_id = f'EXP-{next_n + 1:03d}'

    def test_baseline_retired_gaps_and_new_id(self):
        self.assertGreaterEqual(len(self.rows), 41)
        self.assertEqual("legacy_gap_retired", self.rows[17]["state"])
        self.assertEqual("legacy_gap_retired", self.rows[18]["state"])
        self.assertEqual("legacy_recorded", self.rows[40]["state"])
        updated, ident, created = allocate(self.rows)
        self.assertTrue(created)
        self.assertEqual(self.next_id, ident)
        self.assertEqual("reserved", updated[-1]["state"])
        self.assertEqual(len(self.rows) + 1, len(read_ledger(as_csv(updated))))

    def test_rerun_same_request_is_idempotent(self):
        rows, first, _ = allocate(self.rows)
        second_rows, second, created = allocate(rows)
        self.assertEqual(first, second)
        self.assertFalse(created)
        self.assertEqual(len(rows), len(second_rows))
        with self.assertRaises(ValueError):
            allocate(rows, purpose="Different purpose")

    def test_cancelled_number_never_reused(self):
        rows, first, _ = allocate(self.rows)
        rows[-1]["state"] = "cancelled"
        later, second, created = allocate(
            rows, owner="second", purpose="Another search", key="request-002")
        self.assertEqual(self.next_id, first)
        self.assertEqual(self.following_id, second)
        self.assertTrue(created)
        self.assertEqual("cancelled", later[-2]["state"])

    def test_historical_gap_cannot_be_reassigned(self):
        for new_state in ("reserved", "active", "legacy_recorded"):
            rows = read_ledger(self.source)
            rows[17]["state"] = new_state
            with self.assertRaises(ValueError):
                validate(rows)

    def test_duplicate_id_missing_row_and_order_rejected(self):
        rows = read_ledger(self.source)
        rows[-1]["experiment_id"] = "EXP-040"
        with self.assertRaises(ValueError):
            validate(rows)
        rows = read_ledger(self.source)
        rows.pop(17)
        with self.assertRaises(ValueError):
            validate(rows)

    def test_comma_quoted_purpose_serializes_cleanly(self):
        rows, ident, _ = allocate(self.rows, purpose="RF, multiple-band scan")
        self.assertEqual("RF, multiple-band scan",
                         read_ledger(as_csv(rows))[-1]["purpose"])

    def test_spreadsheet_formula_injection_and_duplicate_keys_fail(self):
        with self.assertRaises(ValueError):
            allocate(self.rows, purpose="=HYPERLINK(1)")
        with self.assertRaises(ValueError):
            allocate(self.rows, key="wrong key")
        rows, _, _ = allocate(self.rows)
        rows[-1]["request_id"] = "not-valid key"
        with self.assertRaises(ValueError):
            validate(rows)


class FastForwardPushRaceTests(unittest.TestCase):
    """Two stale workers start with EXP-041; only one EXP-042 push may land."""

    def git(self, root, *args, check=True):
        run = subprocess.run(["git", *args], cwd=root, capture_output=True,
                             text=True, check=False)
        if check and run.returncode:
            raise AssertionError(run.stderr[-600:])
        return run

    def test_one_push_wins_and_loser_gets_next_number(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            remote = root / "remote.git"
            self.git(root, "init", "--bare", str(remote))
            seed = root / "seed"
            self.git(root, "init", "-b", "main", str(seed))
            self.git(seed, "config", "user.name", "Fixture")
            self.git(seed, "config", "user.email", "fixture@example.invalid")
            p = seed / PATH
            p.parent.mkdir(parents=True)
            p.write_text((ROOT / PATH).read_text(encoding="utf-8"), encoding="utf-8")
            self.git(seed, "add", ".")
            self.git(seed, "commit", "-m", "Seed all existing experiment numbers")
            self.git(seed, "remote", "add", "origin", str(remote))
            self.git(seed, "push", "origin", "HEAD:refs/heads/main")
            self.git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
            workers = []
            for i in range(2):
                w = root / f"worker{i}"
                self.git(root, "clone", "-q", str(remote), str(w))
                self.git(w, "config", "user.name", f"Worker{i}")
                self.git(w, "config", "user.email", f"worker{i}@example.invalid")
                workers.append(w)
            for i, w in enumerate(workers):
                rows = read_ledger((w / PATH).read_text())
                updated, exp_id, created = allocate(
                    rows, owner=f"worker{i}", key=f"request-{i:03d}")
                self.assertEqual("EXP-042", exp_id)
                self.assertTrue(created)
                (w / PATH).write_text(as_csv(updated))
                self.git(w, "add", PATH)
                self.git(w, "commit", "-m", "Reserve EXP-042")
            self.git(workers[0], "push", "origin", "HEAD:refs/heads/main")
            blocked = self.git(
                workers[1], "push", "origin", "HEAD:refs/heads/main",
                check=False)
            self.assertNotEqual(0, blocked.returncode)
            self.git(workers[1], "fetch", "origin", "main")
            self.git(workers[1], "reset", "--hard", "origin/main")
            rows = read_ledger((workers[1] / PATH).read_text())
            updated, ident, created = allocate(
                rows, owner="worker1", key="request-001")
            self.assertTrue(created)
            self.assertEqual("EXP-043", ident)
            (workers[1] / PATH).write_text(as_csv(updated))
            self.git(workers[1], "add", PATH)
            self.git(workers[1], "commit", "-m", "Reserve EXP-043 after conflict")
            self.git(workers[1], "push", "origin", "HEAD:refs/heads/main")
            final = self.git(workers[1], "show", "HEAD:" + PATH).stdout
            keys = [r["request_id"] for r in read_ledger(final)]
            self.assertEqual(1, keys.count("request-000"))
            self.assertEqual(1, keys.count("request-001"))


if __name__ == "__main__":
    unittest.main()
