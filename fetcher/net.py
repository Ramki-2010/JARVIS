"""One bounded HTTPS GET to a fixed host (ADR-0014 D3). Nothing else in JARVIS may import these modules."""

import http.client
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


def get(host: str, path: str, connection=None) -> bytes:
    """GET https://host/path. HTTPS only, certificate checked, no redirect, no cookie, no credentials, at most
    MAX_BYTES, one overall deadline. `connection` is a test seam: a factory taking (host, timeout)."""
    if host not in ALLOWED_HOSTS or not path.startswith("/") or any(c in path for c in " \r\n\t\x00"):
        raise FetchFailed("REFUSED", host)
    deadline = time.monotonic() + TIMEOUT_S
    factory = connection or (lambda h, t: http.client.HTTPSConnection(h, 443, timeout=t, context=ssl.create_default_context()))
    conn = factory(host, TIMEOUT_S)
    try:
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
