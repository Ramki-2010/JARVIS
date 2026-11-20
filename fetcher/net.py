"""One bounded HTTPS GET to a fixed host (ADR-0014 D3). Nothing else in JARVIS may import these modules."""

import http.client
import ipaddress
import ssl
import time

ALLOWED_HOSTS = frozenset({
    "api.open-meteo.com", "hacker-news.firebaseio.com", "www.thehindu.com", "indianexpress.com",
    "feeds.feedburner.com", "timesofindia.indiatimes.com", "www.hindustantimes.com",
})
MAX_BYTES = 512 * 1024
TIMEOUT_S = 8.0
USER_AGENT = "JARVIS-local"


class FetchFailed(Exception):
    """Carries a fixed code: REFUSED, NETWORK, TIMEOUT, REDIRECT, STATUS, TOO_LARGE."""

    def __init__(self, code: str, host: str = ""):
        super().__init__(code)
        self.code = code
        self.host = host


def _embedded(ip):
    """The IPv4 addresses hidden inside an IPv6 one (mapped, 6to4, Teredo, the NAT64 prefix), else an empty list."""
    if ip.version != 6:
        return []
    found = []
    if ip.ipv4_mapped is not None:
        found.append(ip.ipv4_mapped)
    if ip.sixtofour is not None:
        found.append(ip.sixtofour)
    if ip.teredo is not None:
        found.extend(ip.teredo)
    if ip in ipaddress.ip_network("64:ff9b::/96"):
        found.append(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    return found


def _public(ip) -> bool:
    """Globally routable and not multicast or reserved (Python's own `is_global` still lets some multicast ranges through)."""
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_unspecified or ip.is_loopback or ip.is_link_local or ip.is_private)


def require_public(address: str, host: str = "") -> None:
    """ADR-0014 Amendment 4. The address the connection really reached must be a public one (not loopback, private, link-local,
    shared/CGNAT, multicast, reserved, or a private IPv4 hidden inside an IPv6 form). Anything unreadable is refused."""
    try:
        ip = ipaddress.ip_address(str(address).split("%", 1)[0])
    except ValueError:
        raise FetchFailed("REFUSED", host) from None
    if not _public(ip) or any(not _public(inner) for inner in _embedded(ip)):
        raise FetchFailed("REFUSED", host)


def get(host: str, path: str, connection=None) -> bytes:
    """GET https://host/path. HTTPS only, certificate checked, no redirect, no cookie, no credentials, at most
    MAX_BYTES, one overall deadline. `connection` is a test seam: a factory taking (host, timeout)."""
    if host not in ALLOWED_HOSTS or not path.startswith("/") or any(c in path for c in " \r\n\t\x00"):
        raise FetchFailed("REFUSED", host)
    deadline = time.monotonic() + TIMEOUT_S
    factory = connection or (lambda h, t: http.client.HTTPSConnection(h, 443, timeout=t, context=ssl.create_default_context()))
    conn = factory(host, TIMEOUT_S)
    try:
        if connection is None:
            conn.connect()   # connect first, so the address that was really reached can be checked before anything is sent
        sock = getattr(conn, "sock", None)
        if sock is not None:
            require_public(sock.getpeername()[0], host)
        elif connection is None:
            raise FetchFailed("REFUSED", host)   # no socket to inspect: fail closed
        conn.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity", "Connection": "close"})
        resp = conn.getresponse()
        if 300 <= resp.status < 400:
            raise FetchFailed("REDIRECT", host)
        if resp.status != 200:
            raise FetchFailed("STATUS", host)
        length = resp.getheader("Content-Length")
        if length and length.isdigit() and int(length) > MAX_BYTES:
            raise FetchFailed("TOO_LARGE", host)
        chunks, total = [], 0
        while True:
            if time.monotonic() > deadline:
                raise FetchFailed("TIMEOUT", host)
            block = resp.read(16 * 1024)
            if not block:
                return b"".join(chunks)
            total += len(block)
            if total > MAX_BYTES:
                raise FetchFailed("TOO_LARGE", host)
            chunks.append(block)
    except FetchFailed:
        raise
    except TimeoutError:
        raise FetchFailed("TIMEOUT", host) from None
    except (OSError, http.client.HTTPException, ssl.SSLError):
        raise FetchFailed("NETWORK", host) from None
    finally:
        try:
            conn.close()
        except Exception:
            pass
