"""Portable smoke tests for the public review package (not circuit proof)."""
import importlib.util
import unittest
from pathlib import Path

S=Path(__file__).resolve().parents[1]/'scripts/audit_results.py'
spec=importlib.util.spec_from_file_location('lpf_audit',S)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class EvidenceTests(unittest.TestCase):
    def test_all_manifest_and_band_metadata(self):
        self.assertEqual(audit.audit(),[])

    def test_six_cases(self):
        self.assertEqual(len(audit.CASES),6)

if __name__=='__main__':unittest.main()
