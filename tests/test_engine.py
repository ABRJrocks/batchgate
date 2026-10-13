import tempfile
import unittest
from pathlib import Path
from batchgate.contract import validate_contract
from batchgate.engine import _scan
from test_contract import contract


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = validate_contract(contract())
        self.ds = self.config['datasets'][0]

    def scan(self, text):
        path = self.root / self.ds['path']
        path.write_text(text)
        return _scan(self.ds, path, self.config['limits'])

    def test_valid_batch(self):
        result = self.scan('id\n1\n2\n')
        self.assertTrue(result.passed)
        self.assertEqual(result.rows, 2)

    def test_field_errors_count_rows_once(self):
        self.ds['fields']['name'] = {'type': 'string', 'min_length': 3}
        result = self.scan('id,name\nbad,a\n1,good\n')
        self.assertEqual(result.invalid_rows, 1)
        self.assertEqual(result.issue_count, 2)
        self.assertEqual(result.issues[0].line, 2)

    def test_json_missing_extra_and_null(self):
        self.ds['format'] = 'jsonl'
        result = self.scan('{"id": null}\n{}\n{"id": 1, "secret-column": 2}\n')
        self.assertEqual(result.counts, {'null': 1, 'missing_field': 1, 'extra_field': 1})
        self.assertEqual(result.invalid_rows, 3)
        self.assertNotIn('secret-column', str(result.to_dict()))

    def test_row_comparison(self):
        self.ds['fields'] = {'start': {'type': 'date'}, 'end': {'type': 'date'}}
        self.ds['comparisons'] = [{'left': 'start', 'op': 'le', 'right': 'end'}]
        result = self.scan('start,end\n2026-02-02,2026-02-01\n2026-02-01,2026-02-01\n')
        self.assertEqual(result.counts['comparison'], 1)

    def test_fatal_parse_does_not_report_complete(self):
        result = self.scan('id\n1\n"oops\n')
        self.assertFalse(result.complete)
        self.assertFalse(result.passed)
        self.assertEqual(result.rows, 1)

    def test_invalid_rows_are_not_silently_skipped(self):
        result = self.scan('id\n\n1,2\nnot-an-id\n')
        self.assertEqual(result.rows, 3)
        self.assertEqual(result.invalid_rows, 3)
