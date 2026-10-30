"""Relayed worker results: untrusted data (ADR-0010 D5, Beta plan BR-4).

RK relays a result from a worker JARVIS never ran. It is stored exactly as received,
labelled UNTRUSTED, and described in the audit chain by path, size and SHA-256 only.
The fact that RK relayed it is MEDIATED; its claims are REPORTED (ADR-0005 D8). It is
never OBSERVED.

A result is data and nothing else. No module that plans, evaluates, constrains,
authorizes or builds a brief imports this one, a result never changes a task's state,
and `VERIFIED` stays unreachable. Whatever it says, it has no effect.

Files: `<data_root>/results/<task_id>-<audit seq>.txt`, the received bytes verbatim.
"""

import hashlib
import os
import stat
from dataclasses import dataclass
from typing import List, Optional

from . import authorize, canonicalizer, reading
from . import policy as policy_mod
from .model import PolicyFailure, TargetFailure
from .reasons import TargetClass, Verdict
from .tasks import REPO_ROOT, TaskInputError, validate_id

RESULTS_DIR = "results"
EVENT = "RESULT_RECORDED"
MAX_RESULT_BYTES = 256 * 1024
LABEL = "UNTRUSTED, NOT VERIFIED"


class ResultError(ValueError):
    """Carries a fixed code, never a value."""

    def __init__(self, code: str, reason: Optional[str] = None):
        super().__init__(code)
        self.code = code
        self.reason = reason


@dataclass(frozen=True)
class ResultRef:
    seq: int
    task: str
    project: str
    recorded: str
    path: str
    size: int
    sha256: str
    source: str


def validate_bytes(data: bytes) -> bytes:
    if not data.strip():
        raise ResultError("RESULT_EMPTY")
    if len(data) > MAX_RESULT_BYTES:
        raise ResultError("RESULT_TOO_LARGE")
    if b"\x00" in data:
        raise ResultError("RESULT_BINARY")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise ResultError("RESULT_NOT_UTF8") from None
    return data


def read_source_file(cfg, policy_path: str, raw: str):
    """Read a file RK names as the result. Returns (bytes, source label).

    The file must be a regular text file that is not in the governance zone, the data
    root, the JARVIS tree or a user-secret location, and must not have a secret-looking
    name. Larger than the cap is refused, not truncated."""
    loaded = policy_mod.load(policy_path)
    secrets = () if isinstance(loaded, PolicyFailure) else loaded.secret_locations
    if isinstance(loaded, PolicyFailure):
        raise ResultError("RESULT_SOURCE_NOT_ALLOWED", loaded.reason)
    roots = canonicalizer.build_roots(cfg.governance_zone, cfg.data_root, REPO_ROOT,
                                      cfg.user_home, secrets)
    target = canonicalizer.canonicalize_path(raw, roots)
    if isinstance(target, TargetFailure):
        raise ResultError("RESULT_SOURCE_UNREADABLE", target.reason)
    if target.target_class not in (TargetClass.UNCLASSIFIED, TargetClass.PROJECT_PATH):
        raise ResultError("RESULT_SOURCE_NOT_ALLOWED", target.target_class.value)
    if reading.secret_like(os.path.basename(target.value)):
        raise ResultError("RESULT_SOURCE_SECRET_LIKE")
    try:
        if not stat.S_ISREG(os.stat(target.value).st_mode):
            raise ResultError("RESULT_SOURCE_UNREADABLE", "NOT_REGULAR")
        with open(target.value, "rb") as fh:
            data = fh.read(MAX_RESULT_BYTES + 1)
    except OSError:
        raise ResultError("RESULT_SOURCE_UNREADABLE", "IO_ERROR") from None
    return validate_bytes(data), "file:%s" % target.value


def add(store, cfg, policy_path: str, now_utc: str, actor: str, task_id: str,
        data: bytes, source: str) -> ResultRef:
    try:
        validate_id(task_id, "RESULT_TASK_INVALID")
    except TaskInputError:
        raise ResultError("RESULT_TASK_INVALID") from None
    task = store.get_task(task_id)
    if task is None:
        raise ResultError("RESULT_TASK_UNKNOWN")
    if task["state"] == "CANCELLED":
        raise ResultError("RESULT_TASK_CANCELLED")
    validate_bytes(data)
    decision = authorize.decide(store, cfg, policy_path, "RECORD_RESULT", "task", task_id, now_utc)
    if decision.verdict is not Verdict.ALLOW:
        raise ResultError("RESULT_NOT_ALLOWED", "%s %s" % (decision.verdict.value, decision.reason))

    folder = os.path.join(cfg.data_root, RESULTS_DIR)
    written = {}

    def write_file(seq: int) -> dict:
        path = os.path.join(folder, "%s-%d.txt" % (task_id, seq))
        os.makedirs(folder, exist_ok=True)
        temp = path + ".tmp"
        with open(temp, "wb") as fh:
            fh.write(data)
        os.replace(temp, path)
        written.update(path=path, sha256=hashlib.sha256(data).hexdigest())
        return {"kind": "result", "task": task_id, "path": path, "size": len(data),
                "sha256": written["sha256"], "source": source, "relayed_by": "RK_RELAYED",
                "label": LABEL, "claims_provenance": "REPORTED"}

    seq = store.record_document(EVENT, now_utc, actor, write_file, {
        "project": task["project"], "task_id": task_id, "tools_used": ["RECORD_RESULT"],
        "risk_level": decision.risk_level.value})
    return ResultRef(seq, task_id, task["project"], now_utc, written["path"], len(data),
                     written["sha256"], source)


def _ref(record: dict) -> ResultRef:
    d = record["detail"]
    return ResultRef(record["seq"], d["task"], record["project"], record["timestamp"],
                     d["path"], d["size"], d["sha256"], d["source"])


def list_results(store, task: Optional[str] = None) -> List[ResultRef]:
    refs = [_ref(r) for r in store.records_of(EVENT)]
    return [r for r in refs if task is None or r.task == task]


def check(ref: ResultRef, data_root: str) -> Optional[str]:
    root = os.path.normcase(os.path.abspath(os.path.join(data_root, RESULTS_DIR)))
    path = os.path.normcase(os.path.abspath(ref.path))
    if os.path.commonpath([root, path]) != root:
        return "RESULT_FILE_CHANGED"
    try:
        with open(ref.path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return "RESULT_FILE_MISSING"
    if hashlib.sha256(raw).hexdigest() != ref.sha256 or len(raw) != ref.size:
        return "RESULT_FILE_CHANGED"
    return None


def read(store, data_root: str, seq: int):
    """Return (ResultRef, text) after checking the file against the chain."""
    ref = next((r for r in list_results(store) if r.seq == seq), None)
    if ref is None:
        raise ResultError("RESULT_UNKNOWN")
    problem = check(ref, data_root)
    if problem:
        raise ResultError(problem)
    with open(ref.path, "rb") as fh:
        return ref, fh.read().decode("utf-8")


def audit_files(store, data_root: str) -> List[str]:
    problems, known = [], set()
    for ref in list_results(store):
        known.add(os.path.normcase(os.path.abspath(ref.path)))
        found = check(ref, data_root)
        if found:
            problems.append("%s #%d" % (found, ref.seq))
    folder = os.path.join(data_root, RESULTS_DIR)
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if os.path.normcase(os.path.abspath(os.path.join(folder, name))) not in known:
                problems.append("RESULT_FILE_UNRECORDED %s" % name)
    return problems
