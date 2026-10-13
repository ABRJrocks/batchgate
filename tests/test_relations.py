import copy
import tempfile
import unittest
from pathlib import Path
from batchgate.engine import validate_batch
from test_contract import contract


class RelationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = contract()
        ds = copy.deepcopy(self.config['datasets'][0])
        ds.update(name='orders', path='orders.csv', foreign_keys=[{'fields': ['user_id'], 'dataset': 'users', 'references': ['id']}])
        ds['fields']['user_id'] = {'type': 'integer', 'nullable': True}
        self.config['datasets'].insert(0, ds)

    def run_batch(self, users='id\n1\n', orders='id,user_id\n10,1\n'):
        (self.root / 'users.csv').write_text(users)
        (self.root / 'orders.csv').write_text(orders)
        return validate_batch(self.config, self.root)

    def test_references_independent_of_dataset_order(self):
        self.assertTrue(self.run_batch().passed)

    def test_orphan_and_multiple_failures_count_row_once(self):
        result = self.run_batch(orders='id,user_id\n10,2\n10,2\n')
        orders = result.datasets[0]
        self.assertEqual(orders.counts, {'duplicate_key': 1, 'foreign_key': 2})
        self.assertEqual(orders.invalid_rows, 2)

    def test_nullable_reference_and_invalid_type(self):
        result = self.run_batch(orders='id,user_id\n10,\n11,wrong\n')
        self.assertEqual(result.datasets[0].counts, {'type': 1})

    def test_unreadable_target_never_passes_reference(self):
        (self.root / 'orders.csv').write_text('id,user_id\n10,1\n')
        result = validate_batch(self.config, self.root)
        self.assertEqual(result.datasets[0].counts['reference_unavailable'], 1)
        self.assertFalse(result.passed)

    def test_composite_cross_format_keys(self):
        users = self.config['datasets'][1]
        users['fields']['tenant'] = {'type': 'string'}
        users['primary_key'] = ['tenant', 'id']
        orders = self.config['datasets'][0]
        orders['fields']['tenant'] = {'type': 'string'}
        orders['format'] = 'jsonl'
        orders['foreign_keys'][0].update(fields=['tenant', 'user_id'], references=['tenant', 'id'])
        result = self.run_batch(users='id,tenant\n1,A\n', orders='{"id":10,"tenant":"A","user_id":1}\n{"id":11,"tenant":"B","user_id":1}\n')
        self.assertEqual(result.datasets[0].counts['foreign_key'], 1)

    def test_self_reference(self):
        users = self.config['datasets'][1]
        self.config['datasets'] = [users]
        users['fields']['parent'] = {'type': 'integer', 'nullable': True}
        users['foreign_keys'] = [{'fields': ['parent'], 'dataset': 'users', 'references': ['id']}]
        result = self.run_batch(users='id,parent\n1,\n2,1\n')
        self.assertTrue(result.passed)
