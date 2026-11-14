"""One conversation turn at a time for the dashboard's text box (ADR-0011 Amendment 2).

The server never decides anything here. The advisor hands it one function, `respond(text)`, which yields
(kind, text) events exactly as the terminal conversation does. This module only:
  * validates a request body strictly (`parse_say`): one field, `text`, a string of 1 to 400 characters with no
    control characters; unexpected, duplicate or missing fields are refused, nothing is cleaned or defaulted;
  * runs one turn at a time in a worker thread, so a slow model turn never freezes the page;
  * keeps only the last few turns, in memory (nothing is written to disk).

`busy()` is true exactly while a turn is running (from the page or from the terminal, which takes the same
lock through `exclusive()`). The ring shows INTERPRETING only while it is true (ADR-0011 D4).
"""

import contextlib
import json
import threading
import unicodedata
from collections import OrderedDict
from typing import Callable, Iterable, List, Optional, Tuple

MAX_BODY = 1024
MAX_TEXT = 400
KEEP = 8
MAX_EVENT = 6000
KINDS = ("say", "show", "error")


class BadRequest(ValueError):
    """The request body is not acceptable; the message is a short reason, never an echo of the input."""


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise BadRequest("duplicate field")
        seen[key] = value
    return seen


def parse_say(raw: bytes) -> str:
    """The line to say, or BadRequest. Strict: no cleaning, no defaults."""
    if len(raw) > MAX_BODY:
        raise BadRequest("body too large")
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except BadRequest:
        raise
    except (UnicodeDecodeError, ValueError):
        raise BadRequest("body is not valid JSON")
    if not isinstance(obj, dict):
        raise BadRequest("body must be an object")
    if "text" not in obj:
        raise BadRequest("missing field: text")
    if set(obj) != {"text"}:
        raise BadRequest("unexpected field")
    text = obj["text"]
    if not isinstance(text, str):
        raise BadRequest("text must be a string")
    if not text.strip() or len(text) > MAX_TEXT:
        raise BadRequest("text must be 1 to %d characters" % MAX_TEXT)
    if any(unicodedata.category(c) in ("Cc", "Cs") for c in text):
        raise BadRequest("control characters are not allowed")
    return text


def clean(kind: str, text: str) -> Tuple[str, str]:
    """An event as the page may show it: a known kind, no control characters except newline, bounded."""
    text = "".join(c if (c == "\n" or unicodedata.category(c) not in ("Cc", "Cs")) else " " for c in str(text))
    return kind, text[:MAX_EVENT]


class Turns:
    def __init__(self, respond: Optional[Callable[[str], Iterable[Tuple[str, str]]]]):
        self.respond = respond
        self._lock = threading.Lock()   # held for exactly as long as a turn is running
        self._mu = threading.Lock()     # guards the turn table
        self._next = 1
        self._table: "OrderedDict[int, dict]" = OrderedDict()

    @property
    def enabled(self) -> bool:
        return self.respond is not None

    def busy(self) -> bool:
        return self._lock.locked()

    @contextlib.contextmanager
    def exclusive(self):
        """The terminal takes its turn through this, so a page turn and a terminal turn never overlap."""
        with self._lock:
            yield

    def submit(self, text: str) -> Optional[int]:
        """Start a turn; None if one is already running."""
        if self.respond is None or not self._lock.acquire(blocking=False):
            return None
        try:
            with self._mu:
                number = self._next
                self._next += 1
                self._table[number] = {"state": "running", "events": []}
                while len(self._table) > KEEP:
                    self._table.popitem(last=False)
            threading.Thread(target=self._run, args=(number, text), daemon=True).start()
        except BaseException:
            self._lock.release()
            raise
        return number

    def _run(self, number: int, text: str) -> None:
        events: List[Tuple[str, str]] = []
        try:
            for kind, out in self.respond(text):
                if kind in KINDS:
                    events.append(clean(kind, out))
        except Exception as exc:  # a turn that fails is reported as failed, never silently dropped
            events.append(clean("error", "That turn failed (%s)." % type(exc).__name__))
        finally:
            with self._mu:
                if number in self._table:
                    self._table[number] = {"state": "done", "events": [list(e) for e in events]}
            self._lock.release()

    def get(self, number: int) -> Optional[dict]:
        with self._mu:
            entry = self._table.get(number)
            return dict(entry) if entry else None
