import unittest
from batchgate.html_report import html_report
from batchgate.result import BatchResult, DatasetResult, ReconciliationResult


class HtmlTests(unittest.TestCase):
    def test_title_is_escaped(self):
        report = html_report(BatchResult('<script>alert(1)</script>', [DatasetResult('users', complete=True)]))
        self.assertNotIn('<script>', report)
        self.assertIn('&lt;script&gt;', report)

    def test_no_remote_assets_or_scripts(self):
        report = html_report(BatchResult('batch', [DatasetResult('users', complete=True)]))
        self.assertNotIn('src=', report)
        self.assertNotIn('<script', report)
        self.assertIn("default-src 'none'", report)
        self.assertIn('scope="col"', report)
        self.assertIn('Batch accepted', report)

    def test_complete_failure_diagnostics(self):
        ds = DatasetResult('orders', complete=True, rows=100, invalid_rows=1, sample_limit=1)
        ds.add('foreign_key', row=4, line=5, field='user_id')
        ds.add('type', row=4, line=5, field='amount')
        report = html_report(BatchResult('batch', [ds], [ReconciliationResult('totals', False, 'sum_unavailable')]))
        self.assertIn('Batch rejected', report)
        self.assertIn('1 additional issues omitted', report)
        self.assertIn('sum_unavailable', report)
        self.assertIn('foreign_key', report)
