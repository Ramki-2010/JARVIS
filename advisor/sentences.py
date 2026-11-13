"""Split a streamed reply into sentences, so speech can start on the first one."""

import re
from typing import Iterable, Iterator

_END = re.compile(r"(?<=[.!?])[\"')\]]*\s+")
_ABBREV = ("mr.", "mrs.", "ms.", "dr.", "st.", "no.", "vs.", "e.g.", "i.e.")
MIN_FIRST = 12


def sentences(pieces: Iterable[str]) -> Iterator[str]:
    buf = ""
    for piece in pieces:
        buf += piece
        while True:
            m = _END.search(buf)
            if not m:
                break
            end = m.end()
            head = buf[:end].strip()
            if head.lower().endswith(_ABBREV) or len(head) < MIN_FIRST:
                m2 = _END.search(buf, end)
                if not m2:
                    break
                end = m2.end()
                head = buf[:end].strip()
            buf = buf[end:]
            if head:
                yield head
    tail = buf.strip()
    if tail:
        yield tail
