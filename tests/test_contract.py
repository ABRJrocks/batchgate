import copy
import tempfile
import unittest
from pathlib import Path
from batchgate.contract import ContractError, load_contract, strict_json, validate_contract


def contract():
    return {"version": 1, "datasets": [{"name": "users", "path": "users.csv", "format": "csv",
            "fields": {"id": {"type": "integer"}}, "primary_key": ["id"]}]}


class ContractTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(validate_contract(contract())["limits"]["max_issues"], 200)

    def test_invalid_contracts(self):
        for change in [{"version": True}, {"version": 2}, {"unknown": 1}, {"datasets": []},
                       {"limits": {"max_rows": True}}, {"limits": {"max_issues": -1}}]:
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate_contract(contract() | change)

    def test_bad_paths(self):
        for path in ["../x.csv", "/x.csv", "a/../x.csv", "C:\\x", "./x", "a\x00b"]:
            value = contract()
            value["datasets"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(ContractError):
                validate_contract(value)

    def test_nullable_key_rejected(self):
        value = contract()
        value["datasets"][0]["fields"]["id"]["nullable"] = True
        with self.assertRaises(ContractError):
            validate_contract(value)

    def test_unknown_field_option(self):
        value = contract()
        value["datasets"][0]["fields"]["id"]["maximun"] = 9
        with self.assertRaises(ContractError):
            validate_contract(value)

    def test_foreign_key_types(self):
        value = contract()
        other = copy.deepcopy(value["datasets"][0])
        other.update(name="orders", path="orders.csv", foreign_keys=[{"fields": ["id"], "dataset": "users", "references": ["id"]}])
        value["datasets"].append(other)
        validate_contract(value)
        other["fields"]["id"]["type"] = "string"
        with self.assertRaises(ContractError):
            validate_contract(value)

    def test_strict_json(self):
        for text in ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)

    def test_invalid_file_redacts_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text('{"secret-value":broken}')
            with self.assertRaises(ContractError) as caught:
                load_contract(path)
            self.assertNotIn("secret-value", str(caught.exception))
