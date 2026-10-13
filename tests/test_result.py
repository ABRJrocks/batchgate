import unittest
from batchgate.result import BatchResult, DatasetResult, ReconciliationResult


class ResultTests(unittest.TestCase):
    def test_full_counts_with_bounded_samples(self):
        result = DatasetResult('users', sample_limit=2, complete=True)
        for row in range(1, 1001):
            result.add('type', row=row, field='id')
        self.assertEqual(result.issue_count, 1000)
        self.assertEqual(result.counts['type'], 1000)
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(result.to_dict()['issues_omitted'], 998)
        self.assertFalse(result.passed)

    def test_zero_samples_does_not_hide_failure(self):
        result = DatasetResult('users', sample_limit=0, complete=True)
        result.add('null')
        self.assertFalse(result.passed)
        self.assertEqual(result.issues, [])

    def test_incomplete_scan_never_passes(self):
        self.assertFalse(BatchResult('batch', [DatasetResult('users')]).passed)

    def test_reconciliation_blocks_batch(self):
        result = BatchResult('batch', [DatasetResult('users', complete=True)])
        self.assertTrue(result.passed)
        result.reconciliations.append(ReconciliationResult('totals', False, 'sum_mismatch'))
        self.assertFalse(result.passed)
