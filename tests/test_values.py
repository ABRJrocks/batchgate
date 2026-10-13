import unittest
from decimal import Decimal
from batchgate.values import ValueIssue, canonical, parse_value


class TypeTests(unittest.TestCase):
    def test_integer_csv_is_strict(self):
        self.assertEqual(parse_value("42", "integer", csv=True), 42)
        for value in ["01", "1.0", " 1", "+1", "1e2", "١", "9" * 1001]:
            with self.subTest(value=value[:10]), self.assertRaises(ValueIssue):
                parse_value(value, "integer", csv=True)

    def test_boolean_is_not_an_integer(self):
        with self.assertRaises(ValueIssue):
            parse_value(True, "integer")
        with self.assertRaises(ValueIssue):
            parse_value(1, "boolean")
        self.assertTrue(parse_value("true", "boolean", csv=True))

    def test_exact_decimals(self):
        self.assertEqual(parse_value("0.10", "decimal") + parse_value("0.20", "decimal"), Decimal("0.30"))
        self.assertEqual(canonical(Decimal("1.00")), canonical(Decimal("1")))
        self.assertEqual(canonical(Decimal("-0.0")), "0")

    def test_reject_nonfinite_and_unbounded_decimal(self):
        for value in [True, 0.1, "NaN", "Infinity", "1e9999", "0e-9999", " 1", "1."]:
            with self.subTest(value=value), self.assertRaises(ValueIssue):
                parse_value(value, "decimal")

    def test_calendar_dates(self):
        self.assertEqual(canonical(parse_value("2024-02-29", "date")), "2024-02-29")
        for value in ["2023-02-29", "2024-2-1", "20240101", "2024-01-01T00:00:00Z"]:
            with self.subTest(value=value), self.assertRaises(ValueIssue):
                parse_value(value, "date")

    def test_timezone_normalization(self):
        a = parse_value("2026-10-13T05:00:00+05:00", "datetime")
        b = parse_value("2026-10-13T00:00:00Z", "datetime")
        self.assertEqual(a, b)
        for value in ["2026-10-13T00:00:00", "2026-10-13 00:00:00Z", "2026-10-13T00:00:00+01:99"]:
            with self.subTest(value=value), self.assertRaises(ValueIssue):
                parse_value(value, "datetime")

    def test_string_preserves_identifiers(self):
        self.assertEqual(parse_value("001", "string"), "001")
        with self.assertRaises(ValueIssue):
            parse_value(1, "string")
