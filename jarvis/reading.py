"""Bounded, mediated reading of project files (ADR-0010 D3).

These functions act only on a target the evaluator has just returned ALLOW for: a
canonical PROJECT_PATH inside a contract scope. They add the limits the evaluator does
not own: a size cap, text only, regular files only, no secret-looking file names, and
no gap between the check and the open (the path is resolved again before the open and
again after the read, and the file identity must not change).

Nothing here returns anything it did not read: the SHA-256 is over the bytes returned.
Everything returned is data. It is shown through `display.safe` and never reaches the
planner, evaluator, constraints or policy.
"""

import codecs
import fnmatch
import hashlib
import os
import stat
from dataclasses import dataclass
from typing import List, Tuple

from . import canonicalizer
from .model import TargetFailure

MAX_FILE_BYTES = 64 * 1024
MAX_DIR_ENTRIES = 200

# ADR-0010 D3 item 9, matched case-insensitively against the file name only.
SECRET_LIKE_NAMES = (".env", ".env.*", "*.pem", "*.key", "*.pfx", "*.p12", "id_rsa*",
                     "id_ed25519*", "credentials*", "*secret*", "*.kdbx")


class ReadError(ValueError):
    """Carries a fixed code, never a path or content."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FileRead:
    path: str            # canonical path that was read
    size_on_disk: int
    bytes_read: int      # bytes returned (at most MAX_FILE_BYTES)
    sha256: str          # of the bytes returned
    truncated: bool
    text: str

    def as_audit(self) -> dict:
        """What the audit record keeps: never the text."""
        return {"path": self.path, "size": self.size_on_disk, "bytes_read": self.bytes_read,
                "sha256": self.sha256, "truncated": self.truncated}


@dataclass(frozen=True)
class DirListing:
    path: str
    entries: Tuple[Tuple[str, str], ...]   # (name, "dir" | "file" | "link" | "other")
    truncated: bool

    def as_audit(self) -> dict:
        return {"path": self.path, "entries": len(self.entries), "truncated": self.truncated}


def secret_like(name: str) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatchcase(lowered, pattern) for pattern in SECRET_LIKE_NAMES)


def _same_target(canonical: str) -> str:
    """Resolve again and require the same canonical path the evaluator allowed."""
    again = canonicalizer.resolve(canonical)
    if isinstance(again, TargetFailure) or canonicalizer.normalize(again) != canonicalizer.normalize(canonical):
        raise ReadError("READ_PATH_CHANGED")
    return again


def _identity(info: os.stat_result) -> Tuple[int, int]:
    return (info.st_dev, info.st_ino)


def read_file(canonical: str) -> FileRead:
    """Read one allowed canonical file path. Raises ReadError with a closed code."""
    if secret_like(os.path.basename(canonical)):
        raise ReadError("READ_SECRET_LIKE_NAME")
    path = _same_target(canonical)
    try:
        before = os.stat(path)
        if not stat.S_ISREG(before.st_mode):
            raise ReadError("READ_NOT_REGULAR")
        with open(path, "rb") as fh:
            opened = os.fstat(fh.fileno())
            if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(before):
                raise ReadError("READ_PATH_CHANGED")
            raw = fh.read(MAX_FILE_BYTES + 1)
        truncated = len(raw) > MAX_FILE_BYTES
        if truncated:
            raw = raw[:MAX_FILE_BYTES]
        if b"\x00" in raw:
            raise ReadError("READ_BINARY")
        decoder = codecs.getincrementaldecoder("utf-8")()
        try:
            text = decoder.decode(raw, final=not truncated)  # a cut mid-character is held back
        except UnicodeDecodeError:
            raise ReadError("READ_NOT_UTF8") from None
        data = text.encode("utf-8")
        after = _same_target(canonical)
        if _identity(os.stat(after)) != _identity(before):
            raise ReadError("READ_PATH_CHANGED")
    except ReadError:
        raise
    except OSError:
        raise ReadError("READ_IO_ERROR") from None
    return FileRead(path=canonical, size_on_disk=opened.st_size, bytes_read=len(data),
                    sha256=hashlib.sha256(data).hexdigest(), truncated=truncated, text=text)


def list_directory(canonical: str) -> DirListing:
    """Names only, sorted, at most MAX_DIR_ENTRIES, links and junctions listed but not followed."""
    path = _same_target(canonical)
    try:
        if not stat.S_ISDIR(os.stat(path).st_mode):
            raise ReadError("READ_NOT_DIRECTORY")
        found: List[Tuple[str, str]] = []
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_symlink() or entry.is_junction():
                    kind = "link"
                elif entry.is_dir(follow_symlinks=False):
                    kind = "dir"
                elif entry.is_file(follow_symlinks=False):
                    kind = "file"
                else:
                    kind = "other"
                found.append((entry.name, kind))
        _same_target(canonical)
    except ReadError:
        raise
    except OSError:
        raise ReadError("READ_IO_ERROR") from None
    found.sort(key=lambda item: (item[0].casefold(), item[0]))
    truncated = len(found) > MAX_DIR_ENTRIES
    return DirListing(path=canonical, entries=tuple(found[:MAX_DIR_ENTRIES]), truncated=truncated)
