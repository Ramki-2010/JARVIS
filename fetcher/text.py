"""Everything fetched is untrusted text (ADR-0014 D4): neutralise it before it leaves this program."""

import re

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
_TAGS = re.compile(r"<[^>]{0,200}>")


def clean(value, limit: int = 160) -> str:
    text = value if isinstance(value, str) else ""
    text = _TAGS.sub(" ", text)
    text = _CONTROL.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 3].rstrip() + "..."
