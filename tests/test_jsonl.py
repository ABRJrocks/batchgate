import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from batchgate.contract import validate_contract
from batchgate.readers import InputError, read_jsonl
from test_contract import contract


class JsonlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'users.jsonl'
        c = validate_contract(contract())
        self.ds, self.limits = c['datasets'][0], c['limits']

    def read(self, text):
        self.path.write_text(text, encoding='utf-8')
        return list(read_jsonl(self.path, self.ds, self.limits))

    def test_exact_numbers_and_unicode(self):
        rows = self.read('{"id": 1, "amount": 0.1, "label": "café"}\n{"id": 2}')
        self.assertEqual(rows[0].data['amount'], Decimal('0.1'))
        self.assertEqual(rows[0].data['label'], 'café')
        self.assertEqual(rows[1].row, 2)

    def test_bad_rows_are_not_skipped(self):
        rows = self.read('{"id":1}\n\n[]\n{"id":1,"id":2}\n{"id":NaN}\n{bad}\n')
        self.assertEqual(len(rows), 6)
        self.assertEqual([r.error for r in rows], [None] + ['json_syntax'] * 5)

    def test_bom_is_rejected(self):
        self.assertEqual(self.read('\ufeff{"id":1}\n')[0].error, 'json_syntax')

    def test_invalid_utf8(self):
        self.path.write_bytes(b'{"id": "\xff"}\n')
        with self.assertRaises(InputError):
            list(read_jsonl(self.path, self.ds, self.limits))

    def test_row_limit(self):
        self.limits['max_rows'] = 1
        with self.assertRaises(InputError) as caught:
            self.read('{"id":1}\n{"id":2}\n')
        self.assertEqual(caught.exception.code, 'row_limit')
