"""The policy version 4 capability matrix as test data (ADR-0015 D5): version 3 plus exactly LAUNCH_LOCAL."""

from jarvis.model import CapabilityRule, PolicySnapshot
from jarvis.reasons import Level, TargetClass

from . import policy_v3 as v3

CPR = frozenset({TargetClass.CONTROL_PLANE_RECORD})
ADDED = (("LAUNCH_LOCAL", Level.L2, False, CPR, True, True, False, False, "ALLOW", "ALLOWED_BY_POLICY"),)
ROWS = tuple(v3.ROWS) + ADDED
BETA_ALLOW = frozenset(v3.BETA_ALLOW) | {"LAUNCH_LOCAL"}
CHANGED_NAMES = frozenset(row[0] for row in ADDED)
POLICY_SHA = "d" * 64


def policy(version: int = 4) -> PolicySnapshot:
    rules = tuple(
        CapabilityRule(name=n, base_level=lvl, requires_isolation=iso, allowed_classes=cls,
                       phase_enabled=ph, mechanism_implemented=mech, forbidden_l5=l5,
                       non_goal=ng)
        for (n, lvl, iso, cls, ph, mech, l5, ng, _v, _r) in ROWS
    )
    return PolicySnapshot(schema_version=1, policy_version=version, sha256=POLICY_SHA, rules=rules)
