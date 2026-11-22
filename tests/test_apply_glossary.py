"""新版刪除舊 key 後，術語正規化仍須確實寫回。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import apply_glossary as glossary


class ApplyGlossaryTests(unittest.TestCase):
    def test_removed_override_does_not_prevent_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            en = Path(directory) / 'en.json'
            pack = Path(directory) / 'zh.json'
            en.write_text(json.dumps({'label': 'Agent'}))
            pack.write_text(json.dumps({'label': 'agent'}))
            with patch.object(glossary, 'PACK', pack), \
                 patch.object(glossary, 'OVERRIDES', {'deleted': '已刪除'}), \
                 patch('sys.argv', ['apply_glossary.py', str(en)]), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                glossary.main()
            self.assertEqual(json.loads(pack.read_text()), {'label': 'Agent'})
