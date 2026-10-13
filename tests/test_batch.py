import tempfile
import unittest
from pathlib import Path
from batchgate.contract import ContractError
from batchgate.engine import validate_batch
from test_contract import contract


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = contract()

    def run_batch(self, text):
        (self.root / 'users.csv').write_text(text)
        return validate_batch(self.config, self.root)

    def test_duplicate_primary_key(self):
        result = self.run_batch('id\n1\n2\n1\n')
        self.assertFalse(result.passed)
        self.assertEqual(result.datasets[0].counts['duplicate_key'], 1)
        self.assertEqual(result.datasets[0].invalid_rows, 1)
        self.assertEqual(result.datasets[0].issues[0].row, 3)

    def test_composite_unique_preserves_tuple_boundaries(self):
        ds = self.config['datasets'][0]
        ds['fields'] = {'a': {'type': 'string'}, 'b': {'type': 'string'}}
        ds.pop('primary_key')
        ds['unique'] = [['a', 'b']]
        result = self.run_batch('a,b\nab,c\na,bc\nab,c\n')
        self.assertEqual(result.datasets[0].counts['duplicate_key'], 1)

    def test_invalid_key_not_indexed(self):
        result = self.run_batch('id\nwrong\nwrong\n')
        self.assertEqual(result.datasets[0].counts, {'type': 2})

    def test_missing_file_is_failure(self):
        result = validate_batch(self.config, self.root)
        self.assertFalse(result.passed)
        self.assertFalse(result.datasets[0].complete)

    def test_input_is_not_changed(self):
        path = self.root / 'users.csv'
        original = b'id\r\n1\r\n'
        path.write_bytes(original)
        validate_batch(self.config, self.root)
        self.assertEqual(path.read_bytes(), original)

    def test_unsafe_path_is_configuration_failure(self):
        self.config['datasets'][0]['path'] = '../secret'
        with self.assertRaises(ContractError):
            validate_batch(self.config, self.root)
