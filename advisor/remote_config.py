"""RK's private remote-access settings (ADR-0011 Amendment 4, A4.6.1 and A4.6.6).

One small file in RK's governance folder, outside the repository: the one private hostname the phone uses, the one login the
private network must report, the fixed port, and the SHA-256 of the remote token (never the token). JARVIS only reads it, and
only when the advisor is started with `--remote-file`. Anything missing, malformed or empty means remote access stays OFF; there
is no default and no guess. A committed example with placeholders is `docs/examples/remote.example.toml`.
"""

import re
import tomllib
from typing import NamedTuple

KEYS = frozenset({"hostname", "login", "port", "token_sha256"})
HOSTNAME = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+ts\.net$")
LOGIN = re.compile(r"^[A-Za-z0-9._@+-]{1,100}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PORT_MIN, PORT_MAX = 1024, 65535


class RemoteConfigError(ValueError):
    """Why remote access stays off. The text is a short reason, never the file's content."""


class RemoteConfig(NamedTuple):
    hostname: str
    login: str
    port: int
    token_sha256: str


def parse(text: str) -> RemoteConfig:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        raise RemoteConfigError("the remote settings file is not valid TOML") from None
    if set(data) != {"remote"} or not isinstance(data["remote"], dict):
        raise RemoteConfigError("the remote settings file must hold exactly one [remote] table")
    table = data["remote"]
    if set(table) != KEYS:
        raise RemoteConfigError("the [remote] table must hold exactly: " + ", ".join(sorted(KEYS)))
    hostname, login, port, digest = table["hostname"], table["login"], table["port"], table["token_sha256"]
    if not isinstance(hostname, str) or not HOSTNAME.match(hostname):
        raise RemoteConfigError("hostname must be one lower-case private-network name ending in .ts.net, with no port")
    if not isinstance(login, str) or not LOGIN.match(login):
        raise RemoteConfigError("login must be the private network's login name (letters, digits and . _ @ + -)")
    if isinstance(port, bool) or not isinstance(port, int) or not PORT_MIN <= port <= PORT_MAX:
        raise RemoteConfigError("port must be a whole number from %d to %d" % (PORT_MIN, PORT_MAX))
    if not isinstance(digest, str) or not digest:
        raise RemoteConfigError("no remote token has been made yet (run scripts\\make_remote_token.py)")
    if not SHA256.match(digest):
        raise RemoteConfigError("token_sha256 must be 64 lower-case hexadecimal characters")
    return RemoteConfig(hostname, login, port, digest)


def load(path: str) -> RemoteConfig:
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return parse(fh.read(65536))
    except OSError:
        raise RemoteConfigError("the remote settings file could not be read") from None
