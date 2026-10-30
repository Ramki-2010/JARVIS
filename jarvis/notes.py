"""Notes: RK's typed context, kept as plain data (ADR-0010 D6, Beta plan BR-5).

A note is one append-only file under `<data_root>/memory/` named by the sequence number
of its audit record. The audit record carries the path, size and SHA-256; the text
never enters the chain. A note is data: nothing in this module, or anywhere else, feeds
a note to the planner, the evaluator, a constraint, a brief or the policy.

Layout (Master Context section 17 names; ADR-0010 D6 item 1):
    memory/projects/<project_id>/<seq>.txt     project notes
    memory/tasks/<task_id>/<seq>.txt           task notes
    memory/decisions/<project_id>/<seq>.txt    notes RK marks as decisions
"""

import hashlib
import os
from dataclasses import dataclass
from typing import List, Optional

from . import authorize, registry, tasks
from .model import PROJECT_ID_RE
from .reasons import Verdict

MEMORY_DIR = "memory"
EVENT = "NOTE_RECORDED"
MAX_NOTE_BYTES = 16 * 1024
KINDS = ("note", "decision")
AUTHOR = "RK_TYPED"
SEPARATOR = "---"


class NoteError(ValueError):
    """Carries a fixed code, never a value."""

    def __init__(self, code: str, reason: Optional[str] = None):
        super().__init__(code)
        self.code = code
        self.reason = reason


@dataclass(frozen=True)
class NoteRef:
    seq: int
    kind: str
    scope: str          # "project/<id>" or "task/<id>"
    project: str
    recorded: str
    path: str
    size: int
    sha256: str


def memory_root(data_root: str) -> str:
    return os.path.join(data_root, MEMORY_DIR)


def validate_text(text) -> bytes:
    """UTF-8 bytes of a non-empty note whose only control characters are newline and tab."""
    if not isinstance(text, str) or not text.strip():
        raise NoteError("NOTE_TEXT_INVALID")
    if not all(ch in "\n\t" or (ch >= " " and ch != "\x7f") for ch in text):
        raise NoteError("NOTE_TEXT_INVALID")
    data = text.encode("utf-8")
    if len(data) > MAX_NOTE_BYTES:
        raise NoteError("NOTE_TOO_LONG")
    return data


def _folder(kind: str, scope_type: str, scope_id: str) -> str:
    if kind == "decision":
        return os.path.join("decisions", scope_id)
    return os.path.join("projects" if scope_type == "project" else "tasks", scope_id)


def render_file(seq: int, scope: str, kind: str, recorded: str, text_bytes: bytes) -> bytes:
    head = "\n".join(("JARVIS note", "note_id: %d" % seq, "scope: %s" % scope, "kind: %s" % kind,
                      "author: %s" % AUTHOR, "recorded: %s" % recorded, SEPARATOR, ""))
    body = text_bytes if text_bytes.endswith(b"\n") else text_bytes + b"\n"
    return head.encode("utf-8") + body


def _write_atomic(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "wb") as fh:
        fh.write(data)
    os.replace(temp, path)


def add(store, cfg, policy_path: str, now_utc: str, actor: str, *, project: Optional[str],
        task: Optional[str], kind: str, text: str) -> NoteRef:
    """Record one note. Exactly one of project and task is given; a decision needs a project."""
    if (project is None) == (task is None) or kind not in KINDS:
        raise NoteError("NOTE_SCOPE_INVALID")
    if kind == "decision" and project is None:
        raise NoteError("NOTE_SCOPE_INVALID")
    text_bytes = validate_text(text)

    if task is not None:
        try:
            tasks.validate_id(task, "NOTE_SCOPE_INVALID")
        except tasks.TaskInputError:
            raise NoteError("NOTE_SCOPE_INVALID") from None
        row = store.get_task(task)
        if row is None:
            raise NoteError("NOTE_TASK_UNKNOWN")
        scope_type, scope_id, project_id = "task", task, row["project"]
    else:
        if not PROJECT_ID_RE.match(project):
            raise NoteError("NOTE_SCOPE_INVALID")
        registered = registry.load(registry.path_in(cfg.governance_zone))
        if isinstance(registered, registry.RegistryFailure):
            raise NoteError("NOTE_REGISTRY_UNAVAILABLE", registered.reason)
        if project not in {p.id for p in registered.projects}:
            raise NoteError("NOTE_PROJECT_UNKNOWN")
        scope_type, scope_id, project_id = "project", project, project

    decision = authorize.decide(store, cfg, policy_path, "RECORD_NOTE", scope_type, scope_id, now_utc)
    if decision.verdict is not Verdict.ALLOW:
        raise NoteError("NOTE_NOT_ALLOWED", "%s %s" % (decision.verdict.value, decision.reason))

    scope = "%s/%s" % (scope_type, scope_id)
    folder = os.path.join(memory_root(cfg.data_root), _folder(kind, scope_type, scope_id))
    written = {}

    def write_file(seq: int) -> dict:
        data = render_file(seq, scope, kind, now_utc, text_bytes)
        path = os.path.join(folder, "%d.txt" % seq)
        _write_atomic(path, data)
        written.update(path=path, size=len(data), sha256=hashlib.sha256(data).hexdigest())
        return {"kind": kind, "scope": scope, "path": path, "size": len(data),
                "sha256": written["sha256"], "author": AUTHOR}

    seq = store.record_document(EVENT, now_utc, actor, write_file, {
        "project": project_id, "task_id": task or "", "tools_used": ["RECORD_NOTE"],
        "risk_level": decision.risk_level.value})
    return NoteRef(seq, kind, scope, project_id, now_utc, written["path"], written["size"],
                   written["sha256"])


def _ref(record: dict) -> NoteRef:
    detail = record["detail"]
    return NoteRef(record["seq"], detail["kind"], detail["scope"], record["project"],
                   record["timestamp"], detail["path"], detail["size"], detail["sha256"])


def list_notes(store, *, project: Optional[str] = None, task: Optional[str] = None) -> List[NoteRef]:
    refs = [_ref(r) for r in store.records_of(EVENT)]
    if project is not None:
        refs = [r for r in refs if r.project == project]
    if task is not None:
        refs = [r for r in refs if r.scope == "task/%s" % task]
    return refs


def read(store, data_root: str, seq: int):
    """Return (NoteRef, text) after checking the file against the chain.
    Raises NOTE_UNKNOWN, NOTE_FILE_MISSING or NOTE_FILE_CHANGED."""
    ref = next((r for r in list_notes(store) if r.seq == seq), None)
    if ref is None:
        raise NoteError("NOTE_UNKNOWN")
    problem = check(ref, data_root)
    if problem:
        raise NoteError(problem)
    with open(ref.path, "rb") as fh:
        raw = fh.read()
    marker = (SEPARATOR + "\n").encode("utf-8")
    return ref, raw.split(marker, 1)[1].decode("utf-8")


def check(ref: NoteRef, data_root: str) -> Optional[str]:
    """None if the recorded file is present, inside memory\\ and unchanged."""
    root = os.path.normcase(os.path.abspath(memory_root(data_root)))
    path = os.path.normcase(os.path.abspath(ref.path))
    if os.path.commonpath([root, path]) != root:
        return "NOTE_FILE_CHANGED"
    try:
        with open(ref.path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return "NOTE_FILE_MISSING"
    if hashlib.sha256(raw).hexdigest() != ref.sha256 or len(raw) != ref.size:
        return "NOTE_FILE_CHANGED"
    return None


def audit_files(store, data_root: str) -> List[str]:
    """Problems between memory\\ and the chain: changed, missing or unrecorded note files."""
    problems = []
    known = set()
    for ref in list_notes(store):
        known.add(os.path.normcase(os.path.abspath(ref.path)))
        found = check(ref, data_root)
        if found:
            problems.append("%s #%d" % (found, ref.seq))
    root = memory_root(data_root)
    for folder, _dirs, files in os.walk(root):
        for name in files:
            if os.path.normcase(os.path.abspath(os.path.join(folder, name))) not in known:
                problems.append("NOTE_FILE_UNRECORDED %s" % os.path.relpath(os.path.join(folder, name), root))
    return problems
