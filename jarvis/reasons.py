"""Closed vocabularies for evaluation (ADR-0003 D1, D9, D2).

The reason-code list is closed. An unlisted code is a bug. Adding a code is an
ADR amendment; changing which verdict a code maps to is G-03.
"""

from enum import Enum


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"


class Level(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"

    @property
    def rank(self) -> int:
        return int(self.value[1])

    @classmethod
    def from_rank(cls, rank: int) -> "Level":
        return cls("L%d" % max(0, min(5, rank)))


class TargetClass(str, Enum):
    PROJECT_ID = "PROJECT_ID"
    PROJECT_PATH = "PROJECT_PATH"
    CONTROL_PLANE_RECORD = "CONTROL_PLANE_RECORD"
    ARTIFACT = "ARTIFACT"
    COMMAND = "COMMAND"
    URL = "URL"
    GOVERNANCE_ZONE = "GOVERNANCE_ZONE"
    JARVIS_SELF = "JARVIS_SELF"
    DATA_ROOT = "DATA_ROOT"
    USER_SECRET_LOCATION = "USER_SECRET_LOCATION"
    UNCLASSIFIED = "UNCLASSIFIED"


ALWAYS_DENY_CLASSES = {
    TargetClass.GOVERNANCE_ZONE: "TARGET_GOVERNANCE_ZONE",
    TargetClass.JARVIS_SELF: "TARGET_JARVIS_SELF",
    TargetClass.DATA_ROOT: "TARGET_DATA_ROOT",
    TargetClass.USER_SECRET_LOCATION: "TARGET_USER_SECRET",
}

# Classes whose targets are scoped to a registered project and need a contract.
PROJECT_SCOPED_CLASSES = frozenset({TargetClass.PROJECT_ID, TargetClass.PROJECT_PATH})

# Classes that must carry a SHA-256 (ADR-0003 D4).
HASH_REQUIRED_CLASSES = frozenset({TargetClass.ARTIFACT, TargetClass.COMMAND})


# ADR-0003 D9, grouped by the step that may emit them. Order matters only for
# documentation; the evaluator applies the steps in sequence.
REASONS_BY_STEP = (
    (1, ("INPUT_INVALID",)),
    (2, ("POLICY_UNAVAILABLE", "POLICY_VERSION_UNKNOWN", "POLICY_HASH_MISMATCH",
         "POLICY_FORMAT_INVALID")),
    (3, ("CLOCK_SKEW",)),
    (4, ("UNKNOWN_CAPABILITY",)),
    (5, ("REVOCATION_UNAVAILABLE", "REVOKED")),
    (6, ("TARGET_RAW_INVALID", "TARGET_UNRESOLVABLE", "TARGET_CROSS_DRIVE")),
    (7, ("TARGET_GOVERNANCE_ZONE", "TARGET_JARVIS_SELF", "TARGET_DATA_ROOT",
         "TARGET_USER_SECRET", "UNKNOWN_TARGET_CLASS")),
    (8, ("UNKNOWN_PROJECT", "CONTRACT_MISSING", "CONTRACT_SCHEMA_UNKNOWN",
         "CONTRACT_INVALID")),
    (9, ("EXPIRED",)),
    (10, ("TARGET_CLASS_NOT_ALLOWED", "TARGET_OUT_OF_SCOPE", "FORBIDDEN_BY_CONTRACT",
          "CONSTRAINT_WIDENS")),
    (11, ("FORBIDDEN_L5", "NON_GOAL_V01")),
    (13, ("PHASE_NOT_ENABLED", "ISOLATION_REQUIRED", "APPROVAL_MECHANISM_ABSENT",
          "MECHANISM_NOT_IMPLEMENTED")),
    (14, ("ALLOWED_BY_POLICY",)),
)

STEP_OF_REASON = {code: step for step, codes in REASONS_BY_STEP for code in codes}
REASON_CODES = frozenset(STEP_OF_REASON)

DEFER_REASONS = frozenset(dict(REASONS_BY_STEP)[13])
ALLOW_REASONS = frozenset(dict(REASONS_BY_STEP)[14])
DENY_REASONS = REASON_CODES - DEFER_REASONS - ALLOW_REASONS


def verdict_for(reason: str) -> Verdict:
    """The verdict a reason code maps to. Raises on an unlisted code."""
    if reason not in REASON_CODES:
        raise ValueError("unlisted reason code: %r" % (reason,))
    if reason in ALLOW_REASONS:
        return Verdict.ALLOW
    if reason in DEFER_REASONS:
        return Verdict.DEFER
    return Verdict.DENY
