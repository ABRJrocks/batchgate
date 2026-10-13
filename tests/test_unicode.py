import unittest
from xml.etree import ElementTree as ET
from batchgate.contract import ContractError, validate_contract
from batchgate.reports import junit_report
from batchgate.result import BatchResult, DatasetResult
from batchgate.values import ValueIssue, parse_value
from test_contract import contract


class UnicodeTests(unittest.TestCase):
    def test_surrogate_cells_rejected(self):
        for text in ['\ud800', 'A\udfffB']:
            with self.assertRaises(ValueIssue):
                parse_value(text, 'string')

    def test_non_xml_report_metadata_rejected_before_scan(self):
        for title in ['\ud800', '\ufffe', '\uffff', 'A\x00B']:
            c = contract() | {'name': title}
            with self.subTest(title=repr(title)), self.assertRaises(ContractError):
                validate_contract(c)

    def test_multilingual_report_remains_valid_xml(self):
        title = 'Commerce café 商店 🛒'
        validate_contract(contract() | {'name': title})
        result = BatchResult(title, [DatasetResult('users', complete=True)])
        self.assertEqual(ET.fromstring(junit_report(result)).get('name'), title)
