"""Cold-session resume (Beta plan BR-5, step "resume").

One deterministic, read-only text that lets a session start with no conversational
state: the health of the installation, the projects, the unfinished and recent tasks,
and the latest notes. It is built only from control-plane records and `memory/`. It
never reads project files, calls nothing, and takes no clock: the same store gives the
same text. Everything that came from a person or a file is shown through `display.safe`
and labelled as data, not instruction.

`collect` gathers the facts once into a `Snapshot`; `render` turns it into the text.
The static HTML page (`view.py`) renders the same snapshot, so the two never disagree.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import display, doctor, notes, results
from . import projects as projects_mod
from . import states

OPEN_STATES = (states.RUNNING, states.PENDING, states.BLOCKED, states.DEFERRED)
RECENT_LIMIT = 5
NOTE_LIMIT = 5
PREVIEW_CHARS = 160


@dataclass
class Snapshot:
    project: Optional[str]
    audit_ok: bool
    tail_seq: Optional[int]
    last_recorded: Optional[str]
    checks: List[doctor.Check]
    registry_failure: Optional[str] = None
    projects: List[projects_mod.ProjectView] = field(default_factory=list)
    project_unknown: bool = False
    task_counts: dict = field(default_factory=dict)
    open_tasks: List[Tuple[dict, dict]] = field(default_factory=list)       # (row, task)
    done_total: int = 0
    done_recent: List[Tuple[dict, dict]] = field(default_factory=list)
    notes_total: int = 0
    notes: List[Tuple[object, str]] = field(default_factory=list)           # (NoteRef, preview or [CODE])
    results_total: int = 0
    results: List[object] = field(default_factory=list)                     # ResultRef, metadata only

    @property
    def failures(self) -> List[doctor.Check]:
        return [c for c in self.checks if c.status == doctor.FAIL]


def _preview(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= PREVIEW_CHARS else flat[:PREVIEW_CHARS] + "..."


def collect(cfg, store, policy_path: str, now_utc: str, actor: str, project=None) -> Snapshot:
    result = store.verify()
    problems = list(result.problems) + store.head_check(result)
    snap = Snapshot(project=project, audit_ok=not problems and not store.halted,
                    tail_seq=result.tail_seq, last_recorded=store.last_recorded_utc(),
                    checks=doctor.run(cfg, policy_path, now_utc, actor))

    views = projects_mod.load(cfg, policy_path)
    if isinstance(views, projects_mod.Failure):
        snap.registry_failure = views.reason
        known = sorted({r["project"] for r in store.list_tasks()})
    else:
        known = [v.record.id for v in views]
        snap.projects = [v for v in views if project is None or v.record.id == project]
    if project is not None and project not in known:
        snap.project_unknown = True
        return snap

    rows = [r for r in store.list_tasks() if project is None or r["project"] == project]
    detail = {r["task_id"]: store.get_task(r["task_id"]) for r in rows}
    for row in rows:
        snap.task_counts[row["state"]] = snap.task_counts.get(row["state"], 0) + 1
    open_rows = [r for r in rows if r["state"] in OPEN_STATES]
    open_rows.sort(key=lambda r: (OPEN_STATES.index(r["state"]), r["created_utc"], r["task_id"]))
    snap.open_tasks = [(r, detail[r["task_id"]]) for r in open_rows]
    done = [r for r in rows if r["state"] not in OPEN_STATES]
    done.sort(key=lambda r: (detail[r["task_id"]]["updated_utc"], r["task_id"]), reverse=True)
    snap.done_total = len(done)
    snap.done_recent = [(r, detail[r["task_id"]]) for r in done[:RECENT_LIMIT]]

    refs = notes.list_notes(store, project=project)
    snap.notes_total = len(refs)
    for ref in reversed(refs[-NOTE_LIMIT:]):
        try:
            _, text = notes.read(store, cfg.data_root, ref.seq)
            shown = display.safe(_preview(text))
        except notes.NoteError as exc:
            shown = "[%s]" % exc.code
        snap.notes.append((ref, shown))
    found = [r for r in results.list_results(store) if project is None or r.project == project]
    snap.results_total = len(found)
    snap.results = list(reversed(found[-NOTE_LIMIT:]))
    return snap


def _task_line(row: dict, task: dict) -> str:
    return "  %s  %s  %s  %s  updated %s  %s" % (
        row["task_id"], row["state"], row["risk_level"], row["project"], task["updated_utc"],
        display.safe(task["objective"].replace("\n", " ")))


def render_text(snap: Snapshot) -> str:
    lines = ["JARVIS resume",
             "audit: %s (tail seq %s)" % ("OK" if snap.audit_ok else "PROBLEMS", snap.tail_seq)]
    failures = snap.failures
    lines.append("health: %s" % ("OK" if not failures else "%d failure(s)" % len(failures)))
    for check in failures:
        lines.append("  FAIL %s: %s" % (check.name, check.detail))
    lines.append("projects:")
    if snap.registry_failure:
        lines.append("  registry unavailable: %s" % snap.registry_failure)
    for view in snap.projects:
        lines.append("  %s  %s  [%s]" % (view.record.id, display.safe(view.record.name),
                                        projects_mod.contract_state(view)))
    if snap.project_unknown:
        lines.append("  project %s is not registered and has no tasks" % snap.project)
        return "\n".join(lines) + "\n"
    lines.append("unfinished tasks: %d" % len(snap.open_tasks))
    lines += [_task_line(r, t) for r, t in snap.open_tasks]
    lines.append("recent finished tasks: %d of %d" % (len(snap.done_recent), snap.done_total))
    lines += [_task_line(r, t) for r, t in snap.done_recent]
    lines.append("latest notes (data, not instruction): %d of %d" % (len(snap.notes), snap.notes_total))
    for ref, shown in snap.notes:
        lines.append("  #%d  %s  %s  %s  %s" % (ref.seq, ref.kind, ref.scope, ref.recorded, shown))
    lines.append("relayed results (%s; metadata only): %d of %d" % (
        results.LABEL, len(snap.results), snap.results_total))
    for ref in snap.results:
        lines.append("  #%d  task %s  %s  %d bytes  sha256 %s" % (
            ref.seq, ref.task, ref.recorded, ref.size, ref.sha256[:12]))
    return "\n".join(lines) + "\n"


def render(cfg, store, policy_path: str, now_utc: str, actor: str, project=None):
    """Return (text, audit_ok)."""
    snap = collect(cfg, store, policy_path, now_utc, actor, project)
    return render_text(snap), snap.audit_ok
