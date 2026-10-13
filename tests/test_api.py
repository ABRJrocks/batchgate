import tempfile
import unittest
from pathlib import Path
from batchgate import BatchResult, ContractError, DatasetResult, load_contract, validate_batch, validate_contract, write_reports
from test_contract import contract


class ApiTests(unittest.TestCase):
    def test_public_api_and_pipeline_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'users.csv'
            data.write_bytes(b'id\n1\n1\n')
            result = validate_batch(validate_contract(contract()), root)
            self.assertIsInstance(result, BatchResult)
            self.assertIsInstance(result.datasets[0], DatasetResult)
            self.assertFalse(result.passed)
            report = root / 'result.json'
            write_reports(result, json_path=report, protected_paths=[data])
            self.assertTrue(report.is_file())
            consumed = []
            if result.passed:
                consumed.append('import')
            self.assertEqual(consumed, [])

    def test_public_contract_error(self):
        with self.assertRaises(ContractError):
            validate_contract({'version': 99})
