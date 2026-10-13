import tempfile
import unittest
from pathlib import Path
from batchgate.engine import validate_batch


def finance_contract():
    return {'version': 1, 'datasets': [
        {'name': 'orders', 'path': 'orders.csv', 'format': 'csv', 'fields': {'amount': {'type': 'decimal'}}, 'row_count': {'min': 1}},
        {'name': 'payments', 'path': 'payments.jsonl', 'format': 'jsonl', 'fields': {'amount': {'type': 'decimal'}}}],
        'reconciliations': [{'name': 'settlement', 'left': {'dataset': 'orders', 'field': 'amount'},
                            'right': {'dataset': 'payments', 'field': 'amount'}, 'tolerance': '0'}]}


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = finance_contract()

    def check(self, orders='amount\n0.1\n0.2\n', payments='{"amount":0.3}\n'):
        (self.root / 'orders.csv').write_text(orders)
        (self.root / 'payments.jsonl').write_text(payments)
        return validate_batch(self.config, self.root)

    def test_exact_decimal_match(self):
        self.assertTrue(self.check().passed)

    def test_sum_mismatch_blocks_batch(self):
        result = self.check(payments='{"amount":0.31}\n')
        self.assertFalse(result.passed)
        self.assertEqual(result.reconciliations[0].code, 'sum_mismatch')
        self.assertNotIn('0.31', str(result.to_dict()))

    def test_explicit_tolerance(self):
        self.config['reconciliations'][0]['tolerance'] = '0.01'
        self.assertTrue(self.check(payments='{"amount":0.31}\n').passed)
        self.assertFalse(self.check(payments='{"amount":0.310001}\n').passed)

    def test_partial_or_invalid_data_is_unavailable(self):
        result = self.check(orders='amount\nbad-secret-value\n')
        self.assertEqual(result.reconciliations[0].code, 'sum_unavailable')
        self.assertFalse(result.reconciliations[0].passed)

    def test_empty_volume_guard(self):
        result = self.check(orders='amount\n', payments='')
        self.assertEqual(result.datasets[0].counts['row_count'], 1)
        self.assertFalse(result.passed)

    def test_large_precision_not_rounded(self):
        value = '9' * 100 + '.01'
        result = self.check(orders='amount\n' + value + '\n0.01\n', payments='{"amount":"' + '9' * 100 + '.02"}\n')
        self.assertTrue(result.passed)

    def test_max_volume(self):
        self.config['datasets'][0]['row_count']['max'] = 1
        self.assertFalse(self.check().passed)
