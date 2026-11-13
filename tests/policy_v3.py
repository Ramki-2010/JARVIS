"""The policy version 3 capability matrix as test data (ADR-0014 D5).

An independent transcription: the version 2 table plus exactly one added capability, FETCH_PUBLIC_DATA, and nothing else.
It is not the policy file; the tests compare the policy file to it.
"""

from jarvis.model import CapabilityRule, PolicySnapshot
from jarvis.reasons import Level, TargetClass

from . import policy_v2 as v2

CPR = frozenset({TargetClass.CONTROL_PLANE_RECORD})

ADDED = (("FETCH_PUBLIC_DATA", Level.L1, False, CPR, True, True, False, False, "ALLOW", "ALLOWED_BY_POLICY"),)
ROWS = tuple(v2.ROWS) + ADDED
BETA_ALLOW = frozenset(v2.BETA_ALLOW) | {"FETCH_PUBLIC_DATA"}
CHANGED_NAMES = frozenset(row[0] for row in ADDED)
POLICY_SHA = "c" * 64


def policy(version: int = 3) -> PolicySnapshot:
    rules = tuple(
        CapabilityRule(name=n, base_level=lvl, requires_isolation=iso, allowed_classes=cls,
                       phase_enabled=ph, mechanism_implemented=mech, forbidden_l5=l5,
                       non_goal=ng)
        for (n, lvl, iso, cls, ph, mech, l5, ng, _v, _r) in ROWS
    )
    return PolicySnapshot(schema_version=1, policy_version=version, sha256=POLICY_SHA, rules=rules)
