"""CLI exit codes: 0 accepted, 1 rejected, 2 configuration/output failure."""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from . import __version__
from .contract import ContractError, load_contract
from .engine import validate_batch
from .reports import ReportError, check_destinations, write_reports


def main(argv=None):
    parser = argparse.ArgumentParser(description='Validate local CSV/JSONL batches before import.')
    parser.add_argument('--version', action='version', version=f'BatchGate {__version__}')
    commands = parser.add_subparsers(dest='command', required=True)
    lint = commands.add_parser('lint', help='Validate a contract without reading data files')
    lint.add_argument('contract', type=Path)
    check = commands.add_parser('check', help='Gate a batch using the declared contract')
    check.add_argument('contract', type=Path)
    check.add_argument('--data-dir', type=Path, help='Input root; defaults to the contract directory')
    check.add_argument('--json-report', type=Path)
    check.add_argument('--junit', type=Path)
    check.add_argument('--html-report', type=Path)
    check.add_argument('--quiet', action='store_true')
    args = parser.parse_args(argv)
    try:
        config = load_contract(args.contract)
        if args.command == 'lint':
            print(f'VALID contract: {len(config["datasets"])} datasets, {len(config["reconciliations"])} reconciliations')
            return 0
        root = (args.data_dir or args.contract.resolve().parent).resolve()
        protected = [args.contract.resolve()] + [root / d['path'] for d in config['datasets']]
        check_destinations([args.json_report, args.junit, args.html_report], protected)
        result = validate_batch(config, root)
        write_reports(result, json_path=args.json_report, junit_path=args.junit,
                      html_path=args.html_report, protected_paths=protected)
        if not args.quiet:
            for ds in result.datasets:
                state = 'PASS' if ds.passed else 'FAIL'
                scan = 'complete' if ds.complete else 'incomplete'
                print(f'{state} {ds.name}: rows={ds.rows} invalid={ds.invalid_rows} issues={ds.issue_count} scan={scan}')
                if ds.counts:
                    print('  ' + ', '.join(f'{code}={count}' for code, count in sorted(ds.counts.items())))
            for item in result.reconciliations:
                print(f'{"PASS" if item.passed else "FAIL"} {item.name}: {item.code}')
            print('ACCEPTED batch' if result.passed else 'REJECTED batch')
        return 0 if result.passed else 1
    except (ContractError, ReportError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error):
        print('ERROR: local I/O or key-index operation failed', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Interrupted', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
