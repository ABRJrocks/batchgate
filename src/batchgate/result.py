"""Bounded diagnostics without retaining or reporting cell values."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Issue:
    code: str
    row: int | None = None
    line: int | None = None
    field: str | None = None


@dataclass
class DatasetResult:
    name: str
    sample_limit: int = 200
    rows: int = 0
    invalid_rows: int = 0
    complete: bool = False
    issue_count: int = 0
    counts: Counter = field(default_factory=Counter)
    issues: list[Issue] = field(default_factory=list)

    def add(self, code, *, row=None, line=None, field=None):
        self.issue_count += 1
        self.counts[code] += 1
        if len(self.issues) < self.sample_limit:
            self.issues.append(Issue(code, row, line, field))

    @property
    def passed(self):
        return self.complete and self.issue_count == 0

    def to_dict(self):
        return {"name": self.name, "passed": self.passed, "complete": self.complete,
                "rows": self.rows, "invalid_rows": self.invalid_rows,
                "issue_count": self.issue_count, "issue_counts": dict(sorted(self.counts.items())),
                "issues": [asdict(i) for i in self.issues],
                "issues_omitted": self.issue_count - len(self.issues)}


@dataclass
class ReconciliationResult:
    name: str
    passed: bool
    code: str


@dataclass
class BatchResult:
    name: str
    datasets: list[DatasetResult]
    reconciliations: list[ReconciliationResult] = field(default_factory=list)

    @property
    def passed(self):
        return all(d.passed for d in self.datasets) and all(r.passed for r in self.reconciliations)

    def to_dict(self):
        return {"report_version": 1, "name": self.name, "passed": self.passed,
                "datasets": [d.to_dict() for d in self.datasets],
                "reconciliations": [asdict(r) for r in self.reconciliations]}
