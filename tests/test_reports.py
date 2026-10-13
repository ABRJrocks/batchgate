import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from batchgate.reports import ReportError, atomic_write, check_destinations, json_report, junit_report, write_reports
from batchgate.result import BatchResult, DatasetResult, ReconciliationResult


class ReportTests(unittest.TestCase):
    def result(self):
        dataset = DatasetResult('users', complete=True, rows=10, invalid_rows=1)
        dataset.add('type', row=2, line=3, field='id')
        return BatchResult('A < B & C', [dataset], [ReconciliationResult('totals', False, 'sum_mismatch')])

    def test_json_roundtrip(self):
        report = json.loads(json_report(self.result()))
        self.assertFalse(report['passed'])
        self.assertEqual(report['datasets'][0]['issues'][0]['row'], 2)
        self.assertNotIn('values', report['datasets'][0]['issues'][0])

    def test_junit_counts_and_escaping(self):
        root = ET.fromstring(junit_report(self.result()))
        self.assertEqual(root.get('name'), 'A < B & C')
        self.assertEqual(root.get('tests'), '2')
        self.assertEqual(root.get('failures'), '2')
        self.assertEqual(len(root.findall('testcase/failure')), 2)

    def test_reports_written(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            write_reports(self.result(), json_path=path/'a.json', junit_path=path/'b.xml')
            json.loads((path/'a.json').read_text())
            ET.fromstring((path/'b.xml').read_text())

    def test_atomic_failure_keeps_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'report.json'
            path.write_text('old')
            with patch('batchgate.reports.os.replace', side_effect=OSError('sensitive path')):
                with self.assertRaises(ReportError):
                    atomic_write(path, 'new')
            self.assertEqual(path.read_text(), 'old')
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_destinations_cannot_overwrite_inputs(self):
        with self.assertRaises(ReportError):
            check_destinations(['data.csv'], ['data.csv'])
        with self.assertRaises(ReportError):
            check_destinations(['a.json', './a.json'])
