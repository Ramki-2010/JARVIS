"""Starts one program from the catalog (ADR-0015 D2). The fourth process-creating place, and a deliberately dumb one.

It takes an absolute `.exe` path and a fixed argument list, both read from RK's catalog (for a file, the one resolved path is
a single argument): never a shell, never `cmd /c` or `start`, never text typed by the user, never the caller's environment.
The new process is detached: JARVIS does not wait for it, read its output or hold its handles. It runs with RK's ordinary
rights and cannot elevate. This module imports no network module.
"""

import os
import re
import subprocess
from typing import List, NamedTuple, Sequence

# What a started program receives instead of JARVIS's own environment: the plain per-user locations ordinary
# programs need to find their settings, and a system-only PATH. Nothing else (no token, key or project variable).
_ENV_KEEP = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES",
             "PROGRAMFILES(X86)", "PROGRAMDATA", "COMPUTERNAME", "USERNAME", "HOMEDRIVE", "HOMEPATH", "SYSTEMDRIVE", "COMSPEC")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class LaunchRefused(ValueError):
    """A start that must not be made."""


class LaunchResult(NamedTuple):
    ok: bool
    error: str   # "" when started; else REFUSED, MISSING or FAILED


def environment() -> dict:
    env = {name: os.environ[name] for name in _ENV_KEEP if name in os.environ}
    env["PATH"] = os.path.join(env.get("SYSTEMROOT", r"C:\Windows"), "System32")
    return env


def command(exe: str, args: Sequence[str]) -> List[str]:
    if not isinstance(exe, str) or not os.path.isabs(exe) or not exe.lower().endswith(".exe") or exe.startswith("\\\\") or _CONTROL.search(exe):
        raise LaunchRefused("not an absolute local program path")
    if not isinstance(args, (list, tuple)) or len(args) > 8:
        raise LaunchRefused("not a fixed argument list")
    for arg in args:
        if not isinstance(arg, str) or "\x00" in arg or len(arg) > 600:
            raise LaunchRefused("an argument is not a plain string")
    return [exe] + list(args)


def start(exe: str, args: Sequence[str]) -> LaunchResult:
    """Start the program detached and return at once. Never raises for a routine failure."""
    try:
        cmd = command(exe, args)
    except LaunchRefused:
        return LaunchResult(False, "REFUSED")
    if not os.path.isfile(exe):
        return LaunchResult(False, "MISSING")
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP   # Windows only, like JARVIS
    try:
        subprocess.Popen(cmd, cwd=os.path.dirname(exe), env=environment(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, creationflags=flags)
    except OSError:
        return LaunchResult(False, "FAILED")
    return LaunchResult(True, "")
