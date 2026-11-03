"""Read-only front door to JARVIS, for a Claude Code session (or anyone) that should look but not change.

    py -3.14 scripts/jarvis_ro.py <command> [arguments]        (or scripts\\jarvis-ro.cmd)

Only the commands listed in ALLOWED run; everything else is refused with exit code 2 before
JARVIS is even started. The allowed commands write nothing of their own: they read the store,
the registry, the contracts and the notes, briefs and result metadata. (Like `audit verify`,
they may let JARVIS repair a lagging HEAD file or record a RECOVERY entry after a crash; that
is JARVIS's own start-up repair, not something this wrapper or a session chooses.)

Deliberately NOT allowed: anything that creates or changes a task, note, result, brief or
backup (`init`, `task create|evaluate|run`, `cancel`, `note add`, `result add`, `report`,
`view`), and `result show`, because the text of a relayed result is untrusted and should
not be read into a model session. `--config` and `--policy` are refused so the session cannot
point JARVIS at another install or another policy.

This is a convenience guard, not a security boundary: a session that can run shell commands
can still run `scripts\\jarvis.cmd` directly. What stops that is a Claude Code permission rule
(docs/beta/BETA_OPERATIONS.md, "Using Claude Code with JARVIS"). It runs JARVIS in-process, creates
no process and makes no connection.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from jarvis import cli  # noqa: E402

ALLOWED = (
    ("resume",), ("status",), ("doctor",), ("audit", "verify"),
    ("project", "list"), ("project", "show"),
    ("task", "list"), ("task", "show"),
    ("note", "list"), ("note", "show"),
    ("brief", "show"), ("result", "list"),
)
REFUSED_FLAGS = ("--config", "--policy")
EXIT_REFUSED = 2


def permitted(argv) -> bool:
    if not argv or argv[0].startswith("-"):
        return False
    if any(arg == flag or arg.startswith(flag + "=") for arg in argv for flag in REFUSED_FLAGS):
        return False
    return (argv[0],) in ALLOWED or tuple(argv[:2]) in ALLOWED


def main(argv=None, out=None, config=None) -> int:
    """config is a test seam only: the command line itself can never name a config file."""
    argv = list(sys.argv[1:] if argv is None else argv)
    out = out or sys.stdout
    if not permitted(argv):
        shown = " ".join(argv[:2]) if argv and not argv[0].startswith("-") else "(no command)"
        out.write("jarvis-ro: refused: '%s' is not a read-only command.\n" % shown)
        out.write("allowed: %s\n" % ", ".join(" ".join(c) for c in ALLOWED))
        out.write("To change anything, ask RK to run scripts\\jarvis.cmd themselves.\n")
        return EXIT_REFUSED
    return cli.main((["--config", config] if config else []) + argv, out)


if __name__ == "__main__":
    sys.exit(main())
