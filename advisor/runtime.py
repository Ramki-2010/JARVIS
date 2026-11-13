"""A loopback-only client for a local Ollama server (ADR-0013 D2).

Uses `http.client` directly: no redirects, no proxy settings, no TLS, no name
lookup beyond the three loopback names. Output, time and size are capped. Any
failure raises `ModelUnavailable`; it never changes anything.
"""

import http.client
import json
import time
from typing import Dict, Iterator, List, Sequence

LOOPBACK = ("127.0.0.1", "localhost", "::1")
DEFAULT_PORT = 11434
MAX_REPLY_CHARS = 2000
MAX_LINE_BYTES = 256 * 1024


class ModelUnavailable(Exception):
    """The model could not answer. Conversation is off; nothing else changes."""


class OllamaClient:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 120.0):
        if host not in LOOPBACK:
            raise ValueError("the model runtime must be on the loopback interface, not %r" % (host,))
        self.host, self.port, self.timeout = host, int(port), float(timeout)

    def _connect(self, timeout: float) -> http.client.HTTPConnection:
        return http.client.HTTPConnection(self.host, self.port, timeout=timeout)

    def tags(self) -> List[Dict[str, str]]:
        try:
            conn = self._connect(10)
            try:
                conn.request("GET", "/api/tags")
                resp = conn.getresponse()
                body = resp.read(MAX_LINE_BYTES)
                if resp.status != 200:
                    raise ModelUnavailable("model server answered %d" % resp.status)
            finally:
                conn.close()
            models = json.loads(body.decode("utf-8")).get("models", [])
            return [{"name": str(m.get("name", "")), "digest": str(m.get("digest", ""))} for m in models]
        except ModelUnavailable:
            raise
        except (OSError, ValueError, http.client.HTTPException) as exc:
            raise ModelUnavailable("model server not reachable: %s" % type(exc).__name__) from exc

    def chat_stream(self, model: str, messages: Sequence[Dict[str, str]], options: Dict[str, object]) -> Iterator[str]:
        """Yield the reply in pieces. Raises ModelUnavailable on any failure or cap."""
        body = json.dumps({"model": model, "messages": list(messages), "stream": True,
                           "think": False, "keep_alive": "30m", "options": dict(options)}).encode("utf-8")
        deadline = time.monotonic() + self.timeout
        total = 0
        try:
            conn = self._connect(self.timeout)
            try:
                conn.request("POST", "/api/chat", body=body, headers={"Content-Type": "application/json"})
                resp = conn.getresponse()
                if resp.status != 200:
                    raise ModelUnavailable("model server answered %d" % resp.status)
                while True:
                    if time.monotonic() > deadline:
                        raise ModelUnavailable("the model took too long")
                    line = resp.readline(MAX_LINE_BYTES)
                    if not line:
                        return
                    obj = json.loads(line.decode("utf-8"))
                    if "error" in obj:
                        raise ModelUnavailable("the model reported an error")
                    piece = (obj.get("message") or {}).get("content", "")
                    if piece:
                        total += len(piece)
                        if total > MAX_REPLY_CHARS:
                            return
                        yield piece
                    if obj.get("done"):
                        return
            finally:
                conn.close()
        except ModelUnavailable:
            raise
        except (OSError, ValueError, http.client.HTTPException) as exc:
            raise ModelUnavailable("model call failed: %s" % type(exc).__name__) from exc
