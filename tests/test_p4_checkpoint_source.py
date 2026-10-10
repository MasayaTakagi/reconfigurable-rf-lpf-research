import ast,unittest
from pathlib import Path
class CheckpointSourceTests(unittest.TestCase):
    def test_script_parses_and_has_atomic_checkpoint(self):
        script=Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'/'p4_batch.py'
        source=script.read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn("temp.replace(checkpoint)",source)
        self.assertIn("save_partial()",source)
        self.assertIn("status='partial_checkpoint'",source)
