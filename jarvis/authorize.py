"""Evaluate one capability against a control-plane record, outside a task.

`note add` (and later `result add`) are single actions on a record the control plane
names. They still go through the pure evaluator with the current policy and revocation
list (ADR-0003 D1, D7), so a capability the policy does not allow is refused. Nothing
here widens authority: the target is always a CONTROL_PLANE_RECORD.
"""

from . import canonicalizer, revocations
from . import policy as policy_mod
from .evaluator import evaluate
from .model import NO_CONTRACT, Decision, PolicyFailure, TargetFailure, TaskConstraints


def decide(store, cfg, policy_path: str, capability: str, record_type: str, record_id: str,
           now_utc: str) -> Decision:
    loaded = policy_mod.load(policy_path, store.known_policy_hashes())
    policy = loaded if isinstance(loaded, PolicyFailure) else loaded.snapshot
    target = canonicalizer.canonicalize_record(record_type, record_id)
    if isinstance(target, TargetFailure):
        pass  # the evaluator turns a failed target into a DENY with its reason
    revoked = revocations.load(revocations.path_in(cfg.governance_zone))
    return evaluate(capability, target, NO_CONTRACT, policy, revoked, TaskConstraints(),
                    now_utc, store.last_recorded_utc())
