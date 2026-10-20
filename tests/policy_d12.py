"""The ADR-0003 D12 capability matrix as test data.

This is an independent transcription of the accepted table, used to check the
evaluator. It is not the policy file. Columns: name, base level,
requires_isolation, allowed classes (None = ANY), phase_enabled,
mechanism_implemented, forbidden_l5, non_goal, expected Phase 1 verdict and reason.
"""

from jarvis.model import CapabilityRule, PolicySnapshot
from jarvis.reasons import Level, TargetClass

CPR = frozenset({TargetClass.CONTROL_PLANE_RECORD})

#      name                        level     iso    classes phase  mech   l5     nongoal verdict  reason
ROWS = (
    ("CREATE_TASK",                Level.L2, False, CPR,  True,  True,  False, False, "ALLOW", "ALLOWED_BY_POLICY"),
    ("CREATE_REPORT",              Level.L2, False, CPR,  True,  True,  False, False, "ALLOW", "ALLOWED_BY_POLICY"),
    ("READ_REGISTRY",              Level.L1, False, CPR,  True,  True,  False, False, "ALLOW", "ALLOWED_BY_POLICY"),
    ("READ_CONTROL_PLANE_CONFIG",  Level.L1, False, CPR,  True,  True,  False, False, "ALLOW", "ALLOWED_BY_POLICY"),
    ("READ_PROJECT",               Level.L1, False, None, False, True,  False, False, "DEFER", "PHASE_NOT_ENABLED"),
    ("READ_FILE",                  Level.L1, False, None, False, True,  False, False, "DEFER", "PHASE_NOT_ENABLED"),
    ("SEARCH_WEB",                 Level.L3, True,  None, True,  True,  False, False, "DEFER", "ISOLATION_REQUIRED"),
    ("WRITE_SANDBOX",              Level.L3, True,  None, True,  True,  False, False, "DEFER", "ISOLATION_REQUIRED"),
    ("RUN_TEST",                   Level.L3, True,  None, True,  True,  False, False, "DEFER", "ISOLATION_REQUIRED"),
    ("RUN_EXPERIMENT",             Level.L3, True,  None, True,  True,  False, False, "DEFER", "ISOLATION_REQUIRED"),
    ("USE_CLAUDE_CODE",            Level.L3, True,  None, True,  True,  False, False, "DEFER", "ISOLATION_REQUIRED"),
    ("USE_CODEBASE_MEMORY",        Level.L3, True,  None, True,  True,  False, False, "DEFER", "ISOLATION_REQUIRED"),
    ("USE_VERIFICATION",           Level.L3, True,  None, True,  True,  False, False, "DEFER", "ISOLATION_REQUIRED"),
    ("SCHEDULE_TASK",              Level.L3, False, None, True,  False, False, False, "DEFER", "MECHANISM_NOT_IMPLEMENTED"),
    ("GENERATE_WORKER_BRIEF",      Level.L2, False, None, False, True,  False, False, "DEFER", "PHASE_NOT_ENABLED"),
    ("DELETE_PROTECTED",           Level.L4, False, None, True,  True,  False, False, "DEFER", "APPROVAL_MECHANISM_ABSENT"),
    ("PUSH",                       Level.L4, False, None, True,  True,  False, False, "DEFER", "APPROVAL_MECHANISM_ABSENT"),
    ("MERGE",                      Level.L4, False, None, True,  True,  False, False, "DEFER", "APPROVAL_MECHANISM_ABSENT"),
    ("DEPLOY",                     Level.L4, False, None, True,  True,  False, False, "DEFER", "APPROVAL_MECHANISM_ABSENT"),
    ("SEND_EMAIL",                 Level.L4, False, None, True,  True,  False, False, "DEFER", "APPROVAL_MECHANISM_ABSENT"),
    ("SEND_MESSAGE",               Level.L4, False, None, True,  True,  False, False, "DEFER", "APPROVAL_MECHANISM_ABSENT"),
    ("MAKE_CALL",                  Level.L4, False, None, True,  True,  False, True,  "DENY",  "NON_GOAL_V01"),
    ("FINANCIAL_TRANSACTION",      Level.L4, False, None, True,  True,  False, True,  "DENY",  "NON_GOAL_V01"),
    ("CHANGE_PERMISSION",          Level.L5, False, None, True,  True,  True,  False, "DENY",  "FORBIDDEN_L5"),
    ("CHANGE_GOVERNANCE",          Level.L5, False, None, True,  True,  True,  False, "DENY",  "FORBIDDEN_L5"),
    ("DISABLE_GUARDRAIL",          Level.L5, False, None, True,  True,  True,  False, "DENY",  "FORBIDDEN_L5"),
)

MASTER_CONTEXT_INITIAL = (
    "READ_PROJECT", "READ_FILE", "SEARCH_WEB", "WRITE_SANDBOX", "RUN_TEST", "RUN_EXPERIMENT",
    "USE_CLAUDE_CODE", "USE_CODEBASE_MEMORY", "USE_VERIFICATION", "CREATE_REPORT",
    "CREATE_TASK", "SCHEDULE_TASK",
)
MASTER_CONTEXT_RESTRICTED = (
    "DELETE_PROTECTED", "PUSH", "MERGE", "DEPLOY", "SEND_EMAIL", "SEND_MESSAGE", "MAKE_CALL",
    "FINANCIAL_TRANSACTION", "CHANGE_PERMISSION", "CHANGE_GOVERNANCE", "DISABLE_GUARDRAIL",
)
PHASE_1_ADDITIONS = ("READ_REGISTRY", "READ_CONTROL_PLANE_CONFIG", "GENERATE_WORKER_BRIEF")
PHASE_1_ALLOW = ("CREATE_TASK", "CREATE_REPORT", "READ_REGISTRY", "READ_CONTROL_PLANE_CONFIG")

POLICY_SHA = "a" * 64


def policy(version: int = 1) -> PolicySnapshot:
    rules = tuple(
        CapabilityRule(name=n, base_level=lvl, requires_isolation=iso, allowed_classes=cls,
                       phase_enabled=ph, mechanism_implemented=mech, forbidden_l5=l5,
                       non_goal=ng)
        for (n, lvl, iso, cls, ph, mech, l5, ng, _v, _r) in ROWS
    )
    return PolicySnapshot(schema_version=1, policy_version=version, sha256=POLICY_SHA, rules=rules)
