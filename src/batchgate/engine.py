"""Read-only batch validation."""
from __future__ import annotations

import operator

from .readers import InputError, read_records
from .result import DatasetResult
from .values import MISSING, ValueIssue, check_value

OPS = {"lt": operator.lt, "le": operator.le, "eq": operator.eq,
       "ge": operator.ge, "gt": operator.gt}


def _scan(dataset, path, limits, on_row=None):
    result = DatasetResult(dataset["name"], sample_limit=limits["max_issues"])
    try:
        for record in read_records(path, dataset, limits):
            result.rows += 1
            before = result.issue_count
            values = {}
            if record.error:
                result.add(record.error, row=record.row, line=record.line)
            else:
                if not dataset.get("allow_extra_fields", False) and set(record.data) - set(dataset["fields"]):
                    result.add("extra_field", row=record.row, line=record.line)
                for field, rule in dataset["fields"].items():
                    try:
                        values[field] = check_value(record.data.get(field, MISSING), rule,
                                                    csv=dataset["format"] == "csv",
                                                    null_values=dataset.get("null_values", [""]))
                    except ValueIssue as exc:
                        result.add(exc.code, row=record.row, line=record.line, field=field)
                for check in dataset.get("comparisons", []):
                    left, right = values.get(check["left"]), values.get(check["right"])
                    if left is not None and right is not None and not OPS[check["op"]](left, right):
                        result.add("comparison", row=record.row, line=record.line, field=check["left"])
            if on_row:
                on_row(record, values, result, result.issue_count > before)
            if result.issue_count > before:
                result.invalid_rows += 1
        result.complete = True
    except InputError as exc:
        result.add(exc.code, line=exc.line)
    return result
