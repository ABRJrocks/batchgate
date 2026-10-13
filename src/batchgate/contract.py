"""Strict versioned contracts. Unknown keys fail before any data is read."""
from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path, PurePosixPath

from .values import ValueIssue, parse_value


class ContractError(ValueError):
    """An invalid contract or unsafe input path."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def strict_json(text):
    def reject(_):
        raise ValueError("non-finite JSON number")
    return json.loads(text, object_pairs_hook=unique_object,
                      parse_float=Decimal, parse_constant=reject)


def obj(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ContractError("invalid object fields")
    return value


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ContractError("integer outside permitted range")
    return value


def name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", value):
        raise ContractError("names must be identifiers of at most 64 characters")
    return value


def boolean(value):
    if type(value) is not bool:
        raise ContractError("expected boolean")
    return value


def key_fields(value, fields):
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ContractError("keys require one to eight fields")
    if any(not isinstance(x, str) or x not in fields for x in value) or len(set(value)) != len(value):
        raise ContractError("invalid key fields")
    return value


def safe_relative(value):
    if (not isinstance(value, str) or not value or len(value) > 512
            or "\\" in value or ":" in value or "\x00" in value):
        raise ContractError("invalid relative file path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in {"..", "."} for p in value.split("/")):
        raise ContractError("file paths must stay inside the data directory")
    return value


def validate_contract(raw):
    obj(raw, {"version", "name", "datasets", "reconciliations", "limits"}, {"version", "datasets"})
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ContractError("unsupported contract version")
    title = raw.get("name", "batch")
    if not isinstance(title, str) or not 1 <= len(title) <= 100 or any(ord(c) < 32 for c in title):
        raise ContractError("invalid contract name")
    datasets = raw["datasets"]
    if not isinstance(datasets, list) or not 1 <= len(datasets) <= 100:
        raise ContractError("one to 100 datasets are required")
    limits = dict(raw.get("limits", {})) if isinstance(raw.get("limits", {}), dict) else None
    obj(limits, {"max_rows", "max_bytes", "max_line_chars", "max_issues"})
    for k, default, low, high in [("max_rows", 1000000, 1, 5000000),
                                 ("max_bytes", 268435456, 1, 2147483648),
                                 ("max_line_chars", 1048576, 1, 1048576),
                                 ("max_issues", 200, 0, 10000)]:
        limits[k] = integer(limits.get(k, default), low, high)
    by_name = {}
    for ds in datasets:
        obj(ds, {"name", "path", "format", "fields", "primary_key", "unique", "foreign_keys",
                 "row_count", "comparisons", "delimiter", "null_values", "allow_extra_fields"},
            {"name", "path", "format", "fields"})
        name(ds["name"])
        if ds["name"] in by_name:
            raise ContractError("duplicate dataset name")
        by_name[ds["name"]] = ds
        safe_relative(ds["path"])
        if ds["format"] not in {"csv", "jsonl"}:
            raise ContractError("format must be csv or jsonl")
        delimiter = ds.get("delimiter", ",")
        if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in '\r\n"\x00':
            raise ContractError("invalid CSV delimiter")
        boolean(ds.get("allow_extra_fields", False))
        nulls = ds.get("null_values", [""])
        if not isinstance(nulls, list) or len(nulls) > 50 or any(not isinstance(x, str) for x in nulls):
            raise ContractError("null_values must be strings")
        fields = ds["fields"]
        if not isinstance(fields, dict) or not 1 <= len(fields) <= 200:
            raise ContractError("one to 200 fields are required")
        for field, rule in fields.items():
            name(field)
            obj(rule, {"type", "required", "nullable", "min", "max", "min_length", "max_length", "enum", "pattern"}, {"type"})
            if rule["type"] not in {"string", "integer", "decimal", "boolean", "date", "datetime"}:
                raise ContractError("unsupported field type")
            boolean(rule.get("required", True))
            boolean(rule.get("nullable", False))
            for k in ["min", "max"]:
                if k in rule:
                    if rule["type"] not in {"integer", "decimal"} or isinstance(rule[k], bool):
                        raise ContractError("numeric bounds need numeric types")
                    try:
                        bound = Decimal(str(rule[k]))
                        if not bound.is_finite() or len(str(rule[k])) > 1000 or abs(bound.adjusted()) > 1000:
                            raise ValueError()
                    except Exception:
                        raise ContractError("invalid numeric bound") from None
            if "min" in rule and "max" in rule and Decimal(str(rule["min"])) > Decimal(str(rule["max"])):
                raise ContractError("minimum exceeds maximum")
            for k in ["min_length", "max_length"]:
                if k in rule:
                    if rule["type"] != "string":
                        raise ContractError("length constraints require string type")
                    integer(rule[k], 0, 1048576)
            if rule.get("min_length", 0) > rule.get("max_length", 1048576):
                raise ContractError("minimum length exceeds maximum")
            if "pattern" in rule:
                if rule["type"] != "string" or not isinstance(rule["pattern"], str) or len(rule["pattern"]) > 1000:
                    raise ContractError("invalid string pattern")
                try:
                    re.compile(rule["pattern"])
                except re.error:
                    raise ContractError("invalid regular expression") from None
            if "enum" in rule and (not isinstance(rule["enum"], list) or not 1 <= len(rule["enum"]) <= 100):
                raise ContractError("enum requires one to 100 values")
        for rule in fields.values():
            for value in rule.get("enum", []):
                try:
                    parse_value(value, rule["type"])
                except ValueIssue:
                    raise ContractError("enum values must match the field type") from None
        for keys in [ds.get("primary_key", [])] + ds.get("unique", []):
            if keys:
                key_fields(keys, fields)
                if any(fields[k].get("nullable", False) or not fields[k].get("required", True) for k in keys):
                    raise ContractError("key fields must be required and nonnullable")
        for array in ["unique", "foreign_keys", "comparisons"]:
            if array in ds and (not isinstance(ds[array], list) or len(ds[array]) > 50):
                raise ContractError("invalid rule list")
        count = ds.get("row_count", {})
        obj(count, {"min", "max"})
        for k in count:
            integer(count[k], 0, limits["max_rows"])
        if count.get("min", 0) > count.get("max", limits["max_rows"]):
            raise ContractError("invalid row-count bounds")
        for comparison in ds.get("comparisons", []):
            obj(comparison, {"left", "op", "right"}, {"left", "op", "right"})
            key_fields([comparison["left"], comparison["right"]], fields)
            left, right = fields[comparison["left"]], fields[comparison["right"]]
            if left["type"] != right["type"] or left["type"] == "boolean" or comparison["op"] not in {"lt", "le", "eq", "ge", "gt"}:
                raise ContractError("invalid field comparison")
    for ds in datasets:
        for fk in ds.get("foreign_keys", []):
            obj(fk, {"fields", "dataset", "references"}, {"fields", "dataset", "references"})
            source = key_fields(fk["fields"], ds["fields"])
            if not isinstance(fk["dataset"], str) or fk["dataset"] not in by_name:
                raise ContractError("unknown referenced dataset")
            target = by_name[fk["dataset"]]
            dest = key_fields(fk["references"], target["fields"])
            if len(source) != len(dest) or dest not in [target.get("primary_key")] + target.get("unique", []):
                raise ContractError("references must match a declared unique key")
            if any(ds["fields"][s]["type"] != target["fields"][d]["type"] for s, d in zip(source, dest)):
                raise ContractError("foreign-key types must match")
    reconciliations = raw.get("reconciliations", [])
    if not isinstance(reconciliations, list) or len(reconciliations) > 50:
        raise ContractError("invalid reconciliation list")
    for check in reconciliations:
        obj(check, {"name", "left", "right", "tolerance"}, {"name", "left", "right"})
        name(check["name"])
        for side in ["left", "right"]:
            spec = obj(check[side], {"dataset", "field"}, {"dataset", "field"})
            if spec["dataset"] not in by_name or spec["field"] not in by_name[spec["dataset"]]["fields"]:
                raise ContractError("unknown aggregate field")
            if by_name[spec["dataset"]]["fields"][spec["field"]]["type"] not in {"decimal", "integer"}:
                raise ContractError("sum reconciliation needs numeric fields")
        try:
            tolerance = Decimal(str(check.get("tolerance", "0")))
            if not tolerance.is_finite() or tolerance < 0 or len(str(tolerance)) > 1000 or abs(tolerance.adjusted()) > 1000:
                raise ValueError()
        except Exception:
            raise ContractError("invalid reconciliation tolerance") from None
    return {"version": 1, "name": title, "datasets": datasets,
            "reconciliations": reconciliations, "limits": limits}


def load_contract(path):
    try:
        with Path(path).open("rb") as stream:
            content = stream.read(1048577)
        if len(content) > 1048576:
            raise ValueError()
        return validate_contract(strict_json(content.decode("utf-8")))
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("contract could not be loaded or is invalid") from None
