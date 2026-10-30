"""TEST ONLY. Startup module for `python -m jarvis` children started by tests/harness.py.

The harness puts this directory on the child's module search path, so Python
imports this module at start-up, before product code runs. Product code
contains no test hook (ADR-0002 D5, "Test process structure"). It does three
things, each switched on by a harness-set environment variable:

- JARVIS_TEST_GUARD_MARKER: install the runtime audit-hook guard (X-13b).
- JARVIS_TEST_ENV_DUMP: write the NAMES of the child's environment variables (never
  their values) to a file, so a test can check what the harness passed on.
- JARVIS_TEST_SYNC_DIR: before the first BEGIN IMMEDIATE, signal "ready" and wait
  for the harness to say "go", so that several children contend for the write
  lock at the same moment (X-05).
- JARVIS_TEST_CRASH=before_commit|after_commit: end the child at once, with no
  cleanup, at the first COMMIT (X-06). Python's own audit events cover SQLite
  only at connect, so the hook wraps the connection that product code opens.

Product code never reads these variables (test C3 and the static scan).
"""

import os
import sys
import time

if os.environ.get("JARVIS_TEST_CHILD") == "1":
    import childguard

    _dump = os.environ.get("JARVIS_TEST_ENV_DUMP")
    if _dump:
        with open(_dump, "w", encoding="utf-8", newline="\n") as _fh:
            _fh.write("\n".join(sorted(os.environ.keys())) + "\n")

    _marker = os.environ.get("JARVIS_TEST_GUARD_MARKER") or None
    if _marker:
        childguard.install(_marker)

    _selftest = os.environ.get("JARVIS_TEST_GUARD_SELFTEST")
    if _selftest and _marker:
        # Do the forbidden thing on purpose. The guard must end this process.
        if _selftest == "socket":
            import socket
            socket.socket()
        elif _selftest == "process":
            # A real process-creating call is not allowed anywhere in tests/ (static
            # check), so raise the audit event that such a call would raise.
            sys.audit("subprocess.Popen", "probe", ["probe"], None, None)
        elif _selftest == "ctypes":
            import ctypes  # noqa: F401
        elif _selftest == "nonstdlib":
            import probe_nonstdlib  # noqa: F401
        sys.stderr.write("SELFTEST NOT CAUGHT: %s\n" % _selftest)
        os._exit(0)

    _crash = os.environ.get("JARVIS_TEST_CRASH", "")
    _sync = os.environ.get("JARVIS_TEST_SYNC_DIR", "")
    if _crash or _sync:
        import sqlite3

        _state = {"synced": False}

        def _sync_point():
            _state["synced"] = True
            open(os.path.join(_sync, "ready.%d" % os.getpid()), "w").close()
            go = os.path.join(_sync, "go")
            deadline = time.monotonic() + 30.0
            while not os.path.exists(go):
                if time.monotonic() > deadline:
                    os._exit(childguard.SYNC_TIMEOUT_EXIT)
                time.sleep(0.005)

        class _TestConnection(sqlite3.Connection):
            def execute(self, sql, *args):
                text = sql.strip().upper() if isinstance(sql, str) else ""
                if _sync and text == "BEGIN IMMEDIATE" and not _state["synced"]:
                    _sync_point()
                if _crash and text == "COMMIT":
                    if _crash == "before_commit":
                        os._exit(childguard.CRASH_EXIT)
                    result = super().execute(sql, *args)
                    os._exit(childguard.CRASH_EXIT)  # after_commit
                    return result
                return super().execute(sql, *args)

        _real_connect = sqlite3.connect

        def _connect(*args, **kwargs):
            kwargs.setdefault("factory", _TestConnection)
            return _real_connect(*args, **kwargs)

        sqlite3.connect = _connect
