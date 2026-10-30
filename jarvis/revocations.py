"""Revocation-list loader: stage 1 of ADR-0003 D1 for the revocation list (D7).

The list is one TOML file in the governance zone, read for every evaluation and
never cached. It returns a RevocationSnapshot, or a RevocationFailure when the
file is missing, unreadable or malformed. The evaluator turns a failure into DENY
(REVOCATION_UNAVAILABLE), so the control plane fails closed until RK has put a
valid list in place. An empty list is valid and means nothing is revoked.

File format (schema 1). The format is an engineering choice made for Phase 1,
because no ADR fixes it (ADR-0004 D7 leaves schema versions to engineering):

    schema_version = 1
    capabilities = ["SEARCH_WEB"]          # capability names
    projects = ["swarag"]                  # registry IDs
    contract_hashes = ["<64 hex>"]         # SHA-256 of a contract file

Changing the list is a permission change made by RK (ADR-0004 D6, trigger G-04).
"""

import os
import tomllib
from typing import Union

from .config import ConfigError, canonical_text_bytes
from .model import (CAPABILITY_RE, PROJECT_ID_RE, SHA256_RE, RevocationFailure,
                    RevocationSnapshot)

FILE_NAME = "revocations.toml"
SUPPORTED_SCHEMAS = frozenset({1})
KEYS = frozenset({"schema_version", "capabilities", "projects", "contract_hashes"})

_FAIL = RevocationFailure()


def path_in(governance_zone: str) -> str:
    return os.path.join(governance_zone, FILE_NAME)


def _strings(value, pattern) -> Union[frozenset, None]:
    if not isinstance(value, list):
        return None
    if not all(isinstance(v, str) and pattern.match(v) for v in value):
        return None
    return frozenset(value)


def parse(raw: bytes) -> Union[RevocationSnapshot, RevocationFailure]:
    try:
        data = canonical_text_bytes(raw)
        doc = tomllib.loads(data.decode("utf-8"))
    except (ConfigError, tomllib.TOMLDecodeError):
        return _FAIL
    if set(doc) != KEYS:
        return _FAIL
    schema = doc["schema_version"]
    if not isinstance(schema, int) or isinstance(schema, bool) or schema not in SUPPORTED_SCHEMAS:
        return _FAIL
    capabilities = _strings(doc["capabilities"], CAPABILITY_RE)
    projects = _strings(doc["projects"], PROJECT_ID_RE)
    hashes = _strings(doc["contract_hashes"], SHA256_RE)
    if capabilities is None or projects is None or hashes is None:
        return _FAIL
    return RevocationSnapshot(capabilities=capabilities, projects=projects, contract_hashes=hashes)


def load(path: str) -> Union[RevocationSnapshot, RevocationFailure]:
    """Read and parse the list. Any read error is a RevocationFailure."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return _FAIL
    return parse(raw)
