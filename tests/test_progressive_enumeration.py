import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'))
from enumerate_graphs import enumerate_graphs
class ProgressiveEnumerationTests(unittest.TestCase):
    def test_budget_marks_incomplete(self):
        counts,_=enumerate_graphs(6,6,max_raw=30)
        self.assertTrue(counts['truncated'])
        self.assertEqual(counts['raw'],30)
    def test_complete_small(self):
        counts,_=enumerate_graphs(3,2)
        self.assertFalse(counts['truncated'])
    def test_internal_node_expansion(self):
        counts,_=enumerate_graphs(6,6,max_raw=100)
        self.assertLessEqual(counts['raw'],100)
