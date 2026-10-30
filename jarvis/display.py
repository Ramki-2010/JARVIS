"""Terminal-safe display of untrusted text (ADR-0010 D3 item 10).

Text that came from a project file, a relayed result or a note is data, and printing
it raw would let it carry terminal escape sequences. Everything of that kind is printed
through `safe`. Stored bytes are never changed; only what is shown.
"""

_KEEP = frozenset("\n\t")


def _escape(ch: str) -> str:
    code = ord(ch)
    return "\\x%02x" % code if code < 0x100 else "\\u%04x" % code


def safe(text: str) -> str:
    """Replace control characters other than newline and tab, the C1 range and the
    bidirectional-override characters with a visible escape such as \\x1b."""
    out = []
    for ch in text:
        code = ord(ch)
        if ch in _KEEP:
            out.append(ch)
        elif code < 0x20 or code == 0x7F or 0x80 <= code <= 0x9F or 0x202A <= code <= 0x202E \
                or 0x2066 <= code <= 0x2069 or code in (0x200E, 0x200F, 0x061C):
            out.append(_escape(ch))
        else:
            out.append(ch)
    return "".join(out)
