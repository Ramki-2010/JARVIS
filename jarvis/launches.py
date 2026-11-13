"""Authorise and record a local launch (ADR-0015 D5). The control plane never starts the program.

`launch authorize <kind> <catalog-id>` asks the policy whether LAUNCH_LOCAL is allowed for the kind and writes an audit record
either way. `launch record <kind> <catalog-id> ...` writes what the launcher reported: the kind, the catalog id, the result and,
for a file, only its extension and a short hash of its path. A file name is never recorded (a movie title is personal).
This module opens no socket and starts no process (ADR-0006).
"""

import re
from typing import Optional

from . import authorize
from .reasons import Verdict

CAPABILITY = "LAUNCH_LOCAL"
KINDS = ("app", "folder", "file", "game")
RESULTS = ("ok", "refused", "failed")
AUTHORIZED, REFUSED, RECORDED = "LAUNCH_AUTHORIZED", "LAUNCH_REFUSED", "LAUNCH_RECORDED"
_ID = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
_EXT = re.compile(r"^\.[a-z0-9]{1,8}$")
_HASH = re.compile(r"^[0-9a-f]{8}$")


class LaunchError(ValueError):
    """Carries a fixed code, never a value."""

    def __init__(self, code: str, reason: Optional[str] = None):
        super().__init__(code)
        self.code = code
        self.reason = reason


def _kind(kind) -> str:
    if kind not in KINDS:
        raise LaunchError("LAUNCH_KIND_UNKNOWN")
    return kind


def _ident(ident) -> str:
    # a file is not named by a catalog id: it is recorded as "file" with its extension and path hash
    if not (isinstance(ident, str) and _ID.match(ident)):
        raise LaunchError("LAUNCH_ID_INVALID")
    return ident


def authorize_launch(store, cfg, policy_path: str, now_utc: str, actor: str, kind: str, ident: str) -> int:
    """Return the audit sequence of LAUNCH_AUTHORIZED, or raise LAUNCH_NOT_ALLOWED after recording the refusal."""
    kind, ident = _kind(kind), _ident(ident)
    decision = authorize.decide(store, cfg, policy_path, CAPABILITY, "launch", kind, now_utc)
    fields = {"project": "", "tools_used": [CAPABILITY], "risk_level": decision.risk_level.value,
              "objective": "open %s %s" % (kind, ident)}
    if decision.verdict is not Verdict.ALLOW:
        store.record_event(REFUSED, now_utc, actor, dict(fields, final_status="%s %s" % (decision.verdict.value, decision.reason)))
        raise LaunchError("LAUNCH_NOT_ALLOWED", "%s %s" % (decision.verdict.value, decision.reason))
    return store.record_event(AUTHORIZED, now_utc, actor, fields)


def record_launch(store, now_utc: str, actor: str, kind: str, ident: str, result: str, ext: str, path_hash: str) -> int:
    kind, ident = _kind(kind), _ident(ident)
    if result not in RESULTS:
        raise LaunchError("LAUNCH_RESULT_INVALID")
    if not (isinstance(ext, str) and (ext == "" or _EXT.match(ext))) or not (isinstance(path_hash, str) and (path_hash == "" or _HASH.match(path_hash))):
        raise LaunchError("LAUNCH_DETAIL_INVALID")
    if kind != "file" and (ext or path_hash):
        raise LaunchError("LAUNCH_DETAIL_INVALID")
    detail = {"kind": kind, "id": ident, "result": result}
    if kind == "file":
        detail.update(ext=ext, path_hash=path_hash)
    return store.record_event(RECORDED, now_utc, actor, {
        "project": "", "tools_used": [CAPABILITY], "risk_level": "L2", "objective": "open %s %s" % (kind, ident),
        "final_status": result, "detail": detail})
