import unittest
from batchgate.contract import ContractError, validate_contract
from batchgate.values import MISSING, ValueIssue, check_value
from test_contract import contract


class ConstraintTests(unittest.TestCase):
    def assertIssue(self, value, rule, code, **options):
        with self.assertRaises(ValueIssue) as caught:
            check_value(value, rule, **options)
        self.assertEqual(caught.exception.code, code)

    def test_missing_and_null_are_distinct(self):
        self.assertIssue(MISSING, {"type": "string", "nullable": True}, "missing_field")
        self.assertIsNone(check_value(MISSING, {"type": "string", "required": False}))
        self.assertIssue(None, {"type": "string", "required": False}, "null")
        self.assertIsNone(check_value(None, {"type": "integer", "nullable": True}))

    def test_csv_null_tokens_are_explicit(self):
        self.assertIssue("NULL", {"type": "string"}, "null", csv=True, null_values=["NULL"])
        self.assertEqual(check_value("NULL", {"type": "string"}), "NULL")
        self.assertEqual(check_value("", {"type": "string"}, csv=True, null_values=[]), "")

    def test_numeric_bounds(self):
        rule = {"type": "decimal", "min": "0.01", "max": "2.00"}
        self.assertIssue("0", rule, "minimum")
        self.assertIssue("2.01", rule, "maximum")
        self.assertEqual(str(check_value("2.00", rule)), "2.00")

    def test_string_length_and_full_pattern(self):
        rule = {"type": "string", "min_length": 2, "max_length": 4, "pattern": "[A-Z]+"}
        self.assertIssue("A", rule, "min_length")
        self.assertIssue("ABCDE", rule, "max_length")
        self.assertIssue("AB!", rule, "pattern")
        self.assertEqual(check_value("AB", rule), "AB")

    def test_typed_enum(self):
        self.assertEqual(check_value("1", {"type": "integer", "enum": [1, 2]}, csv=True), 1)
        self.assertIssue("3", {"type": "integer", "enum": [1, 2]}, "enum", csv=True)
        value = contract()
        value["datasets"][0]["fields"]["id"]["enum"] = [True]
        with self.assertRaises(ContractError):
            validate_contract(value)

    def test_error_has_no_cell_value(self):
        self.assertIssue("secret@example.com", {"type": "integer"}, "type")
