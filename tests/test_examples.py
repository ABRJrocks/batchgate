import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from batchgate.cli import main
from batchgate.contract import load_contract
from batchgate.engine import validate_batch

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'examples' / 'commerce.contract.json'


class ExampleTests(unittest.TestCase):
    def test_good_batch_accepted(self):
        result = validate_batch(load_contract(CONTRACT), ROOT/'examples/good')
        self.assertTrue(result.passed)
        self.assertEqual(sum(d.rows for d in result.datasets), 6)
        self.assertTrue(result.reconciliations[0].passed)

    def test_bad_batch_catches_real_failures(self):
        result = validate_batch(load_contract(CONTRACT), ROOT/'examples/bad')
        self.assertFalse(result.passed)
        self.assertEqual([d.invalid_rows for d in result.datasets], [1, 2, 2])
        counts = {}
        for ds in result.datasets:
            for code, count in ds.counts.items():
                counts[code] = counts.get(code, 0) + count
        self.assertEqual(counts['duplicate_key'], 3)
        self.assertEqual(counts['foreign_key'], 2)
        self.assertEqual(counts['comparison'], 1)
        self.assertEqual(counts['minimum'], 1)
        self.assertEqual(counts['enum'], 1)
        self.assertEqual(counts['type'], 1)
        self.assertEqual(result.reconciliations[0].code, 'sum_unavailable')

    def test_cli_reports_do_not_contain_example_values(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory)/'report.json'
            code = main(['check', str(CONTRACT), '--data-dir', str(ROOT/'examples/bad'), '--json-report', str(path)])
            self.assertEqual(code, 1)
            content = path.read_text()
            for secret in ['Avery Chen', 'C999', 'P900', '29.99']:
                self.assertNotIn(secret, content)

    def test_module_entrypoint(self):
        import sys
        process = subprocess.run([sys.executable, '-m', 'batchgate', 'check', str(CONTRACT),
                                  '--data-dir', str(ROOT/'examples/good'), '--quiet'], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
