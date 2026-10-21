"""Control-plane configuration loader (ADR-0002 D1 row 1; ADR-0004 D2).

Configuration comes from one TOML file in the governance zone. The loader reads
no environment variable, rejects secret-like keys and unknown keys, and hashes
the canonical bytes (UTF-8, CRLF converted to LF, a lone CR rejected).
"""

import hashlib
import ntpath
import re
import tomllib
from dataclasses import dataclass

DEFAULT_CONFIG_PATH = "D:\\JARVIS\\governance\\jarvis.toml"
SUPPORTED_SCHEMAS = frozenset({1})

REQUIRED_KEYS = frozenset({"schema_version", "data_root", "governance_zone", "user_home"})
OPTIONAL_KEYS = frozenset({"busy_timeout_ms"})
SECRET_LIKE = re.compile(r"(secret|token|passw|credential|api_?key|private_?key|auth)", re.I)


class ConfigError(ValueError):
    """Carries a fixed code, never a value from the file."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Config:
    """user_home is the <USER_HOME> of ADR-0008 D1. It comes only from this file,
    never from an environment variable (ADR-0006 3.3)."""

    schema_version: int
    data_root: str
    governance_zone: str
    user_home: str
    busy_timeout_ms: int
    sha256: str


def canonical_text_bytes(raw: bytes) -> bytes:
    """UTF-8 with LF line endings. A lone CR is an error (ADR-0003 D4)."""
    data = raw.replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ConfigError("CONFIG_FORMAT_INVALID")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise ConfigError("CONFIG_FORMAT_INVALID") from None
    return data


def _absolute_windows_path(value) -> bool:
    return isinstance(value, str) and bool(re.match(r"^[A-Za-z]:\\", value)) and ntpath.isabs(value)


def parse(raw: bytes) -> Config:
    data = canonical_text_bytes(raw)
    try:
        doc = tomllib.loads(data.decode("utf-8"))
    except tomllib.TOMLDecodeError:
        raise ConfigError("CONFIG_FORMAT_INVALID") from None

    for key in doc:
        if SECRET_LIKE.search(key):
            raise ConfigError("CONFIG_SECRET_LIKE_KEY")
    keys = set(doc)
    if not REQUIRED_KEYS <= keys or keys - REQUIRED_KEYS - OPTIONAL_KEYS:
        raise ConfigError("CONFIG_KEYS_INVALID")

    schema = doc["schema_version"]
    if not isinstance(schema, int) or isinstance(schema, bool) or schema not in SUPPORTED_SCHEMAS:
        raise ConfigError("CONFIG_SCHEMA_UNKNOWN")
    if not all(_absolute_windows_path(doc[k]) for k in ("data_root", "governance_zone", "user_home")):
        raise ConfigError("CONFIG_PATH_INVALID")
    timeout = doc.get("busy_timeout_ms", 5000)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 60000:
        raise ConfigError("CONFIG_VALUE_INVALID")

    return Config(schema_version=schema, data_root=doc["data_root"],
                  governance_zone=doc["governance_zone"], user_home=doc["user_home"],
                  busy_timeout_ms=timeout, sha256=hashlib.sha256(data).hexdigest())


def load(path: str) -> Config:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        raise ConfigError("CONFIG_UNAVAILABLE") from None
    return parse(raw)
