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


def _keys(dataset):
    return ([dataset['primary_key']] if dataset.get('primary_key') else []) + dataset.get('unique', [])


def _index_callback(dataset, index):
    def on_row(record, values, result, bad):
        before = result.issue_count
        for number, fields in enumerate(_keys(dataset)):
            if all(values.get(f) is not None for f in fields):
                if index.add_key(dataset['name'], number, [values[f] for f in fields], record.row) is not None:
                    result.add('duplicate_key', row=record.row, line=record.line, field=fields[0])
        for number, check in enumerate(dataset.get('foreign_keys', [])):
            fields = check['fields']
            if all(values.get(f) is not None for f in fields):
                index.add_reference(dataset['name'], number, [values[f] for f in fields], record.row, record.line)
        index.add_row(dataset['name'], record.row, record.line, bad or result.issue_count > before)
    return on_row


def validate_batch(contract, data_dir):
    """Validate a contract dictionary against a stable local data directory."""
    from pathlib import Path
    from .contract import ContractError, validate_contract
    from .index import key_index
    from .readers import resolve_input
    from .result import BatchResult

    config = validate_contract(contract)
    root = Path(data_dir).resolve()
    if not root.is_dir():
        raise ContractError('data directory must exist')
    paths = {}
    for dataset in config['datasets']:
        try:
            paths[dataset['name']] = resolve_input(root, dataset['path'])
        except InputError:
            paths[dataset['name']] = None
    results = []
    with key_index() as index:
        for dataset in config['datasets']:
            if paths[dataset['name']] is None:
                result = DatasetResult(dataset['name'], sample_limit=config['limits']['max_issues'])
                result.add('unreadable_file')
            else:
                result = _scan(dataset, paths[dataset['name']], config['limits'], _index_callback(dataset, index))
            results.append(result)
            index.db.commit()
        by_name = {r.name: r for r in results}
        definitions = {d['name']: d for d in config['datasets']}
        for dataset in config['datasets']:
            result = by_name[dataset['name']]
            for number, check in enumerate(dataset.get('foreign_keys', [])):
                if not by_name[check['dataset']].complete:
                    result.add('reference_unavailable')
                    continue
                target_rule = _keys(definitions[check['dataset']]).index(check['references'])
                for row, line in index.missing_references(dataset['name'], number, check['dataset'], target_rule):
                    result.add('foreign_key', row=row, line=line, field=check['fields'][0])
                    index.mark_bad(dataset['name'], row)
            result.invalid_rows = index.invalid_rows(dataset['name'])
    return BatchResult(config['name'], results)
