import tempfile
import unittest
from pathlib import Path
from batchgate.contract import ContractError, validate_contract
from batchgate.readers import InputError, read_csv, resolve_input
from test_contract import contract


class CsvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "users.csv"
        c = validate_contract(contract())
        self.ds, self.limits = c["datasets"][0], c["limits"]

    def read(self, text):
        self.path.write_text(text, encoding="utf-8", newline="")
        return list(read_csv(self.path, self.ds, self.limits))

    def test_bom_and_crlf(self):
        rows = self.read('\ufeffid\r\n1\r\n2\r\n')
        self.assertEqual([x.data["id"] for x in rows], ["1", "2"])

    def test_multiline_quoted_cell(self):
        self.ds["fields"]["id"]["type"] = "string"
        rows = self.read('id\n"hello\nworld"\n')
        self.assertEqual(rows[0].data["id"], "hello\nworld")
        self.assertEqual((rows[0].row, rows[0].line), (1, 3))

    def test_headers_fail_closed(self):
        for text, code in [('id,id\n1,1\n', 'invalid_header'), ('other\n1\n', 'missing_header'),
                           ('id,new\n1,2\n', 'extra_header'), ('', 'invalid_header')]:
            with self.subTest(code=code), self.assertRaises(InputError) as caught:
                self.read(text)
            self.assertEqual(caught.exception.code, code)

    def test_row_width_and_empty_record(self):
        rows = self.read('id\n1,2\n\n3\n')
        self.assertEqual([x.error for x in rows], ['row_width', 'row_width', None])

    def test_bad_quoting(self):
        with self.assertRaises(InputError) as caught:
            self.read('id\n"unfinished\n')
        self.assertEqual(caught.exception.code, 'csv_syntax')

    def test_limits(self):
        for changes, code in [({'max_rows': 1}, 'row_limit'), ({'max_bytes': 3}, 'byte_limit'),
                              ({'max_line_chars': 2}, 'line_limit')]:
            self.limits.update(changes)
            with self.subTest(code=code), self.assertRaises(InputError) as caught:
                self.read('id\n1\n2\n')
            self.assertEqual(caught.exception.code, code)
            self.limits = validate_contract(contract())["limits"]

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "secret.csv"
            target.write_text('id\n1\n')
            self.path.symlink_to(target)
            with self.assertRaises(ContractError):
                resolve_input(self.temp.name, 'users.csv')

    def test_nonregular_input(self):
        self.path.mkdir()
        with self.assertRaises(InputError):
            resolve_input(self.temp.name, 'users.csv')
