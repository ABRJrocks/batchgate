import copy
import unittest
from batchgate.contract import ContractError, validate_contract
from test_contract import contract


class ContractHardeningTests(unittest.TestCase):
    def test_malformed_shapes_always_raise_contract_error(self):
        values = [None, [], True, {'version': 1, 'datasets': [None]}]
        for field, value in [('format', []), ('unique', {}), ('unique', [[]]), ('primary_key', []),
                             ('foreign_keys', 'bad'), ('fields', {'id': {'type': []}}),
                             ('row_count', []), ('comparisons', [{'left': [], 'op': [], 'right': 'id'}])]:
            c = contract()
            c['datasets'][0][field] = value
            values.append(c)
        for c in values:
            with self.subTest(c=c), self.assertRaises(ContractError):
                validate_contract(c)

    def test_duplicate_key_definition(self):
        c = contract()
        c['datasets'][0]['unique'] = [['id']]
        with self.assertRaises(ContractError):
            validate_contract(c)

    def test_impossible_bounds_and_patterns(self):
        for rule in [{'type': 'integer', 'min': 2, 'max': 1}, {'type': 'string', 'pattern': '['},
                     {'type': 'string', 'min_length': 5, 'max_length': 2}, {'type': 'integer', 'min': 'NaN'}]:
            c = contract()
            c['datasets'][0]['fields']['id'] = rule
            with self.subTest(rule=rule), self.assertRaises(ContractError):
                validate_contract(c)

    def test_input_dictionary_is_not_mutated(self):
        c = contract()
        before = copy.deepcopy(c)
        validate_contract(c)
        self.assertEqual(c, before)
