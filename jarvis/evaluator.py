"""The pure capability evaluator: stage 3 of ADR-0003 D1.

It reads no environment variable, file, network or clock. The only time inputs
are the explicit now_utc and last_recorded_utc arguments. Same inputs give the
same output. Steps follow ADR-0003 D9; the first DENY wins, then the first DEFER,
otherwise ALLOW.

Engineering choices (E-2), recorded here because the ADR leaves them open:
- A project-scoped target (PROJECT_ID, PROJECT_PATH) needs a contract input; any
  other canonical target takes NO_CONTRACT. A mismatch is INPUT_INVALID.
- If the risk level cannot be derived because a step from 1 to 4 fails, the
  reported level is L5, the fail-closed maximum. After step 4 the level is the
  capability's base level, raised in step 12.
- A protected path raises the level by one, capped at L4 (D10 says "raised",
  without a magnitude).
"""

import ntpath
from typing import Iterable, Optional, Tuple

from .model import (
    CAPABILITY_RE, NO_CONTRACT, PROJECT_ID_RE, SHA256_RE, SUPPORTED_CONTRACT_SCHEMAS,
    SUPPORTED_POLICY_SCHEMAS, TIMESTAMP_RE, CanonicalTarget, CapabilityRule,
    ContractFailure, Decision, EffectiveContract, PolicyFailure, PolicySnapshot,
    RevocationFailure, RevocationSnapshot, TargetFailure, TaskConstraints,
)
from .reasons import (
    ALWAYS_DENY_CLASSES, HASH_REQUIRED_CLASSES, PROJECT_SCOPED_CLASSES,
    STEP_OF_REASON, Level, TargetClass, Verdict, verdict_for,
)


def _decide(level: Level, reason: str) -> Decision:
    return Decision(risk_level=level, verdict=verdict_for(reason), reason=reason)


def _is_ts(value) -> bool:
    return isinstance(value, str) and bool(TIMESTAMP_RE.match(value))


def _is_sha(value) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.match(value))


def _within(path: str, root: str) -> bool:
    """Pure containment on canonical Windows paths. No filesystem access."""
    p, r = ntpath.normcase(path), ntpath.normcase(root)
    try:
        return ntpath.commonpath([p, r]) == r
    except ValueError:
        return False


def _failure_ok(reason, step: int) -> bool:
    return isinstance(reason, str) and STEP_OF_REASON.get(reason) == step


def _valid_rule(rule) -> bool:
    if not isinstance(rule, CapabilityRule):
        return False
    if not (isinstance(rule.name, str) and CAPABILITY_RE.match(rule.name)):
        return False
    if not isinstance(rule.base_level, Level):
        return False
    if rule.allowed_classes is not None:
        if not isinstance(rule.allowed_classes, frozenset):
            return False
        if not all(isinstance(c, TargetClass) for c in rule.allowed_classes):
            return False
    flags = (rule.requires_isolation, rule.phase_enabled, rule.mechanism_implemented,
             rule.forbidden_l5, rule.non_goal)
    return all(isinstance(f, bool) for f in flags)


def _valid_inputs(capability, target, contract, policy, revocations,
                  task_constraints, now_utc, last_recorded_utc) -> bool:
    """Step 1: types, no extra fields, hashes present where required."""
    if not (isinstance(capability, str) and CAPABILITY_RE.match(capability)):
        return False

    if isinstance(target, TargetFailure):
        if not _failure_ok(target.reason, 6):
            return False
    elif isinstance(target, CanonicalTarget):
        if not isinstance(target.target_class, TargetClass):
            return False
        if not (isinstance(target.value, str) and target.value):
            return False
        if target.sha256 is not None and not _is_sha(target.sha256):
            return False
        if target.target_class in HASH_REQUIRED_CLASSES and target.sha256 is None:
            return False
        scoped = target.target_class in PROJECT_SCOPED_CLASSES
        if scoped:
            if not (isinstance(target.project_id, str) and PROJECT_ID_RE.match(target.project_id)):
                return False
            if not isinstance(contract, (EffectiveContract, ContractFailure)):
                return False
        else:
            if target.project_id is not None or contract is not NO_CONTRACT:
                return False
    else:
        return False

    if isinstance(contract, ContractFailure):
        if not _failure_ok(contract.reason, 8):
            return False
    elif isinstance(contract, EffectiveContract):
        if not (isinstance(contract.schema_version, int) and _is_sha(contract.sha256)):
            return False
        if not (isinstance(contract.project_id, str) and PROJECT_ID_RE.match(contract.project_id)):
            return False
        if contract.valid_until is not None and not _is_ts(contract.valid_until):
            return False
        if not all(isinstance(p, str) and p for p in contract.scope_roots + contract.protected_paths):
            return False
        if not all(isinstance(c, str) for c in contract.forbidden_operations):
            return False
    elif contract is not NO_CONTRACT:
        return False

    if isinstance(policy, PolicyFailure):
        if not _failure_ok(policy.reason, 2):
            return False
    elif isinstance(policy, PolicySnapshot):
        if not (isinstance(policy.schema_version, int) and isinstance(policy.policy_version, int)):
            return False
        if not _is_sha(policy.sha256):
            return False
        if not (isinstance(policy.rules, tuple) and all(_valid_rule(r) for r in policy.rules)):
            return False
        names = [r.name for r in policy.rules]
        if len(names) != len(set(names)):
            return False
    else:
        return False

    if isinstance(revocations, RevocationFailure):
        if not _failure_ok(revocations.reason, 5) or revocations.reason != "REVOCATION_UNAVAILABLE":
            return False
    elif not isinstance(revocations, RevocationSnapshot):
        return False

    if not isinstance(task_constraints, TaskConstraints):
        return False
    if not (isinstance(task_constraints.extra_capabilities, tuple)
            and all(isinstance(c, str) for c in task_constraints.extra_capabilities)):
        return False
    if task_constraints.scope_paths is not None:
        if not (isinstance(task_constraints.scope_paths, tuple)
                and all(isinstance(p, str) and p for p in task_constraints.scope_paths)):
            return False

    if not _is_ts(now_utc):
        return False
    if last_recorded_utc is not None and not _is_ts(last_recorded_utc):
        return False
    return True


def evaluate(capability, target, contract, policy, revocations, task_constraints,
             now_utc, last_recorded_utc) -> Decision:
    """Return (risk_level, verdict, reason) for one requested capability."""
    unknown = Level.L5

    # Step 1. Input validation.
    if not _valid_inputs(capability, target, contract, policy, revocations,
                         task_constraints, now_utc, last_recorded_utc):
        return _decide(unknown, "INPUT_INVALID")

    # Step 2. Policy.
    if isinstance(policy, PolicyFailure):
        return _decide(unknown, policy.reason)
    if policy.schema_version not in SUPPORTED_POLICY_SCHEMAS:
        return _decide(unknown, "POLICY_FORMAT_INVALID")
    if policy.policy_version < 1:
        return _decide(unknown, "POLICY_VERSION_UNKNOWN")

    # Step 3. Clock. Fixed-format UTC strings compare in time order.
    if last_recorded_utc is not None and now_utc < last_recorded_utc:
        return _decide(unknown, "CLOCK_SKEW")

    # Step 4. Capability recognized.
    rule = policy.rule(capability)
    if rule is None:
        return _decide(unknown, "UNKNOWN_CAPABILITY")
    level = rule.base_level

    # Step 5. Revocation.
    if isinstance(revocations, RevocationFailure):
        return _decide(level, revocations.reason)
    if capability in revocations.capabilities:
        return _decide(level, "REVOKED")
    if isinstance(target, CanonicalTarget) and target.project_id in revocations.projects:
        return _decide(level, "REVOKED")
    if isinstance(contract, EffectiveContract):
        if contract.project_id in revocations.projects or contract.sha256 in revocations.contract_hashes:
            return _decide(level, "REVOKED")

    # Step 6. Target raw checks and strict resolution (done by the canonicalizer).
    if isinstance(target, TargetFailure):
        return _decide(level, target.reason)

    # Step 7. Always-deny classes and unclassified targets.
    if target.target_class in ALWAYS_DENY_CLASSES:
        return _decide(level, ALWAYS_DENY_CLASSES[target.target_class])
    if target.target_class is TargetClass.UNCLASSIFIED:
        return _decide(level, "UNKNOWN_TARGET_CLASS")

    scoped = target.target_class in PROJECT_SCOPED_CLASSES

    # Step 8. Project and contract resolution.
    if scoped:
        if isinstance(contract, ContractFailure):
            return _decide(level, contract.reason)
        if contract.schema_version not in SUPPORTED_CONTRACT_SCHEMAS:
            return _decide(level, "CONTRACT_SCHEMA_UNKNOWN")
        if contract.project_id != target.project_id:
            return _decide(level, "CONTRACT_INVALID")

        # Step 9. Expiry.
        if contract.valid_until is not None and now_utc > contract.valid_until:
            return _decide(level, "EXPIRED")

    # Step 10. Contract authorization and narrowing.
    if rule.allowed_classes is not None and target.target_class not in rule.allowed_classes:
        return _decide(level, "TARGET_CLASS_NOT_ALLOWED")
    if scoped and target.target_class is TargetClass.PROJECT_PATH:
        if not any(_within(target.value, root) for root in contract.scope_roots):
            return _decide(level, "TARGET_OUT_OF_SCOPE")
        if task_constraints.scope_paths is not None and not any(
                _within(target.value, p) for p in task_constraints.scope_paths):
            return _decide(level, "TARGET_OUT_OF_SCOPE")
    if scoped and capability in contract.forbidden_operations:
        return _decide(level, "FORBIDDEN_BY_CONTRACT")
    if task_constraints.extra_capabilities:
        return _decide(level, "CONSTRAINT_WIDENS")
    if scoped and task_constraints.scope_paths is not None:
        for p in task_constraints.scope_paths:
            if not any(_within(p, root) for root in contract.scope_roots):
                return _decide(level, "CONSTRAINT_WIDENS")

    # Step 11. Non-goal and L5 rules.
    if rule.forbidden_l5:
        return _decide(Level.L5, "FORBIDDEN_L5")
    if rule.non_goal:
        return _decide(level, "NON_GOAL_V01")

    # Step 12. Level derivation: raised, never lowered.
    if (scoped and target.target_class is TargetClass.PROJECT_PATH
            and any(_within(target.value, p) for p in contract.protected_paths)):
        if level.rank < Level.L4.rank:
            level = Level.from_rank(level.rank + 1)

    # Step 13. DEFER conditions. No isolation attestation and no approval
    # mechanism exist in Phase 1 (ADR-0003 D8).
    if not rule.phase_enabled:
        return _decide(level, "PHASE_NOT_ENABLED")
    if rule.requires_isolation:
        return _decide(level, "ISOLATION_REQUIRED")
    if level.rank >= Level.L4.rank:
        return _decide(level, "APPROVAL_MECHANISM_ABSENT")
    if not rule.mechanism_implemented:
        return _decide(level, "MECHANISM_NOT_IMPLEMENTED")

    # Step 14. ALLOW.
    return _decide(level, "ALLOWED_BY_POLICY")


def task_outcome(decisions: Iterable[Decision]) -> Tuple[Optional[Level], str]:
    """ADR-0003 D10: task risk is the maximum level; any DENY blocks, else any
    DEFER defers, else the task may run. Returns (task_risk, outcome) where
    outcome is BLOCKED, DEFERRED or RUNNABLE. An empty request is BLOCKED.
    """
    decisions = tuple(decisions)
    if not decisions:
        return None, "BLOCKED"
    risk = Level.from_rank(max(d.risk_level.rank for d in decisions))
    if any(d.verdict is Verdict.DENY for d in decisions):
        return risk, "BLOCKED"
    if any(d.verdict is Verdict.DEFER for d in decisions):
        return risk, "DEFERRED"
    return risk, "RUNNABLE"
