"""The rules for a request that arrives through the private network's proxy (ADR-0011 Amendment 4, A4.6.3 and A4.6.4).

Pure decisions, no sockets. Through the proxy every request reaches the dashboard from 127.0.0.1, so the source address says
nothing: a request is REMOTE if its Host is the one private hostname or it carries any proxy or private-network identity header,
and it is LOCAL only with a loopback Host and none of those headers. A remote request needs all of: the exact private Host, the
proxy's login header equal to the one allowed login, the remote token (its SHA-256 must match the stored hash), and, on a
mutation, the exact Origin `https://<hostname>`. The page itself (`GET /`) cannot carry the token, because a URL fragment never
leaves the browser, so loading it needs the Host and the login only; every API call needs the token too.
Each of those headers must appear exactly once. Any failure is one generic refusal. Five failures in a minute switch remote
access off until the advisor is restarted; local use is untouched.
"""

import hashlib
import hmac
import threading
import time
from collections import deque
from typing import Optional

PROXY_PREFIXES = ("tailscale-", "x-forwarded-")
PROXY_NAMES = ("forwarded", "x-real-ip", "via")
LOGIN_HEADER = "Tailscale-User-Login"
TOKEN_HEADER = "X-JARVIS-Token"
FAIL_LIMIT = 5
FAIL_WINDOW_S = 60.0


def has_proxy_headers(headers) -> bool:
    for name in headers.keys():
        lower = name.lower()
        if lower.startswith(PROXY_PREFIXES) or lower in PROXY_NAMES:
            return True
    return False


def single(headers, name: str) -> Optional[str]:
    """The header's value if it appears exactly once, else None (missing, or repeated)."""
    values = headers.get_all(name)
    return values[0] if values is not None and len(values) == 1 else None


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RemoteGate:
    def __init__(self, hostname: str, login: str, token_sha256: str, clock=time.monotonic):
        self.hostname, self.login, self.token_sha256 = hostname, login, token_sha256
        self._clock = clock
        self._mu = threading.Lock()
        self._fails = deque()
        self._locked = False

    @property
    def locked(self) -> bool:
        return self._locked

    def origin(self) -> str:
        return "https://" + self.hostname

    def check(self, headers, post: bool, need_token: bool) -> bool:
        """True only if every required header is present once and correct. All the comparisons are made either way."""
        host = single(headers, "Host")
        login = single(headers, LOGIN_HEADER)
        origins = headers.get_all("Origin")
        if post:
            origin_ok = origins is not None and len(origins) == 1 and origins[0] == self.origin()
        else:
            origin_ok = origins is None or (len(origins) == 1 and origins[0] == self.origin())
        token_ok = True
        if need_token:
            given = single(headers, TOKEN_HEADER)
            token_ok = given is not None and hmac.compare_digest(token_digest(given).encode(), self.token_sha256.encode())
        host_ok = host is not None and hmac.compare_digest(host.encode(), self.hostname.encode())
        login_ok = login is not None and hmac.compare_digest(login.encode(), self.login.encode())
        return bool(host_ok and login_ok and origin_ok and token_ok)

    def fail(self) -> None:
        with self._mu:
            now = self._clock()
            self._fails.append(now)
            while self._fails and now - self._fails[0] > FAIL_WINDOW_S:
                self._fails.popleft()
            if len(self._fails) >= FAIL_LIMIT:
                self._locked = True
