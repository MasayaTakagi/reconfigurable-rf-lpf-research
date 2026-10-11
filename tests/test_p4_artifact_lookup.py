import json
import sys
import unittest
from pathlib import Path
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_p4_a_artifact import find_artifact


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class ArtifactLookupTests(unittest.TestCase):
    def lookup(self, items):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse({"total_count": len(items), "artifacts": items})

        result = find_artifact(
            "1234", "lpf-p4-a-shard-0", "owner/repository", "token", opener=opener
        )
        self.assertEqual(requests[0][0].get_header("Authorization"), "Bearer token")
        return result

    def test_existing_artifact_is_restorable(self):
        result = self.lookup([{"id": 77, "name": "lpf-p4-a-shard-0", "expired": False}])
        self.assertTrue(result["found"])
        self.assertEqual(result["artifact_id"], 77)

    def test_missing_and_expired_artifacts_are_explicit(self):
        missing = self.lookup([])
        expired = self.lookup([{
            "id": 77, "name": "lpf-p4-a-shard-0", "expired": True,
        }])
        self.assertEqual(missing["reason"], "artifact_missing")
        self.assertEqual(expired["reason"], "artifact_expired")
        self.assertFalse(missing["found"])
        self.assertFalse(expired["found"])

    def test_bad_run_id_is_rejected_before_network_access(self):
        with self.assertRaisesRegex(ValueError, "run ID"):
            find_artifact("../bad", "artifact", "owner/repository", "token")

    def test_artifact_api_error_is_not_downgraded_to_missing(self):
        def failing_opener(_request, timeout):
            raise URLError("permission denied")

        with self.assertRaisesRegex(RuntimeError, "Unable to inspect"):
            find_artifact(
                "1234", "artifact", "owner/repository", "token", opener=failing_opener
            )


if __name__ == "__main__":
    unittest.main()
