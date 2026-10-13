"""Detect ordinary replacement and mutation of batch files during validation."""
from dataclasses import dataclass
from pathlib import Path

from .contract import ContractError
from .readers import InputError, resolve_input


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    signature: tuple

    @classmethod
    def capture(cls, path):
        path = Path(path).resolve()
        info = path.stat()
        return cls(path, (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))

    def unchanged(self, root, relative):
        # shortcut: metadata checks do not lock files; consume immutable batches.
        try:
            current = resolve_input(root, relative)
            return current == self.path and self.signature == self.capture(current).signature
        except (OSError, InputError, ContractError):
            return False
