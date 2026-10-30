"""Project registry loader (ADR-0002 D1 row 2; ADR-0004 D3, D4, D5, D7).

One TOML file in the governance zone, read on every evaluation and never cached.
It is written by RK outside JARVIS. The format is an engineering choice made for
Phase 1, because no ADR fixes it (ADR-0004 D7 leaves schema versions to
engineering):

    schema_version = 1

    [[projects]]
    id = "swarag"                # immutable lowercase slug
    name = "Swarag"
    root = 'D:\\work\\swarag'     # optional; a record may be unresolved
    repository = "owner/name"    # optional, informational
    description = "..."          # optional, informational

Allowed operations, required verification and workspace restrictions belong to the
contract (jarvis/contracts.py). Project instructions and the memory location are
informational and are not parsed in Phase 1 (ADR-0004 D1).

A project whose root is missing, does not resolve, lies in a protected area, or
overlaps another root has no usable root: evaluations treat the project as unknown
until RK corrects the registry. JARVIS never edits the registry.
"""

import hashlib
import os
import re
import tomllib
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

from . import canonicalizer
from .config import ConfigError, canonical_text_bytes
from .model import PROJECT_ID_RE, TargetFailure
from .reasons import TargetClass

FILE_NAME = "registry.toml"
SUPPORTED_SCHEMAS = frozenset({1})
TOP_KEYS = frozenset({"schema_version", "projects"})
REQUIRED = frozenset({"id", "name"})
OPTIONAL = frozenset({"root", "repository", "description"})
_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:\\")
MAX_TEXT = 500
_PROTECTED = (TargetClass.GOVERNANCE_ZONE, TargetClass.DATA_ROOT,
              TargetClass.JARVIS_SELF, TargetClass.USER_SECRET_LOCATION)


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    name: str
    root: Optional[str] = None
    repository: str = ""
    description: str = ""


@dataclass(frozen=True)
class RegistrySnapshot:
    projects: Tuple[ProjectRecord, ...]
    sha256: str


@dataclass(frozen=True)
class RegistryFailure:
    reason: str


def path_in(governance_zone: str) -> str:
    return os.path.join(governance_zone, FILE_NAME)


def _text(value) -> bool:
    return isinstance(value, str) and len(value) <= MAX_TEXT and all(ch >= " " for ch in value)


def parse(raw: bytes) -> Union[RegistrySnapshot, RegistryFailure]:
    try:
        data = canonical_text_bytes(raw)
        doc = tomllib.loads(data.decode("utf-8"))
    except (ConfigError, tomllib.TOMLDecodeError):
        return RegistryFailure("REGISTRY_INVALID")
    if set(doc) != TOP_KEYS:
        return RegistryFailure("REGISTRY_INVALID")
    schema = doc["schema_version"]
    if not isinstance(schema, int) or isinstance(schema, bool) or schema not in SUPPORTED_SCHEMAS:
        return RegistryFailure("REGISTRY_SCHEMA_UNKNOWN")
    entries = doc["projects"]
    if not isinstance(entries, list):
        return RegistryFailure("REGISTRY_INVALID")
    projects, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict):
            return RegistryFailure("REGISTRY_INVALID")
        keys = set(entry)
        if not REQUIRED <= keys or keys - REQUIRED - OPTIONAL:
            return RegistryFailure("REGISTRY_INVALID")
        pid = entry["id"]
        if not (isinstance(pid, str) and PROJECT_ID_RE.match(pid)) or pid in seen:
            return RegistryFailure("REGISTRY_INVALID")
        seen.add(pid)
        root = entry.get("root")
        if root is not None and not (isinstance(root, str) and _DRIVE_ABSOLUTE.match(root)):
            return RegistryFailure("REGISTRY_INVALID")
        name = entry["name"]
        repository, description = entry.get("repository", ""), entry.get("description", "")
        if not (_text(name) and name and _text(repository) and _text(description)):
            return RegistryFailure("REGISTRY_INVALID")
        projects.append(ProjectRecord(pid, name, root, repository, description))
    return RegistrySnapshot(tuple(projects), hashlib.sha256(data).hexdigest())


def load(path: str) -> Union[RegistrySnapshot, RegistryFailure]:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return RegistryFailure("REGISTRY_MISSING")
    except OSError:
        return RegistryFailure("REGISTRY_UNAVAILABLE")
    return parse(raw)


def resolve_roots(snapshot: RegistrySnapshot, base_roots) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Resolve each project root strictly (ADR-0003 D3) and apply ADR-0004 D3 and D5.

    base_roots is a canonicalizer.Roots without project roots. Returns
    (usable canonical roots by project ID, reason by project ID for every project
    with a root that cannot be used). A project with no root is in neither."""
    resolved: Dict[str, str] = {}
    rejected: Dict[str, str] = {}
    for project in snapshot.projects:
        if project.root is None:
            continue
        path = canonicalizer.resolve(project.root)
        if isinstance(path, TargetFailure):
            rejected[project.id] = path.reason
            continue
        if any(canonicalizer.inside(path, form) or canonicalizer.inside(form, path)
               for cls in _PROTECTED for form in base_roots.protected[cls]):
            rejected[project.id] = "ROOT_PROTECTED"
            continue
        resolved[project.id] = path
    for a in sorted(resolved):
        for b in sorted(resolved):
            if a != b and (canonicalizer.inside(resolved[a], resolved[b])
                           or canonicalizer.inside(resolved[b], resolved[a])):
                rejected[a] = "ROOT_OVERLAP"
    usable = {pid: canonicalizer.normalize(path) for pid, path in resolved.items()
              if pid not in rejected}
    return usable, rejected
