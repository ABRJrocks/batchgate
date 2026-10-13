"""Streaming local-file readers with bounded physical lines."""
from __future__ import annotations

import csv
import stat
from dataclasses import dataclass
from pathlib import Path

from .contract import ContractError, safe_relative


class InputError(ValueError):
    def __init__(self, code, line=None):
        super().__init__(code)
        self.code, self.line = code, line


@dataclass
class Record:
    row: int
    line: int
    data: dict | None
    error: str | None = None


def resolve_input(root, relative):
    safe_relative(relative)
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ContractError("input resolves outside the data directory")
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            raise OSError()
    except OSError:
        raise InputError("unreadable_file") from None
    return path


def bounded_lines(stream, limits):
    total, line = 0, 0
    while True:
        text = stream.readline(limits["max_line_chars"] + 1)
        if not text:
            return
        line += 1
        if len(text) > limits["max_line_chars"]:
            raise InputError("line_limit", line)
        total += len(text.encode("utf-8"))
        if total > limits["max_bytes"]:
            raise InputError("byte_limit", line)
        yield text


def read_csv(path, dataset, limits):
    try:
        if path.stat().st_size > limits["max_bytes"]:
            raise InputError("byte_limit")
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(bounded_lines(stream, limits),
                                delimiter=dataset.get("delimiter", ","), strict=True)
            header = next(reader, None)
            if header is None or not header or len(header) > 200 or len(set(header)) != len(header) or any(not x for x in header):
                raise InputError("invalid_header", 1)
            fields = dataset["fields"]
            if any(rule.get("required", True) and field not in header for field, rule in fields.items()):
                raise InputError("missing_header", reader.line_num)
            if not dataset.get("allow_extra_fields", False) and set(header) - set(fields):
                raise InputError("extra_header", reader.line_num)
            for row, cells in enumerate(reader, 1):
                if row > limits["max_rows"]:
                    raise InputError("row_limit", reader.line_num)
                if len(cells) != len(header):
                    yield Record(row, reader.line_num, None, "row_width")
                else:
                    yield Record(row, reader.line_num, dict(zip(header, cells)))
    except (OSError, UnicodeError):
        raise InputError("unreadable_file") from None
    except csv.Error:
        raise InputError("csv_syntax", reader.line_num) from None
