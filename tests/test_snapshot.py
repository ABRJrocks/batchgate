import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from batchgate.engine import _scan, validate_batch
from batchgate.snapshot import FileSnapshot
from test_contract import contract


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'users.csv'
        self.path.write_text('id\n1\n')

    def test_stable_file(self):
        snapshot = FileSnapshot.capture(self.path)
        self.assertTrue(snapshot.unchanged(self.root, 'users.csv'))

    def test_append_and_removal(self):
        snapshot = FileSnapshot.capture(self.path)
        self.path.write_text('id\n1\n2\n')
        self.assertFalse(snapshot.unchanged(self.root, 'users.csv'))
        self.path.unlink()
        self.assertFalse(snapshot.unchanged(self.root, 'users.csv'))

    def test_replacement_same_size(self):
        snapshot = FileSnapshot.capture(self.path)
        replacement = self.root / 'replacement'
        replacement.write_text('id\n2\n')
        replacement.replace(self.path)
        self.assertFalse(snapshot.unchanged(self.root, 'users.csv'))

    def test_engine_blocks_mutation(self):
        def scan_and_change(*args, **kwargs):
            result = _scan(*args, **kwargs)
            self.path.write_text('id\n1\n2\n')
            return result
        with patch('batchgate.engine._scan', side_effect=scan_and_change):
            result = validate_batch(contract(), self.root)
        self.assertFalse(result.passed)
        self.assertFalse(result.datasets[0].complete)
        self.assertEqual(result.datasets[0].counts['file_changed'], 1)
