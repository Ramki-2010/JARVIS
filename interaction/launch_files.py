"""Finding a file by name inside the catalog folders (ADR-0015 D3). Names and extensions only, never contents.

The name a person says is a lookup token and nothing more: each word of it must be a word of the file name, or the start of one
(three letters or more), so a long title need not be spelled out in full. Exact matches are listed first.
A found path must resolve (real path, so links and junctions cannot lead out) to a regular file inside the folder it was
found under, with an extension on the allow list and none on the never-open list. This module starts nothing and reads
no file contents.
"""

import os
import re
import time
from typing import Callable, List, NamedTuple, Sequence, Tuple

from interaction.launch_catalog import FILE_EXTENSIONS, NEVER_OPEN

MAX_DEPTH = 4
MAX_ENTRIES = 20000
BUDGET_S = 2.0
MAX_MATCHES = 8
PREFIX_MIN = 3
QUERY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .'-]{1,59}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class Match(NamedTuple):
    folder_id: str
    path: str
    name: str
    ext: str


class Found(NamedTuple):
    matches: Tuple[Match, ...]
    truncated: bool   # the search stopped at a limit before looking everywhere


def words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def _fits(wanted: List[str], name_words: List[str]) -> int:
    """0 = the file name is exactly these words, 1 = every word matches whole, 2 = some word matches a word start, 3 = no match."""
    if wanted == name_words:
        return 0
    rank = 1
    for w in wanted:
        if w in name_words:
            continue
        if len(w) >= PREFIX_MIN and any(n.startswith(w) for n in name_words):
            rank = 2
            continue
        return 3
    return rank


def contained(path: str, root: str) -> bool:
    """The real path of `path` is `root` itself or below it, and it is a regular file."""
    try:
        real, base = os.path.realpath(path), os.path.realpath(root)
        return os.path.commonpath([real, base]) == base and os.path.isfile(real) and not os.path.islink(path)
    except (OSError, ValueError):
        return False


def _ordered(found) -> Tuple[Match, ...]:
    return tuple(m for _, m in sorted(found, key=lambda rm: (rm[0], rm[1].name.casefold())))


def find(roots: Sequence[Tuple[str, str]], extensions, query: str, clock: Callable[[], float] = time.monotonic,
         max_entries: int = MAX_ENTRIES, max_depth: int = MAX_DEPTH, budget: float = BUDGET_S) -> Found:
    """roots: [(folder id, absolute folder path)]; extensions: the allowed extensions for this search."""
    if not isinstance(query, str) or not QUERY_RE.match(query.strip()):
        return Found((), False)
    wanted = words(query)
    allowed = {e.lower() for e in extensions} & FILE_EXTENSIONS - NEVER_OPEN
    if not wanted or not allowed:
        return Found((), False)
    start, seen, truncated, out = clock(), 0, False, []
    for folder_id, root in roots:
        queue = [(root, 0)]
        while queue:
            here, depth = queue.pop(0)
            try:
                it = os.scandir(here)
            except OSError:
                continue
            with it:
                for entry in it:
                    seen += 1
                    if seen > max_entries or clock() - start > budget:
                        return Found(_ordered(out), True)
                    try:
                        if entry.is_symlink() or entry.is_junction():
                            continue          # a link is never followed and never opened
                        if entry.is_dir(follow_symlinks=False):
                            if depth < max_depth:
                                queue.append((entry.path, depth + 1))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                    except OSError:
                        continue
                    stem, ext = os.path.splitext(entry.name)
                    ext = ext.lower()
                    if ext not in allowed or _CONTROL.search(entry.name) or (rank := _fits(wanted, words(stem))) == 3:
                        continue
                    if not contained(entry.path, root):
                        continue
                    out.append((rank, Match(folder_id, entry.path, entry.name, ext)))
                    if len(out) >= MAX_MATCHES:
                        return Found(_ordered(out), True)
    return Found(_ordered(out), truncated)
