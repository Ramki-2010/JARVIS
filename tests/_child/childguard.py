"""TEST ONLY. Decision logic for the runtime guard in `python -m jarvis` children.

X-13b (ADR-0002 D5, ADR-0006 6.1). This module lives under tests/ and is never
imported by product code. It is a detection aid, not an isolation boundary: a
process that wants to evade an audit hook can. It catches mistakes.

The decision function is pure so that it can be unit-tested in-process with
synthetic events. The sitecustomize module installs it inside each child.
"""

import os
import sys

GUARD_EXIT = 97
SYNC_TIMEOUT_EXIT = 98
CRASH_EXIT = 99

# Imports of these roots are violations even though some are standard library
# (ADR-0006 3.2). `importlib` is not listed here: the interpreter's own runner
# imports it, and the static scan of jarvis/ already forbids product use of it.
FORBIDDEN_IMPORT_ROOTS = frozenset({
    "socket", "_socket", "ssl", "_ssl", "http", "urllib", "ftplib", "smtplib", "xmlrpc",
    "asyncio", "subprocess", "_posixsubprocess", "multiprocessing", "ctypes", "_ctypes",
    "cffi", "pickle", "marshal", "shelve",
})
# Always allowed: the product package, the two test startup modules, and
# `usercustomize`, which the interpreter's own `site` module probes for right after
# `sitecustomize` (the import event fires even when the module does not exist).
ALLOWED_IMPORT_ROOTS = frozenset({"jarvis", "childguard", "sitecustomize", "usercustomize"})

FORBIDDEN_EVENT_PREFIXES = (
    "socket.", "urllib.", "http.client.", "ftplib.", "smtplib.", "ctypes.",
    "subprocess.", "multiprocessing.",
)
FORBIDDEN_EVENTS = frozenset({
    "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.forkpty",
    "os.startfile",
})


def violation(event, args):
    """Return a short reason string if the audit event is forbidden, else None."""
    if event in FORBIDDEN_EVENTS:
        return event
    for prefix in FORBIDDEN_EVENT_PREFIXES:
        if event.startswith(prefix):
            return event
    if event == "import":
        name = str(args[0]) if args else ""
        root = name.split(".")[0]
        if root in FORBIDDEN_IMPORT_ROOTS:
            return "import %s" % root
        if root in ALLOWED_IMPORT_ROOTS or not root:
            return None
        if root not in sys.stdlib_module_names and root not in sys.builtin_module_names:
            return "import %s (outside the standard library)" % root
    return None


def die(reason, marker_path=None):
    """End the process at once. os._exit cannot be caught by product code."""
    try:
        if marker_path:
            with open(marker_path, "a", encoding="utf-8") as fh:
                fh.write("VIOLATION %s\n" % reason)
        sys.stderr.write("GUARD VIOLATION: %s\n" % reason)
        sys.stderr.flush()
    finally:
        os._exit(GUARD_EXIT)


def install(marker_path=None):
    """Install the audit hook. Call once, before product code runs."""
    def hook(event, args):
        reason = violation(event, args)
        if reason:
            die(reason, marker_path)

    sys.addaudithook(hook)
    if marker_path:
        with open(marker_path, "a", encoding="utf-8") as fh:
            fh.write("INSTALLED\n")
