"""Starts the public-data fetcher (ADR-0014 D2). A third process-creating place, after `child.py` and `voice_child.py`.

The fetcher is `<root>\\python314\\python.exe -E -s -m fetcher <lookup> <arguments>` run from the repository folder: its
own private copy of Python 3.14 by absolute path (so a firewall rule can name that one program and every other JARVIS
program stays blocked), no shell, a minimal environment, a timeout and a bounded output. Every argument is one of the
fixed keys in `fetcher.keys` or a short plain keyword; nothing from an utterance is ever passed on unchecked.
This module imports no network module and makes no connection itself.
"""

import json
import os
import re
import subprocess
import time
from collections import deque
from typing import List, NamedTuple, Optional

from fetcher import keys
from interaction.child import REPO

TIMEOUT_S = 25
MAX_OUTPUT = 64 * 1024
MAX_PER_MINUTE = 6
_ENV_KEEP = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
_KEYWORD = re.compile(r"^[a-z0-9][a-z0-9 ]{0,%d}$" % (keys.KEYWORD_MAX - 1))


class FetchRefused(ValueError):
    """A fetcher call that must not be made."""


class FetchResult(NamedTuple):
    ok: bool
    error: str      # "" when ok; else NOT_SET_UP, RATE, TIMEOUT, BAD_OUTPUT, or the fetcher's own code
    hosts: str      # comma-separated host names, for the audit record
    nbytes: int
    ms: int
    data: dict


def interpreter(root: str) -> str:
    exe = os.path.join(root, "python314", "python.exe")
    if not os.path.isabs(root) or not os.path.isfile(exe):
        raise FetchRefused("no fetcher interpreter at the fetcher folder")
    return exe


def arguments(lookup: str, args) -> List[str]:
    """The fixed argument list for one lookup, or FetchRefused."""
    args = [str(a) for a in args]
    if lookup == "weather" and len(args) == 1 and args[0] in keys.PLACES:
        return ["weather", args[0]]
    if lookup == "hn" and not args:
        return ["hn"]
    if lookup == "news" and 1 <= len(args) <= 2 and (args[0] in keys.NEWS or args[0] == "all") \
            and (len(args) == 1 or _KEYWORD.match(args[1])):
        return ["news"] + args
    raise FetchRefused("not a permitted lookup")


def environment() -> dict:
    env = {name: os.environ[name] for name in _ENV_KEEP if name in os.environ}
    env["PATH"] = os.path.join(env.get("SYSTEMROOT", r"C:\Windows"), "System32")
    env["PYTHONUTF8"] = "1"
    return env


class Fetcher:
    """Callable used by the controller: fetcher(lookup, args) -> FetchResult. Never raises for a routine failure."""

    def __init__(self, root: str, clock=time.monotonic):
        self.root = root
        self._clock = clock
        self._recent: "deque[float]" = deque()

    def _rate_ok(self) -> bool:
        now = self._clock()
        while self._recent and now - self._recent[0] > 60.0:
            self._recent.popleft()
        if len(self._recent) >= MAX_PER_MINUTE:
            return False
        self._recent.append(now)
        return True

    def __call__(self, lookup: str, args) -> FetchResult:
        argv = arguments(lookup, args)
        try:
            exe = interpreter(self.root)
        except FetchRefused:
            return FetchResult(False, "NOT_SET_UP", "", 0, 0, {})
        if not self._rate_ok():
            return FetchResult(False, "RATE", "", 0, 0, {})
        start = self._clock()
        try:
            proc = subprocess.run([exe, "-E", "-s", "-m", "fetcher"] + argv, cwd=REPO, env=environment(),
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return FetchResult(False, "TIMEOUT", "", 0, int((self._clock() - start) * 1000), {})
        except OSError:
            return FetchResult(False, "NOT_SET_UP", "", 0, 0, {})
        return parse_output((proc.stdout or b"")[:MAX_OUTPUT], int((self._clock() - start) * 1000))


def parse_output(raw: bytes, elapsed_ms: int) -> FetchResult:
    """Read the fetcher's one line of JSON. Anything unexpected is BAD_OUTPUT, never a guess."""
    try:
        obj = json.loads(raw.decode("utf-8", errors="replace").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return FetchResult(False, "BAD_OUTPUT", "", 0, elapsed_ms, {})
    if not isinstance(obj, dict):
        return FetchResult(False, "BAD_OUTPUT", "", 0, elapsed_ms, {})
    hosts = obj.get("hosts")
    hosts = ",".join(h for h in hosts if isinstance(h, str) and re.fullmatch(r"[a-z0-9.-]{1,63}", h)) if isinstance(hosts, list) else ""
    nbytes = obj.get("bytes") if isinstance(obj.get("bytes"), int) and not isinstance(obj.get("bytes"), bool) else 0
    ms = obj.get("ms") if isinstance(obj.get("ms"), int) and not isinstance(obj.get("ms"), bool) else elapsed_ms
    if obj.get("ok") is True and isinstance(obj.get("data"), dict):
        return FetchResult(True, "", hosts, max(0, nbytes), max(0, ms), obj["data"])
    code = obj.get("error")
    code = code if isinstance(code, str) and re.fullmatch(r"[A-Z_]{1,20}", code) else "BAD_OUTPUT"
    return FetchResult(False, code, hosts, max(0, nbytes), max(0, ms), {})
