import ast,unittest
from pathlib import Path
class CheckpointSourceTests(unittest.TestCase):
    def test_script_parses_and_exposes_shard_resume_controls(self):
        script=Path(__file__).resolve().parents[1]/'experiments'/'matching_limit'/'p4_batch.py'
        source=script.read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn("'--checkpoint'",source)
        self.assertIn("'--shard-count'",source)
        self.assertIn("'--shard-index'",source)
        self.assertIn("'--resume'",source)
        self.assertIn("atomic_write_json(checkpoint,payload)",source)
        self.assertIn("save_checkpoint('interrupted')",source)
