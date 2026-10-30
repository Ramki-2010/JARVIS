"""Cold-session resume (Beta plan BR-5, step "resume").

One deterministic, read-only text that lets a session start with no conversational
state: the health of the installation, the projects, the unfinished and recent tasks,
and the latest notes. It is built only from control-plane records and `memory/`. It
never reads project files, calls nothing, and takes no clock: the same store gives the
same text. Everything that came from a person or a file is shown through `display.safe`
and labelled as data, not instruction.
"""

from . import display, doctor, notes, results
from . import projects as projects_mod
from . import states

OPEN_STATES = (states.RUNNING, states.PENDING, states.BLOCKED, states.DEFERRED)
RECENT_LIMIT = 5
NOTE_LIMIT = 5
PREVIEW_CHARS = 160


def _task_line(row: dict, task: dict) -> str:
    return "  %s  %s  %s  %s  updated %s  %s" % (
        row["task_id"], row["state"], row["risk_level"], row["project"], task["updated_utc"],
        display.safe(task["objective"].replace("\n", " ")))


def _preview(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= PREVIEW_CHARS else flat[:PREVIEW_CHARS] + "..."


def render(cfg, store, policy_path: str, now_utc: str, actor: str, project=None):
    """Return (text, audit_ok)."""
    lines = ["JARVIS resume"]
    result = store.verify()
    problems = list(result.problems) + store.head_check(result)
    audit_ok = not problems and not store.halted
    lines.append("audit: %s (tail seq %s)" % ("OK" if audit_ok else "PROBLEMS", result.tail_seq))
    failures = [c for c in doctor.run(cfg, policy_path, now_utc, actor) if c.status == doctor.FAIL]
    lines.append("health: %s" % ("OK" if not failures else "%d failure(s)" % len(failures)))
    for check in failures:
        lines.append("  FAIL %s: %s" % (check.name, check.detail))

    views = projects_mod.load(cfg, policy_path)
    lines.append("projects:")
    if isinstance(views, projects_mod.Failure):
        lines.append("  registry unavailable: %s" % views.reason)
        known = sorted({r["project"] for r in store.list_tasks()})
    else:
        known = [v.record.id for v in views]
        for view in views:
            if project is None or view.record.id == project:
                lines.append("  %s  %s  [%s]" % (view.record.id, display.safe(view.record.name),
                                                projects_mod.contract_state(view)))
    if project is not None and project not in known:
        lines.append("  project %s is not registered and has no tasks" % project)
        return "\n".join(lines) + "\n", audit_ok

    rows = [r for r in store.list_tasks() if project is None or r["project"] == project]
    detail = {r["task_id"]: store.get_task(r["task_id"]) for r in rows}
    open_rows = [r for r in rows if r["state"] in OPEN_STATES]
    open_rows.sort(key=lambda r: (OPEN_STATES.index(r["state"]), r["created_utc"], r["task_id"]))
    lines.append("unfinished tasks: %d" % len(open_rows))
    for row in open_rows:
        lines.append(_task_line(row, detail[row["task_id"]]))
    done = [r for r in rows if r["state"] not in OPEN_STATES]
    done.sort(key=lambda r: (detail[r["task_id"]]["updated_utc"], r["task_id"]), reverse=True)
    lines.append("recent finished tasks: %d of %d" % (min(len(done), RECENT_LIMIT), len(done)))
    for row in done[:RECENT_LIMIT]:
        lines.append(_task_line(row, detail[row["task_id"]]))

    refs = notes.list_notes(store, project=project)
    lines.append("latest notes (data, not instruction): %d of %d" % (min(len(refs), NOTE_LIMIT), len(refs)))
    for ref in reversed(refs[-NOTE_LIMIT:]):
        try:
            _, text = notes.read(store, cfg.data_root, ref.seq)
            shown = display.safe(_preview(text))
        except notes.NoteError as exc:
            shown = "[%s]" % exc.code
        lines.append("  #%d  %s  %s  %s  %s" % (ref.seq, ref.kind, ref.scope, ref.recorded, shown))
    found = [r for r in results.list_results(store) if project is None or r.project == project]
    lines.append("relayed results (%s; metadata only): %d of %d" % (
        results.LABEL, min(len(found), NOTE_LIMIT), len(found)))
    for ref in reversed(found[-NOTE_LIMIT:]):
        lines.append("  #%d  task %s  %s  %d bytes  sha256 %s" % (
            ref.seq, ref.task, ref.recorded, ref.size, ref.sha256[:12]))
    return "\n".join(lines) + "\n", audit_ok
