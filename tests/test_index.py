import unittest
from decimal import Decimal
from pathlib import Path
from batchgate.index import key_index


class IndexTests(unittest.TestCase):
    def test_duplicate_composite_key(self):
        with key_index() as index:
            self.assertIsNone(index.add_key('users', 0, ['ab', 'c'], 1))
            self.assertIsNone(index.add_key('users', 0, ['a', 'bc'], 2))
            self.assertEqual(index.add_key('users', 0, ['ab', 'c'], 3), 1)

    def test_normalized_decimal_keys(self):
        with key_index() as index:
            index.add_key('users', 0, [Decimal('1.00')], 1)
            self.assertEqual(index.add_key('users', 0, [Decimal('1')], 2), 1)

    def test_per_run_hashes(self):
        with key_index() as one, key_index() as two:
            self.assertNotEqual(one.digest(['secret']), two.digest(['secret']))

    def test_missing_reference_query(self):
        with key_index() as index:
            index.add_key('users', 0, [1], 1)
            index.add_reference('orders', 0, [1], 1, 2)
            index.add_reference('orders', 0, [2], 2, 3)
            self.assertEqual(list(index.missing_references('orders', 0, 'users', 0)), [(2, 3)])

    def test_bad_rows_count_once(self):
        with key_index() as index:
            index.add_row('users', 1, 2, False)
            index.mark_bad('users', 1)
            index.mark_bad('users', 1)
            self.assertEqual(index.invalid_rows('users'), 1)

    def test_cleanup_and_no_plaintext_keys(self):
        with key_index() as index:
            filename = Path(index.db.execute('PRAGMA database_list').fetchone()[2])
            index.add_key('users', 0, ['highly-secret-value'], 1)
            index.db.commit()
            self.assertNotIn(b'highly-secret-value', filename.read_bytes())
        self.assertFalse(filename.parent.exists())
