"""Task requests and evaluation: the glue between the loaders, the canonicalizer, the
pure evaluator and the store (ADR-0002 D1 and D2, ADR-0003 D1, D7, D10, D11).

The loader stages here do the I/O (policy, revocation list, clock, audit store). The
evaluator receives plain values and performs none. A task's request is structured:
capabilities, each with one target, and optional constraints. Free text never reaches
the evaluator (ADR-0003 D5); the objective is stored and ignored by evaluation.
"""

import os
import re
from typing import List

from . import canonicalizer, contracts, registry, revocations
from . import policy as policy_mod
from . import states
from .evaluator import evaluate as evaluate_capability
from .evaluator import task_outcome
from .model import (CAPABILITY_RE, NO_CONTRACT, CanonicalTarget, ContractFailure,
                    EffectiveContract, PolicyFailure, TargetFailure, TaskConstraints)
from .reasons import PROJECT_SCOPED_CLASSES, Level
from .store import Evaluation

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
MAX_OBJECTIVE = 2000
MAX_REQUESTS = 20

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_POLICY_PATH = os.path.join(REPO_ROOT, "policy", "policy.toml")


class TaskInputError(ValueError):
    """Carries a fixed code, never a value."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def validate_id(value: str, code: str) -> str:
    if not (isinstance(value, str) and ID_RE.match(value)):
        raise TaskInputError(code)
    return value


def validate_objective(value: str) -> str:
    if not (isinstance(value, str) and value.strip() and len(value) <= MAX_OBJECTIVE
            and all(ch == "\n" or ch >= " " for ch in value)):
        raise TaskInputError("OBJECTIVE_INVALID")
    return value


def parse_request(spec: str, task_id: str) -> dict:
    """`CAPABILITY`, `CAPABILITY=record:TYPE/ID` or `CAPABILITY=path:RAW`.

    With no target the request names the task itself, as the control-plane record
    `task/<task_id>`. A path target is classified by the canonicalizer.
    """
    if not isinstance(spec, str):
        raise TaskInputError("REQUEST_INVALID")
    name, sep, target = spec.partition("=")
    if not CAPABILITY_RE.match(name):
        raise TaskInputError("REQUEST_INVALID")
    if not sep:
        return {"capability": name, "target": {"kind": "record", "value": "task/%s" % task_id}}
    kind, colon, value = target.partition(":")
    if kind not in ("record", "path") or not colon or not value:
        raise TaskInputError("REQUEST_INVALID")
    if kind == "record" and "/" not in value:
        raise TaskInputError("REQUEST_INVALID")
    return {"capability": name, "target": {"kind": kind, "value": value}}


def build_request(specs: List[str], add_capabilities: List[str], task_id: str) -> dict:
    if not specs or len(specs) > MAX_REQUESTS:
        raise TaskInputError("REQUEST_COUNT_INVALID")
    for cap in add_capabilities:
        if not CAPABILITY_RE.match(cap):
            raise TaskInputError("REQUEST_INVALID")
    return {
        "requests": [parse_request(s, task_id) for s in specs],
        "constraints": {"add_capabilities": sorted(set(add_capabilities))},
    }


def _target(request: dict, roots, project_id=None):
    target = request["target"]
    if target["kind"] == "record":
        record_type, _, record_id = target["value"].partition("/")
        return canonicalizer.canonicalize_record(record_type, record_id)
    return canonicalizer.canonicalize_path(target["value"], roots, project_id=project_id)


def _describe(target) -> str:
    if isinstance(target, TargetFailure):
        return "FAILED:%s" % target.reason
    return "%s:%s" % (target.target_class.value, target.value)


def evaluate_task(store, config, policy_path: str, task_id: str, now_utc: str) -> Evaluation:
    """Evaluate every requested capability of a task under the current policy,
    revocation list and clock, and return the Evaluation the store records.

    Nothing is cached: the policy and the revocation list are read on every call
    (ADR-0003 D7, D11).
    """
    return evaluate_with_targets(store, config, policy_path, task_id, now_utc)[0]


def evaluate_with_targets(store, config, policy_path: str, task_id: str, now_utc: str):
    """As evaluate_task, and also return one (request item, target, decision) per
    requested capability, in request order. `task run` uses it to act only on a target
    that is ALLOW under a fresh evaluation (ADR-0010 D3 item 1).
    """
    request = store.task_request(task_id)
    if not request or not request.get("requests"):
        raise TaskInputError("TASK_REQUEST_MISSING")

    loaded = policy_mod.load(policy_path, store.known_policy_hashes())
    if isinstance(loaded, PolicyFailure):
        policy, secrets = loaded, ()
    else:
        policy, secrets = loaded.snapshot, loaded.secret_locations
    roots = canonicalizer.build_roots(config.governance_zone, config.data_root, REPO_ROOT,
                                      config.user_home, secrets)
    # Registry and contracts are read on every evaluation. A missing or invalid
    # registry leaves no project root, so project-scoped targets are denied.
    project = store.get_task(task_id)["project"]
    registered = registry.load(registry.path_in(config.governance_zone))
    if isinstance(registered, registry.RegistryFailure):
        project_roots = {}
    else:
        project_roots, _ = registry.resolve_roots(registered, roots)
        roots = canonicalizer.build_roots(config.governance_zone, config.data_root, REPO_ROOT,
                                          config.user_home, secrets, project_roots)
    revoked = revocations.load(revocations.path_in(config.governance_zone))
    constraints = TaskConstraints(
        extra_capabilities=tuple((request.get("constraints") or {}).get("add_capabilities", ())))
    last_recorded = store.last_recorded_utc()

    decisions = []
    described = []
    resolved = []
    contract_hash = None
    for item in request["requests"]:
        target = _target(item, roots, project)
        contract = NO_CONTRACT
        if isinstance(target, CanonicalTarget) and target.target_class in PROJECT_SCOPED_CLASSES:
            root = project_roots.get(target.project_id) if target.project_id else None
            if root is None:
                contract = ContractFailure("CONTRACT_MISSING")
            else:
                contract = contracts.load(config.governance_zone, target.project_id, root)
                if isinstance(contract, EffectiveContract):
                    contract_hash = contract.sha256
        decision = evaluate_capability(item["capability"], target, contract, policy, revoked,
                                       constraints, now_utc, last_recorded)
        decisions.append(decision)
        resolved.append((item, target, decision))
        described.append({
            "capability": item["capability"],
            "target": _describe(target),
            "risk_level": decision.risk_level.value,
            "verdict": decision.verdict.value,
            "reason": decision.reason,
        })

    risk, outcome = task_outcome(decisions)
    snapshot = None if isinstance(policy, PolicyFailure) else policy
    evaluation = Evaluation(
        outcome=outcome,
        risk_level=risk if risk is not None else Level.L5,
        policy_version=snapshot.policy_version if snapshot else None,
        policy_sha256=snapshot.sha256 if snapshot else None,
        contract_sha256=contract_hash,
        capabilities=tuple(sorted({i["capability"] for i in request["requests"]})),
        decisions=tuple(described),
    )
    return evaluation, resolved


def target_state(evaluation: Evaluation) -> str:
    return states.STATE_FOR_OUTCOME[evaluation.outcome]
