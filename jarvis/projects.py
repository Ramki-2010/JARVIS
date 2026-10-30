"""Read-only project views for `project list` and `project show` (Beta plan BR-1).

Combines the registry, each project's resolved root and its contract, exactly as the
evaluator loads them (ADR-0004), and reports what RK has written. It decides nothing:
authority still comes only from the evaluator. A control-plane read, not a capability
(ADR-0002 D1).
"""

from dataclasses import dataclass
from typing import List, Optional, Union

from . import canonicalizer, contracts, registry
from . import policy as policy_mod
from .model import ContractFailure, EffectiveContract, PolicyFailure
from .tasks import REPO_ROOT


@dataclass(frozen=True)
class ProjectView:
    record: registry.ProjectRecord
    root: Optional[str]                    # canonical root, when usable
    root_problem: Optional[str]            # reason code when the root is rejected
    contract: Union[EffectiveContract, ContractFailure, None]  # None: no usable root


@dataclass(frozen=True)
class Failure:
    reason: str


def load(cfg, policy_path: str) -> Union[List[ProjectView], Failure]:
    loaded = policy_mod.load(policy_path)
    if isinstance(loaded, PolicyFailure):
        return Failure(loaded.reason)
    registered = registry.load(registry.path_in(cfg.governance_zone))
    if isinstance(registered, registry.RegistryFailure):
        return Failure(registered.reason)
    base = canonicalizer.build_roots(cfg.governance_zone, cfg.data_root, REPO_ROOT,
                                     cfg.user_home, loaded.secret_locations)
    usable, rejected = registry.resolve_roots(registered, base)
    views = []
    for project in registered.projects:
        contract = None
        if project.id in usable:
            contract = contracts.load(cfg.governance_zone, project.id, usable[project.id])
        views.append(ProjectView(project, usable.get(project.id), rejected.get(project.id), contract))
    return views


def contract_state(view: ProjectView) -> str:
    if view.root_problem:
        return "root rejected: %s" % view.root_problem
    if view.contract is None:
        return "no root registered"
    if isinstance(view.contract, ContractFailure):
        return view.contract.reason
    return "ok"
