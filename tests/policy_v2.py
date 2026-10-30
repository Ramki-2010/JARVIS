"""The policy version 2 capability matrix as test data (ADR-0010 D2).

An independent transcription, like policy_d12 for version 1: the ADR-0003 D12 table with
exactly the five changes ADR-0010 D2 lists, and nothing else. It is not the policy file;
the tests compare the policy file to it.
"""

from jarvis.model import CapabilityRule, PolicySnapshot
from jarvis.reasons import Level, TargetClass

from . import policy_d12 as d12

CPR = frozenset({TargetClass.CONTROL_PLANE_RECORD})
PP = frozenset({TargetClass.PROJECT_PATH})

#      name                     level     iso    classes phase  mech   l5     nongoal verdict  reason
CHANGED = {
    "READ_PROJECT":          ("READ_PROJECT", Level.L1, False, PP, True, True, False, False, "ALLOW", "ALLOWED_BY_POLICY"),
    "READ_FILE":             ("READ_FILE", Level.L1, False, PP, True, True, False, False, "ALLOW", "ALLOWED_BY_POLICY"),
    "GENERATE_WORKER_BRIEF": ("GENERATE_WORKER_BRIEF", Level.L2, False, CPR, True, True, False, False,
                              "ALLOW", "ALLOWED_BY_POLICY"),
}
ADDED = (
    ("RECORD_RESULT", Level.L2, False, CPR, True, True, False, False, "ALLOW", "ALLOWED_BY_POLICY"),
    ("RECORD_NOTE", Level.L2, False, CPR, True, True, False, False, "ALLOW", "ALLOWED_BY_POLICY"),
)

ROWS = tuple(CHANGED.get(row[0], row) for row in d12.ROWS) + ADDED

# Exactly what may be ALLOWed in version 2: the four Phase 1 capabilities and the five
# Beta capabilities. Each is implemented in jarvis/ and covered by tests.
BETA_ALLOW = frozenset(d12.PHASE_1_ALLOW) | {"READ_PROJECT", "READ_FILE", "GENERATE_WORKER_BRIEF",
                                             "RECORD_RESULT", "RECORD_NOTE"}
CHANGED_NAMES = frozenset(CHANGED) | {row[0] for row in ADDED}

POLICY_SHA = "b" * 64


def policy(version: int = 2) -> PolicySnapshot:
    rules = tuple(
        CapabilityRule(name=n, base_level=lvl, requires_isolation=iso, allowed_classes=cls,
                       phase_enabled=ph, mechanism_implemented=mech, forbidden_l5=l5,
                       non_goal=ng)
        for (n, lvl, iso, cls, ph, mech, l5, ng, _v, _r) in ROWS
    )
    return PolicySnapshot(schema_version=1, policy_version=version, sha256=POLICY_SHA, rules=rules)
