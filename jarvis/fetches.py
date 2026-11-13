"""Authorise and record a public-data lookup (ADR-0014 D5). The control plane never makes the lookup.

`fetch authorize <lookup>` asks the policy whether FETCH_PUBLIC_DATA is allowed and writes an audit record either way.
`fetch record <lookup> ...` writes what the separate fetcher program reported: the lookup name, the host names it
contacted, the result, the byte count and the duration. The place name, the keyword and every fetched word are
never recorded. This module opens no socket and starts no process (ADR-0006).
"""

import re
from typing import Optional

from . import authorize
from .reasons import Verdict

CAPABILITY = "FETCH_PUBLIC_DATA"
LOOKUPS = ("weather", "hn", "news")
RESULTS = ("ok", "partial", "refused", "failed")
AUTHORIZED, REFUSED, RECORDED = "FETCH_AUTHORIZED", "FETCH_REFUSED", "FETCH_RECORDED"
_HOSTS = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,62}[a-z0-9])?(,[a-z0-9]([a-z0-9.-]{0,62}[a-z0-9])?){0,7}$")
MAX_BYTES = 64 * 1024 * 1024
MAX_MS = 10 * 60 * 1000


class FetchError(ValueError):
    """Carries a fixed code, never a value."""

    def __init__(self, code: str, reason: Optional[str] = None):
        super().__init__(code)
        self.code = code
        self.reason = reason


def _lookup(name) -> str:
    if name not in LOOKUPS:
        raise FetchError("FETCH_LOOKUP_UNKNOWN")
    return name


def authorize_lookup(store, cfg, policy_path: str, now_utc: str, actor: str, lookup: str) -> int:
    """Return the audit sequence of the FETCH_AUTHORIZED record, or raise FETCH_NOT_ALLOWED after recording the refusal."""
    lookup = _lookup(lookup)
    decision = authorize.decide(store, cfg, policy_path, CAPABILITY, "fetch", lookup, now_utc)
    fields = {"project": "", "tools_used": [CAPABILITY], "risk_level": decision.risk_level.value,
              "objective": "lookup %s" % lookup}
    if decision.verdict is not Verdict.ALLOW:
        store.record_event(REFUSED, now_utc, actor, dict(fields, final_status="%s %s" % (decision.verdict.value, decision.reason)))
        raise FetchError("FETCH_NOT_ALLOWED", "%s %s" % (decision.verdict.value, decision.reason))
    return store.record_event(AUTHORIZED, now_utc, actor, fields)


def record_lookup(store, now_utc: str, actor: str, lookup: str, hosts: str, result: str, nbytes: int, ms: int) -> int:
    lookup = _lookup(lookup)
    if result not in RESULTS:
        raise FetchError("FETCH_RESULT_INVALID")
    if not (isinstance(hosts, str) and (hosts == "" or _HOSTS.match(hosts))):
        raise FetchError("FETCH_HOST_INVALID")
    if not (isinstance(nbytes, int) and 0 <= nbytes <= MAX_BYTES and isinstance(ms, int) and 0 <= ms <= MAX_MS):
        raise FetchError("FETCH_NUMBER_INVALID")
    detail = {"lookup": lookup, "hosts": hosts, "result": result, "bytes": nbytes, "duration_ms": ms}
    return store.record_event(RECORDED, now_utc, actor, {
        "project": "", "tools_used": [CAPABILITY], "risk_level": "L1", "objective": "lookup %s" % lookup,
        "final_status": result, "detail": detail})
