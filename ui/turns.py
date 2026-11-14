"""One conversation turn at a time for the dashboard's text box (ADR-0011 Amendment 2).

The server never decides anything here. The advisor hands it one function, `respond(text)`, which yields
(kind, text) events exactly as the terminal conversation does. This module only:
  * validates a request body strictly (`parse_say`): one field, `text`, a string of 1 to 400 characters with no
    control characters; unexpected, duplicate or missing fields are refused, nothing is cleaned or defaulted;
  * runs one turn at a time in a worker thread, so a slow model turn never freezes the page;
  * keeps only the last few turns, in memory (nothing is written to disk).

The one lock is held for a whole exchange. What it is held *for* is recorded: "turn" (the intent layer is
working on a line, from the page or from the terminal, which takes the same lock through `exclusive()`), "mic" (a
button-held listen is in progress, ADR-0011 Amendment 3) or "after" (replies are being spoken). `busy()` is true
only for "turn", so the ring shows INTERPRETING only while the intent layer is really working (ADR-0011 D4);
`occupied()` is true for any of them.
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
MIC_ACTIONS = ("start", "stop")


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


class MicRefused(Exception):
    """The microphone button cannot be used right now; `status` is the HTTP code and the message a short reason."""

    def __init__(self, reason: str, status: int = 409):
        super().__init__(reason)
        self.status = status


def parse_mic(raw: bytes) -> str:
    """The button action, `start` or `stop`, or BadRequest. Same strictness as `parse_say`."""
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
    if "action" not in obj:
        raise BadRequest("missing field: action")
    if set(obj) != {"action"}:
        raise BadRequest("unexpected field")
    if obj["action"] not in MIC_ACTIONS:
        raise BadRequest("action must be start or stop")
    return obj["action"]


def clean(kind: str, text: str) -> Tuple[str, str]:
    """An event as the page may show it: a known kind, no control characters except newline, bounded."""
    text = "".join(c if (c == "\n" or unicodedata.category(c) not in ("Cc", "Cs")) else " " for c in str(text))
    return kind, text[:MAX_EVENT]


class Turns:
    def __init__(self, respond: Optional[Callable[[str], Iterable[Tuple[str, str]]]], after: Optional[Callable[[], None]] = None):
        self.respond = respond
        self.after = after              # runs once a turn's replies are stored (the advisor waits for speech here)
        self._lock = threading.Lock()   # held for exactly as long as an exchange is running
        self._mu = threading.Lock()     # guards the turn table and the kind
        self._kind: Optional[str] = None
        self._next = 1
        self._table: "OrderedDict[int, dict]" = OrderedDict()

    @property
    def enabled(self) -> bool:
        return self.respond is not None

    def busy(self) -> bool:
        """True only while the intent layer is working on a line (the ring's INTERPRETING)."""
        return self._lock.locked() and self._kind == "turn"

    def occupied(self) -> bool:
        return self._lock.locked()

    def _set(self, kind: Optional[str]) -> None:
        with self._mu:
            self._kind = kind

    @contextlib.contextmanager
    def exclusive(self):
        """The terminal takes its turn through this, so a page turn and a terminal turn never overlap."""
        with self._lock:
            self._set("turn")
            try:
                yield
            finally:
                self._set(None)

    def reserve(self, kind: str) -> bool:
        """Take the lock without starting a turn (a microphone listen); False if anything is already running."""
        if not self._lock.acquire(blocking=False):
            return False
        self._set(kind)
        return True

    def release(self) -> None:
        self._set(None)
        self._lock.release()

    def submit(self, text: str) -> Optional[int]:
        """Start a turn; None if anything is already running."""
        if self.respond is None or not self.reserve("turn"):
            return None
        return self.start_reserved(text)

    def start_reserved(self, text: str, respond: Optional[Callable[[str], Iterable[Tuple[str, str]]]] = None) -> int:
        """Run a turn under a lock the caller already holds via `reserve`; the turn releases it when it ends."""
        run = respond or self.respond
        try:
            self._set("turn")
            with self._mu:
                number = self._next
                self._next += 1
                self._table[number] = {"state": "running", "events": []}
                while len(self._table) > KEEP:
                    self._table.popitem(last=False)
            threading.Thread(target=self._run, args=(number, text, run), daemon=True).start()
        except BaseException:
            self.release()
            raise
        return number

    def _run(self, number: int, text: str, run) -> None:
        events: List[Tuple[str, str]] = []
        try:
            try:
                for kind, out in run(text):
                    if kind in KINDS:
                        events.append(clean(kind, out))
            except Exception as exc:  # a turn that fails is reported as failed, never silently dropped
                events.append(clean("error", "That turn failed (%s)." % type(exc).__name__))
            with self._mu:
                if number in self._table:
                    self._table[number] = {"state": "done", "events": [list(e) for e in events]}
                self._kind = "after"   # the replies are out; anything still happening is speech, not interpreting
            if self.after is not None:
                try:
                    self.after()
                except Exception:
                    pass
        finally:
            self.release()

    def get(self, number: int) -> Optional[dict]:
        with self._mu:
            entry = self._table.get(number)
            return dict(entry) if entry else None
