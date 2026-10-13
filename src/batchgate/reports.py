"""Redacted machine reports and atomic output files."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET


class ReportError(ValueError):
    pass


def json_report(result):
    return json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=True) + '\n'


def junit_report(result):
    cases = len(result.datasets) + len(result.reconciliations)
    failed = sum(not d.passed for d in result.datasets) + sum(not r.passed for r in result.reconciliations)
    suite = ET.Element('testsuite', name=result.name, tests=str(cases), failures=str(failed), errors='0')
    for dataset in result.datasets:
        case = ET.SubElement(suite, 'testcase', classname='batchgate.dataset', name=dataset.name)
        if not dataset.passed:
            failure = ET.SubElement(case, 'failure', message='Dataset validation failed', type='validation')
            failure.text = json.dumps(dataset.to_dict(), sort_keys=True)
    for check in result.reconciliations:
        case = ET.SubElement(suite, 'testcase', classname='batchgate.reconciliation', name=check.name)
        if not check.passed:
            ET.SubElement(case, 'failure', message=check.code, type='reconciliation')
    return ET.tostring(suite, encoding='unicode', xml_declaration=True) + '\n'


def atomic_write(path, content):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with NamedTemporaryFile('w', encoding='utf-8', newline='\n', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except (OSError, ValueError):
        raise ReportError('report could not be written') from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def check_destinations(destinations, protected_paths=()):
    paths = [Path(path).resolve() for path in destinations if path is not None]
    protected = {Path(path).resolve() for path in protected_paths}
    if len(set(paths)) != len(paths) or any(p in protected for p in paths):
        raise ReportError('report paths must be distinct and must not overwrite inputs or the contract')


def write_reports(result, *, json_path=None, junit_path=None, html_path=None, protected_paths=()):
    from .html_report import html_report
    check_destinations([json_path, junit_path, html_path], protected_paths)
    for path, render in [(json_path, json_report), (junit_path, junit_report), (html_path, html_report)]:
        if path is not None:
            atomic_write(path, render(result))
