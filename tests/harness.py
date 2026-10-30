"""TEST ONLY. The one place in tests/ that starts a process (ADR-0002 D5, ADR-0006 3.2).

It starts `python -m jarvis` with the given arguments and nothing else. A static
check over tests/ (test_static_guard.HarnessGuardTests) fails if any other
process-creating call appears, or if this module has more than one call site.
This harness sits outside the product-code guard; the children it starts do not.
"""

import os
import subprocess
import sys
from dataclasses import dataclass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHILD_DIR = os.path.join(REPO, "tests", "_child")


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str
    stderr: str


def write_config(directory, data_root, governance_zone, busy_timeout_ms=30000, name="jarvis-test.toml"):
    """Write a throwaway configuration file. Temporary paths only (ADR-0007 D7)."""
    path = os.path.join(directory, name)
    lines = [
        "schema_version = 1",
        "data_root = '%s'" % data_root,
        "governance_zone = '%s'" % governance_zone,
        "user_home = 'C:\\home'",
        "busy_timeout_ms = %d" % busy_timeout_ms,
    ]
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


# Names a Windows Python child needs to start. Everything else in the parent's
# environment, including any variable that holds a credential, is not passed on.
# Compared in upper case because Windows names are case-insensitive.
CHILD_ENV_ALLOWLIST = frozenset({"SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP"})


def child_environment(parent, *, marker=None, crash=None, sync_dir=None, selftest=None,
                      env_dump=None):
    """The environment for a child: the allow-listed parent names plus the test settings.

    Pure function of its arguments, so it can be tested without starting a process.
    """
    env = {name: value for name, value in parent.items() if name.upper() in CHILD_ENV_ALLOWLIST}
    env.update({
        "PYTHONPATH": CHILD_DIR,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "JARVIS_TEST_CHILD": "1",
    })
    for key, value in (("JARVIS_TEST_GUARD_MARKER", marker), ("JARVIS_TEST_GUARD_SELFTEST", selftest),
                       ("JARVIS_TEST_CRASH", crash), ("JARVIS_TEST_SYNC_DIR", sync_dir),
                       ("JARVIS_TEST_ENV_DUMP", env_dump)):
        if value:
            env[key] = value
    return env


def spawn_jarvis(args, config_path, *, marker=None, crash=None, sync_dir=None, selftest=None,
                 env_dump=None):
    """Start `python -m jarvis --config <config> <args...>` and return the Popen.

    marker: path of the guard marker file; installs the runtime guard (X-13b).
    crash: "before_commit" or "after_commit" (X-06).
    sync_dir: directory for the start-line barrier (X-05).
    selftest: make the startup module do a forbidden thing, to prove the guard fires.
    env_dump: path where the startup module writes the child's environment NAMES
    (never values), so a test can check what the child was given.
    """
    env = child_environment(os.environ, marker=marker, crash=crash, sync_dir=sync_dir,
                            selftest=selftest, env_dump=env_dump)
    cmd = [sys.executable, "-m", "jarvis", "--config", config_path] + list(args)
    return subprocess.Popen(cmd, cwd=REPO, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8")


def finish(proc, timeout=60):
    out, err = proc.communicate(timeout=timeout)
    return Result(proc.returncode, out, err)


def run_jarvis(args, config_path, timeout=60, **kwargs):
    return finish(spawn_jarvis(args, config_path, **kwargs), timeout)
