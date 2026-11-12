"""The one place a surface starts the control plane (ADR-0011 D2).

It runs `<python 3.14> -E -s -m jarvis --config <absolute path> <arguments>`:
the running interpreter by absolute path (never a bare `python` or `py`), no
shell, a fixed working folder (the repository), a minimal environment, a
timeout and a bounded output. `jarvis/` itself never creates a process.

`-E -s` instead of `-I`: isolated mode also drops the working folder from the
import path, and JARVIS is deliberately not installed into Python, so
`-I -m jarvis` cannot find it. ADR-0011 Amendment 1 records this.
"""

import locale
import os
import subprocess
import sys
from typing import List, NamedTuple, Sequence

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT_S = 60
MAX_OUTPUT = 256 * 1024
EXIT_TIMEOUT = 124
_ENV_KEEP = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")


class ChildRefused(ValueError):
    """A child call that must not be made."""


class ChildResult(NamedTuple):
    code: int
    text: str
    truncated: bool


def interpreter() -> str:
    if tuple(sys.version_info[:2]) != (3, 14):
        raise ChildRefused("the control plane needs Python 3.14; this is %d.%d" % tuple(sys.version_info[:2]))
    exe = sys.executable
    if not exe or not os.path.isabs(exe):
        raise ChildRefused("the interpreter path is not absolute")
    return exe


def command(config: str, args: Sequence[str]) -> List[str]:
    if not isinstance(config, str) or not os.path.isabs(config):
        raise ChildRefused("the config path must be absolute")
    for arg in args:
        if not isinstance(arg, str) or "\x00" in arg:
            raise ChildRefused("an argument is not a plain string")
    return [interpreter(), "-E", "-s", "-m", "jarvis", "--config", config] + list(args)


def environment() -> dict:
    return {name: os.environ[name] for name in _ENV_KEEP if name in os.environ}


def run(config: str, args: Sequence[str], timeout: int = TIMEOUT_S) -> ChildResult:
    cmd = command(config, args)
    try:
        proc = subprocess.run(cmd, cwd=REPO, env=environment(), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ChildResult(EXIT_TIMEOUT, "timed out after %d s" % timeout, False)
    raw = proc.stdout or b""
    text = raw[:MAX_OUTPUT].decode(locale.getencoding(), errors="replace")
    return ChildResult(proc.returncode, text, len(raw) > MAX_OUTPUT)
