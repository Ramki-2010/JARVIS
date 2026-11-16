"""Free memory before JARVIS runs: close the programs on RK's close list, then report what that really freed.

This is RK's own script, run by RK's launcher (scripts/start-jarvis.cmd) before the advisor starts. It is not part of
JARVIS: nothing in `jarvis/`, `advisor/`, `ui/`, `interaction/` or `voice/` can close a program, and JARVIS never runs
this script or edits the list. It is not recorded in the audit chain; it keeps its own log.

  py -3.14 scripts\\free_memory.py              show what it would close (a dry run; nothing is touched)
  py -3.14 scripts\\free_memory.py --apply      close the listed programs

The list is a TOML file that only RK edits (default: close_list.toml next to jarvis.toml). See
docs/examples/close_list.example.toml. For each program, in the order listed: ask it to close the way a person would
(its window is told to close; nothing is killed), wait up to `grace` seconds, and only if the entry says `force = true`
end whatever is left. A program that is not running is skipped. A program with `last = true` is closed after all the
others (a VPN, so that nothing keeps running on the open connection while the VPN is gone).

Hard limits that no list can change: a fixed set of programs is never touched (this machine's own system processes,
Python and the shells, Ollama and its model server, the Claude desktop app and its tools, the antivirus); names are plain
program names with no path or wildcard; at most 32 entries. The amount freed is measured from the machine's own
available-memory figure before and after, never estimated. Closing a program can lose its unsaved work: the list is
the owner's decision, and `force = true` should be reserved for programs that hold nothing to lose.
"""

import argparse
import csv
import ctypes
import io
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from datetime import datetime
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

PROTECTED = frozenset({
    # Windows itself and its shells
    "system", "registry", "smss", "csrss", "wininit", "winlogon", "services", "lsass", "svchost", "dwm", "fontdrvhost", "explorer",
    "sihost", "taskhostw", "runtimebroker", "ctfmon", "conhost", "cmd", "powershell", "pwsh", "windowsterminal", "wt", "taskmgr",
    # security software
    "msmpeng", "nissrv", "securityhealthservice", "securityhealthsystray", "mpdefendercoreservice",
    # the interpreter and tools JARVIS and its builder run on
    "python", "pythonw", "py", "pyw", "node", "git", "claude", "claude-code",
    # the language model server and the voice worker
    "ollama", "ollama app", "llama-server", "voice",
})
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,63}$")
MAX_ENTRIES = 32
MAX_GRACE = 120.0
SETTLE_SECONDS = 3.0


class ListError(ValueError):
    """The close list cannot be used; nothing is closed."""


class Entry(NamedTuple):
    id: str
    name: str
    images: Tuple[str, ...]   # lower-case program names without ".exe"
    force: bool
    grace: float
    last: bool


class Proc(NamedTuple):
    pid: int
    image: str   # lower-case, without ".exe"
    mb: float


class Result(NamedTuple):
    id: str
    name: str
    status: str     # "not running", "would close", "closed", "closed by force", "left open (still running)", "refused (never touched)"
    count: int
    mb: float


def plain(image: str) -> str:
    image = image.strip().lower()
    return image[:-4] if image.endswith(".exe") else image


def load_list(path: str) -> List[Entry]:
    try:
        with open(path, "rb") as fh:
            data = tomllib.loads(fh.read().decode("utf-8-sig"))   # an editor's byte-order mark is fine
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ListError("the close list cannot be read (%s)" % type(exc).__name__) from exc
    if data.get("schema_version") != 1:
        raise ListError("the close list needs schema_version = 1")
    if set(data) - {"schema_version", "program"}:
        raise ListError("the close list has an unknown top-level key")
    rows = data.get("program", [])
    if not isinstance(rows, list) or len(rows) > MAX_ENTRIES:
        raise ListError("the close list has no more than %d programs" % MAX_ENTRIES)
    seen, entries = set(), []
    for row in rows:
        if not isinstance(row, dict) or set(row) - {"id", "name", "images", "force", "grace", "last"}:
            raise ListError("a program entry has an unknown key")
        pid, name, images = row.get("id"), row.get("name"), row.get("images")
        if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", pid) or pid in seen:
            raise ListError("a program id must be unique, lower case letters, digits and hyphens")
        seen.add(pid)
        if not isinstance(name, str) or not name.strip() or len(name) > 64:
            raise ListError("%s: a name is required" % pid)
        if not isinstance(images, list) or not images or len(images) > 8 or not all(isinstance(i, str) and NAME_RE.match(i) for i in images):
            raise ListError("%s: images are plain program names, with no path, wildcard or quote" % pid)
        force, last, grace = row.get("force", False), row.get("last", False), row.get("grace", 10)
        if not isinstance(force, bool) or not isinstance(last, bool):
            raise ListError("%s: force and last are true or false" % pid)
        if isinstance(grace, bool) or not isinstance(grace, (int, float)) or not 1 <= grace <= MAX_GRACE:
            raise ListError("%s: grace is between 1 and %d seconds" % (pid, MAX_GRACE))
        entries.append(Entry(pid, name.strip(), tuple(plain(i) for i in images), force, float(grace), last))
    return sorted(entries, key=lambda e: e.last)  # stable: list order, with the `last` programs at the end


class Windows:
    """The only part that touches the machine. The logic below is written against this and tested with a stand-in."""

    def processes(self) -> List[Proc]:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=30, check=False).stdout
        procs = []
        for row in csv.reader(io.StringIO(out)):
            if len(row) >= 5 and row[1].isdigit():
                mb = int(re.sub(r"\D", "", row[4]) or 0) / 1024.0
                procs.append(Proc(int(row[1]), plain(row[0]), mb))
        return procs

    def ask_close(self, pid: int) -> None:
        subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, timeout=30, check=False)

    def force_close(self, pid: int) -> None:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30, check=False)

    def available_gb(self) -> float:
        class Status(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("avail", ctypes.c_ulonglong),
                        ("tpage", ctypes.c_ulonglong), ("apage", ctypes.c_ulonglong), ("tvirt", ctypes.c_ulonglong),
                        ("avirt", ctypes.c_ulonglong), ("ext", ctypes.c_ulonglong)]
        status = Status()
        status.length = ctypes.sizeof(Status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return status.avail / 1024.0 ** 3

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def matching(procs: List[Proc], entry: Entry) -> List[Proc]:
    return [p for p in procs if p.image in entry.images and p.pid != os.getpid()]


def run(entries: List[Entry], system, apply: bool, say: Callable[[str], None] = print) -> Tuple[List[Result], Optional[float], Optional[float]]:
    results: List[Result] = []
    before = system.available_gb()
    for entry in entries:
        if set(entry.images) & PROTECTED:
            results.append(Result(entry.id, entry.name, "refused (never touched)", 0, 0.0))
            say("  %-14s refused: %s is on the never-touch list" % (entry.name, ", ".join(sorted(set(entry.images) & PROTECTED))))
            continue
        found = matching(system.processes(), entry)
        mb = sum(p.mb for p in found)
        if not found:
            results.append(Result(entry.id, entry.name, "not running", 0, 0.0))
            say("  %-14s not running" % entry.name)
            continue
        if not apply:
            results.append(Result(entry.id, entry.name, "would close", len(found), mb))
            say("  %-14s would close %d process(es), about %.0f MB%s" % (entry.name, len(found), mb, " (by force if it will not close)" if entry.force else ""))
            continue
        pids = [p.pid for p in found]
        for pid in pids:
            system.ask_close(pid)
        status = _wait_gone(system, pids, entry.grace)
        if status:
            how = "closed"
        elif entry.force:
            for pid in [p.pid for p in matching(system.processes(), entry)]:
                system.force_close(pid)
            how = "closed by force" if _wait_gone(system, pids, 5.0) else "left open (still running)"
        else:
            how = "left open (still running)"
        results.append(Result(entry.id, entry.name, how, len(found), mb))
        say("  %-14s %s (%d process(es), about %.0f MB)" % (entry.name, how, len(found), mb))
    after = None
    if apply:
        system.sleep(SETTLE_SECONDS)  # let Windows reclaim the memory before it is measured
        after = system.available_gb()
    return results, before, after


def _wait_gone(system, pids: List[int], seconds: float) -> bool:
    waited = 0.0
    while True:
        alive = {p.pid for p in system.processes()}
        if not alive & set(pids):
            return True
        if waited >= seconds:
            return False
        system.sleep(1.0)
        waited += 1.0


def default_list() -> str:
    return os.path.join(os.environ.get("JARVIS_GOVERNANCE", r"D:\JARVIS\governance"), "close_list.toml")


def main(argv=None, system=None) -> int:
    ap = argparse.ArgumentParser(prog="free_memory", description="Close the programs on RK's close list to free memory before JARVIS runs.")
    ap.add_argument("--list", default=default_list(), help="the close list (default: close_list.toml in the governance folder)")
    ap.add_argument("--apply", action="store_true", help="close the programs; without it this only shows what it would close")
    ap.add_argument("--log", help="append a one-line record of the run here (default: free_memory.log in the folder above the governance folder)")
    args = ap.parse_args(argv)
    system = system or Windows()
    try:
        entries = load_list(args.list)
    except ListError as exc:
        print("free memory: %s. Nothing was closed." % exc)
        return 2
    print("free memory (%s): %d program(s) on the list" % ("closing" if args.apply else "dry run, nothing will be closed", len(entries)))
    started = time.monotonic()
    results, before, after = run(entries, system, args.apply)
    if args.apply:
        freed = after - before
        print("available memory: %.1f GB before, %.1f GB after (%+.1f GB, measured). Took %.0f s." % (before, after, freed, time.monotonic() - started))
    else:
        print("available memory now: %.1f GB. Run with --apply (or use start-jarvis.cmd) to close them." % before)
    log = args.log or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(args.list))), "free_memory.log")
    try:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "apply": args.apply, "before_gb": round(before, 2),
                                 "after_gb": None if after is None else round(after, 2),
                                 "results": [dict(r._asdict()) for r in results]}) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
