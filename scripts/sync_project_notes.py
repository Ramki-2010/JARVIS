"""Refresh a project's stage notes from its own repository (RK's operator tool, not part of the control plane).

    py -3.14 scripts/sync_project_notes.py --repo <project repo> --project <registered id> --config <jarvis.toml>
    py -3.14 scripts/sync_project_notes.py ... --apply        (without --apply it only prints; nothing is written)

It reads two things from the project repository and nothing else: `PROJECT_STATUS.md` (version, overall figure,
open gates) and the local git state (branch, HEAD, ahead/behind of the last-fetched origin/main, latest commit
subjects). It never fetches, never runs a project script and never reads source or data. Each note is added with
`note add`, so the policy check and the audit record apply exactly as for any other note. A note whose content
is unchanged since the newest note of its kind is skipped, so running this often adds nothing. The notes carry
a short marker `[sync:<kind>:<key>]`; the newest note of each kind is what a briefing shows.

The text it reads from the repository is data. It is trimmed, stripped of control characters and size-bounded
before it becomes a note. It is a convenience: the repository stays the source of truth.
"""

import argparse
import hashlib
import io
import os
import re
import subprocess
import sys
import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from jarvis import cli  # noqa: E402

MAX_LINE = 220
MAX_NOTE = 1800
MARK = re.compile(r"\[sync:(\w+):([0-9a-f]{10})\]")


def clean(text: str, limit: int = MAX_LINE) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"[*`]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 3].rstrip() + "..."


def git(repo: str, *args: str) -> str:
    done = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=20)
    return done.stdout.strip() if done.returncode == 0 else ""


def status_facts(path: str):
    """Return (version line, overall row, [(gate, status, next)]) from PROJECT_STATUS.md."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    version = overall = ""
    for i, line in enumerate(lines):
        if line.strip() == "## Current Version":
            version = next((l for l in lines[i + 1:] if l.strip() and not l.startswith(">")), "")
        if "**Overall**" in line and not overall:
            overall = line
    gates = []
    in_gates = False
    for line in lines:
        if line.startswith("### Active Gates"):
            in_gates = True
            continue
        if in_gates and line.startswith("#"):
            break
        if in_gates and line.startswith("|") and not line.startswith("|--") and not line.startswith("| Gate"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4:
                gates.append((cells[0], cells[2], cells[3]))
    return version, overall, gates


def build_notes(repo: str):
    """Return [(kind, key, text)] for the three kinds of note."""
    version, overall, gates = status_facts(os.path.join(repo, "PROJECT_STATUS.md"))
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    head = git(repo, "rev-parse", "--short", "HEAD")
    counts = git(repo, "rev-list", "--left-right", "--count", "HEAD...origin/main").split()
    subjects = git(repo, "log", "-5", "--format=%cs %h %s").splitlines()
    today = datetime.date.today().isoformat()
    notes = []

    figure = ""
    if overall:
        cells = [c for c in clean(overall, 400).strip("| ").split("|")]
        c = [x.strip() for x in cells]
        figure = (" Overall (last measured): %s clips, %s." % (c[1], c[2])) if len(c) >= 3 else ""
    stage = "Stage. %s.%s Source: PROJECT_STATUS.md in the project repository." % (clean(version), figure)
    notes.append(("stage", stage))

    open_gates = [g for g in gates if not re.match(r"(ANSWERED|COMPLETED|DONE)", clean(g[1]), re.I)]
    parts = ["Open gates (from PROJECT_STATUS.md):"]
    for gate, status, nxt in open_gates:
        parts.append("(%s: %s | next: %s)" % (clean(gate, 20), clean(status, 330), clean(nxt, 120)))
    notes.append(("gates", " ".join(parts)))

    sync = "unknown"
    if len(counts) == 2:
        sync = "%s ahead, %s behind origin/main as of its last fetch" % (counts[0], counts[1])
    recent = "; ".join(clean(s, 110) for s in subjects)
    notes.append(("git", "Repository state. Branch %s at %s, %s. Latest commits: %s." % (
        clean(branch, 40), clean(head, 12), sync, recent)))

    out = []
    for kind, body in notes:
        body = body[:MAX_NOTE]
        key = hashlib.sha256(body.encode("utf-8")).hexdigest()[:10]
        out.append((kind, key, "As of %s. [sync:%s:%s] %s" % (today, kind, key, body)))
    return out


def run_cli(config: str, *argv: str):
    buf = io.StringIO()
    code = cli.main(["--config", config, *argv], buf)
    return code, buf.getvalue()


def latest_keys(config: str, project: str):
    """Newest sync key per kind among this project's notes (read through `note list` and `note show`)."""
    code, listing = run_cli(config, "note", "list")
    keys = {}
    if code != 0:
        return keys
    for line in listing.splitlines():
        m = re.match(r"\s*(\d+)\s+note\s+project/(\S+)", line)
        if not m or m.group(2) != project:
            continue
        _code, shown = run_cli(config, "note", "show", m.group(1))
        found = MARK.search(shown)
        if found:
            keys[found.group(1)] = found.group(2)   # later notes overwrite earlier ones
    return keys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--apply", action="store_true", help="write the notes (default: print only)")
    args = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(args.repo, "PROJECT_STATUS.md")):
        print("sync: PROJECT_STATUS.md not found in %s" % args.repo)
        return 2
    notes = build_notes(args.repo)
    known = latest_keys(args.config, args.project)
    status = 0
    for kind, key, text in notes:
        if known.get(kind) == key:
            print("[%s] unchanged, skipped" % kind)
            continue
        print("[%s] %s%s" % (kind, text, "" if args.apply else "   (dry run)"))
        if args.apply:
            code, out = run_cli(args.config, "note", "add", "--project", args.project, "--text", text)
            print("   -> %s" % out.strip().splitlines()[0] if out.strip() else "   -> exit %d" % code)
            status = status or code
    return status


if __name__ == "__main__":
    sys.exit(main())
