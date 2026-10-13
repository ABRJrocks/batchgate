import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from batchgate.cli import main
from test_contract import contract


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'contract.json'
        self.path.write_text(json.dumps(contract()))
        self.data = self.root / 'users.csv'
        self.data.write_text('id\n1\n')

    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_success_and_all_reports(self):
        paths = [self.root/'report.json', self.root/'report.xml', self.root/'report.html']
        code, out, err = self.invoke(['check', str(self.path), '--json-report', str(paths[0]), '--junit', str(paths[1]), '--html-report', str(paths[2])])
        self.assertEqual(code, 0)
        self.assertIn('ACCEPTED', out)
        self.assertEqual(err, '')
        self.assertTrue(all(p.is_file() for p in paths))

    def test_failure_exit_and_value_redaction(self):
        self.data.write_text('id\nsecret@example.com\n')
        code, out, err = self.invoke(['check', str(self.path)])
        self.assertEqual(code, 1)
        self.assertNotIn('secret@example.com', out + err)
        self.assertIn('type=1', out)

    def test_invalid_contract_exit(self):
        self.path.write_text('{broken secret}')
        code, out, err = self.invoke(['check', str(self.path)])
        self.assertEqual(code, 2)
        self.assertNotIn('secret', err)

    def test_lint_does_not_read_inputs(self):
        self.data.unlink()
        self.assertEqual(self.invoke(['lint', str(self.path)])[0], 0)

    def test_reports_cannot_overwrite_source_or_contract(self):
        for path in [self.path, self.data]:
            before = path.read_bytes()
            self.assertEqual(self.invoke(['check', str(self.path), '--json-report', str(path)])[0], 2)
            self.assertEqual(path.read_bytes(), before)

    def test_quiet(self):
        code, out, err = self.invoke(['check', str(self.path), '--quiet'])
        self.assertEqual((code, out, err), (0, '', ''))

    def test_interrupt_and_io_failure(self):
        with patch('batchgate.cli.validate_batch', side_effect=KeyboardInterrupt):
            self.assertEqual(self.invoke(['check', str(self.path)])[0], 130)
        with patch('batchgate.cli.validate_batch', side_effect=OSError('secret-path')):
            code, out, err = self.invoke(['check', str(self.path)])
            self.assertEqual(code, 2)
            self.assertNotIn('secret-path', err)
