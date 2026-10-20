"""Task states and transitions (ADR-0002 D2).

Every transition not listed is rejected. VERIFIED is reserved and unreachable in
Phase 1. Transitions out of PENDING, DEFERRED and BLOCKED into RUNNING, BLOCKED or
DEFERRED require a fresh evaluation whose outcome matches the target state.
"""

PENDING = "PENDING"
RUNNING = "RUNNING"
BLOCKED = "BLOCKED"
DEFERRED = "DEFERRED"
COMPLETED_UNVERIFIED = "COMPLETED_UNVERIFIED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
VERIFIED = "VERIFIED"

STATES = frozenset({PENDING, RUNNING, BLOCKED, DEFERRED, COMPLETED_UNVERIFIED,
                    FAILED, CANCELLED, VERIFIED})
TERMINAL = frozenset({COMPLETED_UNVERIFIED, FAILED, CANCELLED})

# Target state required for each evaluation outcome (ADR-0003 D10).
STATE_FOR_OUTCOME = {"RUNNABLE": RUNNING, "BLOCKED": BLOCKED, "DEFERRED": DEFERRED}

_EVALUATED = frozenset({
    (PENDING, RUNNING), (PENDING, BLOCKED), (PENDING, DEFERRED),
    (DEFERRED, RUNNING), (DEFERRED, BLOCKED), (DEFERRED, DEFERRED),
    (BLOCKED, RUNNING), (BLOCKED, BLOCKED), (BLOCKED, DEFERRED),
})
_PLAIN = frozenset({
    (RUNNING, COMPLETED_UNVERIFIED), (RUNNING, FAILED),
    (PENDING, CANCELLED), (RUNNING, CANCELLED), (DEFERRED, CANCELLED), (BLOCKED, CANCELLED),
})


def is_allowed(from_state: str, to_state: str) -> bool:
    return (from_state, to_state) in _EVALUATED or (from_state, to_state) in _PLAIN


def needs_evaluation(from_state: str, to_state: str) -> bool:
    return (from_state, to_state) in _EVALUATED
