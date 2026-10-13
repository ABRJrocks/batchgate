"""Explicit scalar parsing with exact decimal values."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation


class ValueIssue(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def parse_value(value, kind, *, csv=False):
    try:
        if kind == "string":
            if not isinstance(value, str):
                raise ValueError()
            return value
        if kind == "boolean":
            if csv and value in {"true", "false"}:
                return value == "true"
            if not csv and type(value) is bool:
                return value
            raise ValueError()
        if kind == "integer":
            if csv:
                if not isinstance(value, str) or len(value) > 1000 or not re.fullmatch(r"-?(0|[1-9][0-9]*)", value):
                    raise ValueError()
                return int(value)
            if type(value) is int and len(str(value)) <= 1000:
                return value
            raise ValueError()
        if kind == "decimal":
            if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
                raise ValueError()
            text = str(value)
            if len(text) > 1000 or not re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?", text):
                raise ValueError()
            result = Decimal(text)
            if not result.is_finite() or abs(result.adjusted()) > 1000 or abs(result.as_tuple().exponent) > 1000:
                raise ValueError()
            return result
        if kind == "date":
            if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError()
            return date.fromisoformat(value)
        if kind == "datetime":
            if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})", value):
                raise ValueError()
            if not value.endswith("Z"):
                hour, minute = value[-5:].split(":")
                if int(hour) > 23 or int(minute) > 59:
                    raise ValueError()
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        raise ValueError()
    except (ValueError, TypeError, OverflowError, InvalidOperation):
        raise ValueIssue("type") from None


def canonical(value):
    if isinstance(value, Decimal):
        text = format(value, "f")
        text = text.rstrip("0").rstrip(".") if "." in text else text
        return "0" if value == 0 else text
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
