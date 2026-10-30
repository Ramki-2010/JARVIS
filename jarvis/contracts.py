"""Project contract loader (ADR-0002 D1 row 3; ADR-0004 D1, D6, D7, D8, D9).

One TOML file per project in the governance zone, contracts/<project id>.toml, written
by RK outside JARVIS. JARVIS never loads a contract from a project tree. The format
is an engineering choice made for Phase 1 (ADR-0004 D9 leaves the field list to an
engineering schema task):

    schema_version = 1
    project_id = "swarag"
    valid_until = "2026-12-31T00:00:00.000000Z"   # optional, UTC
    scope_roots = ['D:\\work\\swarag\\src']         # inside the registered root
    protected_paths = ['D:\\work\\swarag\\keys']    # optional
    forbidden_operations = ["PUSH"]                # capability names, optional

A contract may only narrow (ADR-0004 D8): every scope root must lie inside the
project's registered root, otherwise the contract is invalid. Any problem returns
a ContractFailure with a closed reason code, and the evaluator denies.
"""

import hashlib
import os
import tomllib
from typing import Union

from . import canonicalizer
from .config import ConfigError, canonical_text_bytes
from .model import (CAPABILITY_RE, PROJECT_ID_RE, SUPPORTED_CONTRACT_SCHEMAS, TIMESTAMP_RE,
                    ContractFailure, EffectiveContract, TargetFailure)

DIR_NAME = "contracts"
REQUIRED = frozenset({"schema_version", "project_id", "scope_roots"})
OPTIONAL = frozenset({"valid_until", "protected_paths", "forbidden_operations"})
_INVALID = ContractFailure("CONTRACT_INVALID")


def path_in(governance_zone: str, project_id: str) -> str:
    return os.path.join(governance_zone, DIR_NAME, project_id + ".toml")


def _paths(value, must_exist: bool):
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, str):
            return None
        resolved = canonicalizer.resolve(item, must_exist)
        if isinstance(resolved, TargetFailure):
            return None
        out.append(canonicalizer.normalize(resolved))
    return tuple(out)


def parse(raw: bytes, project_id: str, project_root: str) -> Union[EffectiveContract, ContractFailure]:
    """project_root is the project's canonical registered root."""
    try:
        data = canonical_text_bytes(raw)
        doc = tomllib.loads(data.decode("utf-8"))
    except (ConfigError, tomllib.TOMLDecodeError):
        return _INVALID
    keys = set(doc)
    if not REQUIRED <= keys or keys - REQUIRED - OPTIONAL:
        return _INVALID
    schema = doc["schema_version"]
    if not isinstance(schema, int) or isinstance(schema, bool):
        return _INVALID
    if schema not in SUPPORTED_CONTRACT_SCHEMAS:
        return ContractFailure("CONTRACT_SCHEMA_UNKNOWN")
    if doc["project_id"] != project_id or not PROJECT_ID_RE.match(project_id):
        return _INVALID
    valid_until = doc.get("valid_until")
    if valid_until is not None and not (isinstance(valid_until, str) and TIMESTAMP_RE.match(valid_until)):
        return _INVALID
    scope = _paths(doc["scope_roots"], True)
    protected = _paths(doc.get("protected_paths", []), False)
    forbidden = doc.get("forbidden_operations", [])
    if scope is None or protected is None:
        return _INVALID
    if not (isinstance(forbidden, list)
            and all(isinstance(f, str) and CAPABILITY_RE.match(f) for f in forbidden)):
        return _INVALID
    if not all(canonicalizer.inside(root, project_root) for root in scope):
        return _INVALID
    return EffectiveContract(schema_version=schema, project_id=project_id,
                             sha256=hashlib.sha256(data).hexdigest(), valid_until=valid_until,
                             scope_roots=scope, forbidden_operations=frozenset(forbidden),
                             protected_paths=protected)


def load(governance_zone: str, project_id: str,
         project_root: str) -> Union[EffectiveContract, ContractFailure]:
    try:
        with open(path_in(governance_zone, project_id), "rb") as fh:
            raw = fh.read()
    except OSError:
        return ContractFailure("CONTRACT_MISSING")
    return parse(raw, project_id, project_root)
