"""Temporary disk-backed key indexes with per-run keyed hashes."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from pathlib import Path

from .values import canonical


class KeyIndex:
    def __init__(self, path):
        self.secret = os.urandom(32)
        self.db = sqlite3.connect(path)
        self.db.executescript('''
            PRAGMA temp_store=FILE;
            CREATE TABLE rows(dataset TEXT, row INTEGER, line INTEGER, bad INTEGER,
                              PRIMARY KEY(dataset, row));
            CREATE TABLE keys(dataset TEXT, rule INTEGER, digest BLOB, row INTEGER,
                              PRIMARY KEY(dataset, rule, digest));
            CREATE TABLE refs(dataset TEXT, rule INTEGER, row INTEGER, line INTEGER, digest BLOB);
            CREATE INDEX refs_rule ON refs(dataset, rule);
        ''')

    def digest(self, values):
        body = json.dumps([canonical(x) for x in values], ensure_ascii=True, separators=(',', ':')).encode()
        return hmac.new(self.secret, body, hashlib.sha256).digest()

    def add_row(self, dataset, row, line, bad):
        self.db.execute('INSERT INTO rows VALUES (?, ?, ?, ?)', (dataset, row, line, int(bad)))

    def mark_bad(self, dataset, row):
        self.db.execute('UPDATE rows SET bad=1 WHERE dataset=? AND row=?', (dataset, row))

    def invalid_rows(self, dataset):
        return self.db.execute('SELECT COUNT(*) FROM rows WHERE dataset=? AND bad=1', (dataset,)).fetchone()[0]

    def add_key(self, dataset, rule, values, row):
        digest = self.digest(values)
        cursor = self.db.execute('INSERT OR IGNORE INTO keys VALUES (?, ?, ?, ?)', (dataset, rule, digest, row))
        if cursor.rowcount == 0:
            return self.db.execute('SELECT row FROM keys WHERE dataset=? AND rule=? AND digest=?',
                                   (dataset, rule, digest)).fetchone()[0]
        return None

    def add_reference(self, dataset, rule, values, row, line):
        self.db.execute('INSERT INTO refs VALUES (?, ?, ?, ?, ?)',
                        (dataset, rule, row, line, self.digest(values)))

    def missing_references(self, dataset, rule, target, target_rule):
        return self.db.execute('''SELECT r.row, r.line FROM refs r
            LEFT JOIN keys k ON k.dataset=? AND k.rule=? AND k.digest=r.digest
            WHERE r.dataset=? AND r.rule=? AND k.digest IS NULL ORDER BY r.row''',
            (target, target_rule, dataset, rule))


@contextmanager
def key_index():
    with TemporaryDirectory(prefix='batchgate-') as directory:
        index = KeyIndex(Path(directory) / 'keys.sqlite3')
        try:
            yield index
        finally:
            index.db.close()
