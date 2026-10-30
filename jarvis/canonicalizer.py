"""Canonicalizer: stage 2 of ADR-0003 D1 and D3.

Turns a raw path into a CanonicalTarget (resolved path plus a target class) or a
TargetFailure with one closed-list reason code. It performs I/O (strict path
resolution) and never decides a verdict; the pure evaluator applies the class
rules (always-DENY classes, scope, contracts).

Order, as ADR-0003 D3 requires:
1. Raw-input checks on the raw string, BEFORE any normalising call. Python's
   abspath strips trailing dots and spaces on Windows, so those must be rejected
   first.
2. Strict resolution with os.path.realpath(strict=True). Any error is
   TARGET_UNRESOLVABLE. A path that does not exist yet (must_exist=False) has its
   parent resolved strictly and its leaf validated by the raw rules.
3. Classification by containment on canonical, case-normalised paths.

Engineering choices (E-3), stated here because the ADR leaves them open:
- Class precedence when a target lies inside more than one protected area:
  GOVERNANCE_ZONE, DATA_ROOT, JARVIS_SELF, USER_SECRET_LOCATION.
- Every protected root and secret entry is matched in two forms, lexical and
  resolved, so a junction or symlink that moves a protected folder is still caught,
  and an entry that does not exist on this machine still matches.
- A target that resolves to a UNC or network location is TARGET_UNRESOLVABLE.
- A target outside every protected area and every registered project is
  UNCLASSIFIED, which the evaluator denies (default deny).
"""

import ntpath
import os
import re
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple, Union

from .model import CanonicalTarget, TargetFailure
from .reasons import TargetClass

_RESERVED_BASES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {"COM%d" % i for i in range(1, 10)}
    | {"LPT%d" % i for i in range(1, 10)}
    | {"COM\u00b9", "COM\u00b2", "COM\u00b3", "LPT\u00b9", "LPT\u00b2", "LPT\u00b3"}
)
_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_INVALID_CHARS = frozenset('<>"|?*')
_RECORD_TYPE = re.compile(r"^[a-z][a-z_]{0,31}$")
_RECORD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Highest precedence first (engineering choice, see module docstring).
_PROTECTED_ORDER = (TargetClass.GOVERNANCE_ZONE, TargetClass.DATA_ROOT,
                    TargetClass.JARVIS_SELF, TargetClass.USER_SECRET_LOCATION)


def is_reserved_name(component: str) -> bool:
    """A Windows reserved device name, with or without an extension."""
    base = component.split(".", 1)[0].rstrip(" ").upper()
    return base in _RESERVED_BASES


def raw_failure(raw) -> Optional[str]:
    """Raw-input checks (ADR-0003 D3 step 1). Returns a reason code or None.
    Runs on the raw string; calls no normalising function."""
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        return "TARGET_RAW_INVALID"
    if raw.startswith(("\\\\", "//")):
        return "TARGET_RAW_INVALID"  # UNC and the \\?\ and \\.\ device prefixes
    if not _DRIVE_ABSOLUTE.match(raw):
        return "TARGET_RAW_INVALID"  # relative, rooted-only or drive-relative
    rest = raw[2:]
    if ":" in rest:
        return "TARGET_RAW_INVALID"  # alternate data stream marker
    if any(ch in _INVALID_CHARS for ch in rest):
        return "TARGET_RAW_INVALID"
    for part in rest.replace("/", "\\").split("\\"):
        if part in ("", ".", ".."):
            continue
        if part.endswith((".", " ")):
            return "TARGET_RAW_INVALID"
        if is_reserved_name(part):
            return "TARGET_RAW_INVALID"
    return None


def _strip_device_prefix(path: str) -> Optional[str]:
    if path.startswith("\\\\?\\UNC\\"):
        return None  # a network location
    if path.startswith("\\\\?\\"):
        path = path[4:]
    elif path.startswith("\\\\"):
        return None  # plain UNC
    return path if _DRIVE_ABSOLUTE.match(path) else None


def resolve(raw: str, must_exist: bool = True) -> Union[str, TargetFailure]:
    """Raw checks, then strict resolution. Returns the resolved path or a failure."""
    reason = raw_failure(raw)
    if reason:
        return TargetFailure(reason)
    try:
        resolved = os.path.realpath(raw, strict=True)
    except FileNotFoundError:
        if must_exist:
            return TargetFailure("TARGET_UNRESOLVABLE")
        leaf = ntpath.basename(raw.replace("/", "\\").rstrip("\\"))
        parent = ntpath.dirname(raw.replace("/", "\\").rstrip("\\"))
        if leaf in ("", ".", "..") or not parent:
            return TargetFailure("TARGET_UNRESOLVABLE")
        try:
            resolved_parent = os.path.realpath(parent, strict=True)
        except (OSError, ValueError):
            return TargetFailure("TARGET_UNRESOLVABLE")
        resolved = ntpath.join(resolved_parent, leaf)
    except (OSError, ValueError):
        return TargetFailure("TARGET_UNRESOLVABLE")
    clean = _strip_device_prefix(resolved)
    if clean is None:
        return TargetFailure("TARGET_UNRESOLVABLE")
    return clean


def _norm(path: str) -> str:
    return ntpath.normcase(ntpath.normpath(path))


def normalize(path: str) -> str:
    """Case-normalised form used for every containment comparison."""
    return _norm(path)


def inside(path: str, root: str) -> bool:
    """Containment on canonical, case-normalised paths. A different drive is not
    inside. A name that only shares a prefix is not inside."""
    p, r = _norm(path), _norm(root)
    try:
        return ntpath.commonpath([p, r]) == r
    except ValueError:
        return False


def _forms(path: str) -> Tuple[str, ...]:
    lexical = _norm(ntpath.abspath(path))
    resolved = _norm(os.path.realpath(path))
    return (lexical,) if lexical == resolved else (lexical, resolved)


@dataclass(frozen=True)
class Roots:
    """Everything classification needs, already in matching form.

    protected maps each always-deny class to the forms it matches. project_roots
    maps a registry ID to the canonical root path of that project.
    """

    protected: Mapping[TargetClass, Tuple[str, ...]]
    project_roots: Mapping[str, str]


def build_roots(governance_zone: str, data_root: str, jarvis_repo: str, user_home: str,
                secret_entries: Tuple[str, ...],
                project_roots: Optional[Mapping[str, str]] = None) -> Roots:
    """Prepare roots from configuration values and the policy's secret entries.
    Paths need not exist: nothing here raises on a missing path."""
    secrets = []
    for entry in secret_entries:
        secrets.extend(_forms(ntpath.join(user_home, entry)))
    protected = {
        TargetClass.GOVERNANCE_ZONE: _forms(governance_zone),
        TargetClass.DATA_ROOT: _forms(data_root),
        TargetClass.JARVIS_SELF: _forms(jarvis_repo),
        TargetClass.USER_SECRET_LOCATION: tuple(dict.fromkeys(secrets)),
    }
    roots = {pid: _norm(os.path.realpath(path)) for pid, path in (project_roots or {}).items()}
    return Roots(protected=protected, project_roots=roots)


def canonicalize_path(raw: str, roots: Roots, must_exist: bool = True,
                      project_id: Optional[str] = None) -> Union[CanonicalTarget, TargetFailure]:
    """Resolve and classify a path target (ADR-0003 D3)."""
    resolved = resolve(raw, must_exist)
    if isinstance(resolved, TargetFailure):
        return resolved
    for cls in _PROTECTED_ORDER:
        if any(inside(resolved, form) for form in roots.protected[cls]):
            return CanonicalTarget(cls, resolved)
    if project_id is not None:
        root = roots.project_roots.get(project_id)
        if root is None:
            return CanonicalTarget(TargetClass.UNCLASSIFIED, resolved)
        if _drive(resolved) != _drive(root):
            return TargetFailure("TARGET_CROSS_DRIVE")
        return CanonicalTarget(TargetClass.PROJECT_PATH, resolved, project_id=project_id)
    for pid, root in roots.project_roots.items():
        if inside(resolved, root):
            return CanonicalTarget(TargetClass.PROJECT_PATH, resolved, project_id=pid)
    return CanonicalTarget(TargetClass.UNCLASSIFIED, resolved)


def _drive(path: str) -> str:
    return ntpath.splitdrive(_norm(path))[0]


def canonicalize_record(record_type: str, record_id: str) -> Union[CanonicalTarget, TargetFailure]:
    """A CONTROL_PLANE_RECORD is a type and an ID chosen by the control plane. It
    involves no path; only the shape is validated (ADR-0003 D3)."""
    if not (isinstance(record_type, str) and _RECORD_TYPE.match(record_type)
            and isinstance(record_id, str) and _RECORD_ID.match(record_id)):
        return TargetFailure("TARGET_RAW_INVALID")
    return CanonicalTarget(TargetClass.CONTROL_PLANE_RECORD, "%s/%s" % (record_type, record_id))
