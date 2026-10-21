"""Policy loader: stage 1 of ADR-0003 D1 for the policy file (D6).

Reads one TOML policy file and returns a PolicySnapshot with its SHA-256 over
canonical bytes (UTF-8, CRLF converted to LF, a lone CR rejected: D4), or a
PolicyFailure carrying one reason code from the closed list. The evaluator never
reads files; it receives the snapshot.

The user-secret locations (ADR-0008 D1) come from the same file, relative to
<USER_HOME>. Turning them into absolute paths needs the user-home value from
governance-zone configuration and belongs to the canonicalizer (ADR-0003 D3).
"""

import hashlib
import tomllib
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from .config import ConfigError, canonical_text_bytes
from .model import (CAPABILITY_RE, SUPPORTED_POLICY_SCHEMAS, CapabilityRule, PolicyFailure,
                    PolicySnapshot)
from .reasons import ALWAYS_DENY_CLASSES, Level, TargetClass

TOP_KEYS = frozenset({"schema_version", "policy_version", "capability", "secret_locations"})
REQUIRED_RULE_KEYS = frozenset({"name", "base_level", "requires_isolation", "phase_enabled",
                                "mechanism_implemented", "forbidden_l5", "non_goal"})
OPTIONAL_RULE_KEYS = frozenset({"allowed_classes"})
BOOL_KEYS = ("requires_isolation", "phase_enabled", "mechanism_implemented",
             "forbidden_l5", "non_goal")


@dataclass(frozen=True)
class LoadedPolicy:
    snapshot: PolicySnapshot
    secret_locations: Tuple[str, ...]


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _fail(code: str) -> PolicyFailure:
    return PolicyFailure(code)


def _rule(row) -> Optional[CapabilityRule]:
    if not isinstance(row, dict):
        return None
    keys = set(row)
    if not REQUIRED_RULE_KEYS <= keys or keys - REQUIRED_RULE_KEYS - OPTIONAL_RULE_KEYS:
        return None
    name = row["name"]
    if not (isinstance(name, str) and CAPABILITY_RE.match(name)):
        return None
    try:
        level = Level(row["base_level"])
    except (ValueError, TypeError):
        return None
    if not all(isinstance(row[k], bool) for k in BOOL_KEYS):
        return None
    classes = None
    if "allowed_classes" in row:
        raw = row["allowed_classes"]
        if not (isinstance(raw, list) and raw and all(isinstance(c, str) for c in raw)):
            return None
        try:
            parsed = {TargetClass(c) for c in raw}
        except ValueError:
            return None
        # A capability can never be allowed on an always-deny class or UNCLASSIFIED.
        if parsed & (set(ALWAYS_DENY_CLASSES) | {TargetClass.UNCLASSIFIED}):
            return None
        classes = frozenset(parsed)
    return CapabilityRule(name=name, base_level=level,
                          requires_isolation=row["requires_isolation"], allowed_classes=classes,
                          phase_enabled=row["phase_enabled"],
                          mechanism_implemented=row["mechanism_implemented"],
                          forbidden_l5=row["forbidden_l5"], non_goal=row["non_goal"])


def _secrets(section) -> Optional[Tuple[str, ...]]:
    if not isinstance(section, dict) or set(section) != {"user_home_relative"}:
        return None
    entries = section["user_home_relative"]
    if not (isinstance(entries, list) and entries):
        return None
    out = []
    for e in entries:
        if not (isinstance(e, str) and e and e == e.strip()):
            return None
        if e.startswith(("\\", "/")) or ":" in e or ".." in e.replace("\\", "/").split("/"):
            return None  # must stay a relative path inside <USER_HOME>
        out.append(e)
    if len({e.lower() for e in out}) != len(out):
        return None
    return tuple(out)


def parse(raw: bytes, known_hashes: Optional[Mapping[int, str]] = None):
    """Parse policy bytes. known_hashes maps policy_version to the SHA-256 already
    recorded for it; the same version with a different hash is POLICY_HASH_MISMATCH
    (ADR-0003 D6)."""
    try:
        data = canonical_text_bytes(raw)
    except ConfigError:
        return _fail("POLICY_FORMAT_INVALID")
    try:
        doc = tomllib.loads(data.decode("utf-8"))
    except tomllib.TOMLDecodeError:
        return _fail("POLICY_FORMAT_INVALID")

    if set(doc) != TOP_KEYS:
        return _fail("POLICY_FORMAT_INVALID")
    schema, version = doc["schema_version"], doc["policy_version"]
    if not _is_int(schema) or schema not in SUPPORTED_POLICY_SCHEMAS:
        return _fail("POLICY_FORMAT_INVALID")
    if not _is_int(version) or version < 1:
        return _fail("POLICY_VERSION_UNKNOWN")

    rows = doc["capability"]
    if not (isinstance(rows, list) and rows):
        return _fail("POLICY_FORMAT_INVALID")
    rules = []
    for row in rows:
        rule = _rule(row)
        if rule is None:
            return _fail("POLICY_FORMAT_INVALID")
        rules.append(rule)
    if len({r.name for r in rules}) != len(rules):
        return _fail("POLICY_FORMAT_INVALID")

    secrets = _secrets(doc["secret_locations"])
    if secrets is None:
        return _fail("POLICY_FORMAT_INVALID")

    digest = hashlib.sha256(data).hexdigest()
    if known_hashes is not None and version in known_hashes and known_hashes[version] != digest:
        return _fail("POLICY_HASH_MISMATCH")

    snapshot = PolicySnapshot(schema_version=schema, policy_version=version, sha256=digest,
                              rules=tuple(rules))
    return LoadedPolicy(snapshot=snapshot, secret_locations=secrets)


def load(path: str, known_hashes: Optional[Mapping[int, str]] = None):
    """Read and parse a policy file. Any read error is POLICY_UNAVAILABLE."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return _fail("POLICY_UNAVAILABLE")
    return parse(raw, known_hashes)
