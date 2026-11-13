"""Strict RSS reading (ADR-0014 D3 item 5): refuse any document type or entity declaration, at most 30 items."""

import re
from datetime import timezone
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from fetcher.text import clean

MAX_ITEMS = 30
_DANGER = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.I)


class BadFeed(Exception):
    pass


def parse(data: bytes):
    """Return [(title, iso utc time or "")] for up to MAX_ITEMS items. Raise BadFeed on anything unexpected."""
    if _DANGER.search(data):
        raise BadFeed("DOCTYPE")
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise BadFeed("XML") from None
    if root.tag != "rss":
        raise BadFeed("NOT_RSS")
    out = []
    for item in root.iter("item"):
        title = clean(item.findtext("title") or "", 200)
        if not title:
            continue
        when = ""
        try:
            stamp = parsedate_to_datetime((item.findtext("pubDate") or "").strip())
            when = stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        except (TypeError, ValueError, IndexError):
            when = ""
        out.append((title, when))
        if len(out) >= MAX_ITEMS:
            break
    if not out:
        raise BadFeed("EMPTY")
    return out
