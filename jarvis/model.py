"""Frozen input and output types for the evaluator (ADR-0003 D1, D5).

No type here carries free text that can reach the evaluator. Every string field
is an identifier, a canonical path, a hash or a fixed-format timestamp.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Tuple, FrozenSet, Union

from .reasons import Level, TargetClass

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
CAPABILITY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

SUPPORTED_POLICY_SCHEMAS = frozenset({1})
SUPPORTED_CONTRACT_SCHEMAS = frozenset({1})


@dataclass(frozen=True)
class CapabilityRule:
    """One row of the policy matrix (ADR-0003 D8, D12).

    allowed_classes None means ANY: every class except the always-deny classes
    and UNCLASSIFIED, which step 7 denies first.
    """

    name: str
    base_level: Level
    requires_isolation: bool
    allowed_classes: Optional[FrozenSet[TargetClass]]
    phase_enabled: bool
    mechanism_implemented: bool = True
    forbidden_l5: bool = False
    non_goal: bool = False


@dataclass(frozen=True)
class PolicySnapshot:
    schema_version: int
    policy_version: int
    sha256: str
    rules: Tuple[CapabilityRule, ...]

    def rule(self, capability: str) -> Optional[CapabilityRule]:
        for r in self.rules:
            if r.name == capability:
                return r
        return None


@dataclass(frozen=True)
class PolicyFailure:
    reason: str


@dataclass(frozen=True)
class RevocationSnapshot:
    capabilities: FrozenSet[str] = frozenset()
    projects: FrozenSet[str] = frozenset()
    contract_hashes: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class RevocationFailure:
    reason: str = "REVOCATION_UNAVAILABLE"


@dataclass(frozen=True)
class CanonicalTarget:
    """Output of the canonicalizer (ADR-0003 D3).

    value is the canonical string: a case-normalised absolute path for path
    classes, or "<type>/<id>" for CONTROL_PLANE_RECORD.
    """

    target_class: TargetClass
    value: str
    sha256: Optional[str] = None
    project_id: Optional[str] = None


@dataclass(frozen=True)
class TargetFailure:
    reason: str


@dataclass(frozen=True)
class EffectiveContract:
    """A project contract after narrowing (ADR-0004 D9). Paths are canonical."""

    schema_version: int
    project_id: str
    sha256: str
    valid_until: Optional[str] = None
    scope_roots: Tuple[str, ...] = ()
    forbidden_operations: FrozenSet[str] = frozenset()
    protected_paths: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ContractFailure:
    reason: str


class _NoContract:
    """Sentinel: the target is not project-scoped, so no contract applies."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NO_CONTRACT"


NO_CONTRACT = _NoContract()


@dataclass(frozen=True)
class TaskConstraints:
    """Structured constraints supplied by RK (ADR-0002 D3). Narrow only.

    extra_capabilities: any entry is an attempt to widen and is denied.
    scope_paths: canonical paths; each must lie inside the contract scope.
    """

    extra_capabilities: Tuple[str, ...] = ()
    scope_paths: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class Decision:
    risk_level: Level
    verdict: "object"
    reason: str

    def as_record(self) -> dict:
        return {
            "risk_level": self.risk_level.value,
            "verdict": self.verdict.value,
            "reason": self.reason,
        }


TargetInput = Union[CanonicalTarget, TargetFailure]
ContractInput = Union[EffectiveContract, ContractFailure, _NoContract]
PolicyInput = Union[PolicySnapshot, PolicyFailure]
RevocationInput = Union[RevocationSnapshot, RevocationFailure]
