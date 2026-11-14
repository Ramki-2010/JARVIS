"""Stage A dashboard server (ADR-0011 D3). Read-only; every route runs one CLI command.

Rules held here: bound to 127.0.0.1 on a random port; a per-launch token in a
request header (never in a query string); Host and Origin accepted only as
exactly this launch's 127.0.0.1 or localhost address; no CORS; a strict CSP; GET
only; no request body; a bounded request rate; JSON output, inserted by the page
as text. The server keeps no state of its own beyond the token.
"""

import hmac
import http.server
import json
import re
import secrets
import threading
import time
import types
from collections import deque

from interaction import child
from ui import galaxy, page, ring, voicesignal

ROUTES = {
    "status": ["status"],
    "doctor": ["doctor"],
    "projects": ["project", "list"],
    "tasks": ["task", "list"],
    "notes": ["note", "list"],
    "results": ["result", "list"],
    "audit": ["audit", "verify"],
    "resume": ["resume"],
}
DETAIL = {"project": ["project", "show"], "task": ["task", "show"], "note": ["note", "show"]}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
TOKEN_HEADER = "X-JARVIS-Token"
RATE_WINDOW_S = 5.0
RATE_MAX = 40


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "JARVIS"
    sys_version = ""

    def log_message(self, fmt, *args):  # never print requests (the token travels in a header)
        pass

    # ----- checks
    def _allowed_hosts(self):
        port = self.server.server_address[1]
        return {"127.0.0.1:%d" % port, "localhost:%d" % port}

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in self._allowed_hosts()

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin in {"http://" + h for h in self._allowed_hosts()}

    def _token_ok(self) -> bool:
        given = self.headers.get(TOKEN_HEADER, "")
        return hmac.compare_digest(given.encode(), self.server.token.encode())

    def _rate_ok(self) -> bool:
        with self.server.rate_lock:
            now = time.monotonic()
            hits = self.server.rate_hits
            while hits and now - hits[0] > RATE_WINDOW_S:
                hits.popleft()
            if len(hits) >= RATE_MAX:
                return False
            hits.append(now)
            return True

    # ----- responses
    def _send(self, code: int, body: bytes, ctype: str, nonce: str = ""):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", page.csp(nonce))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _refuse(self, code: int, reason: str):
        self._json(code, {"error": reason})

    # ----- methods
    def do_GET(self):
        if not self._host_ok():
            return self._refuse(403, "host not allowed")
        if not self._origin_ok():
            return self._refuse(403, "origin not allowed")
        if self.headers.get("Content-Length", "0") not in ("", "0"):
            return self._refuse(400, "no request body allowed")
        if not self._rate_ok():
            return self._refuse(429, "too many requests")
        path = self.path.split("?", 1)[0]
        if path == "/":
            nonce = secrets.token_urlsafe(16)
            return self._send(200, page.html(nonce).encode("utf-8"), "text/html; charset=utf-8", nonce)
        if not path.startswith("/api/"):
            return self._refuse(404, "not found")
        if not self._token_ok():
            return self._refuse(403, "token required")
        parts = path[len("/api/"):].split("/")
        if len(parts) == 1 and parts[0] in ROUTES:
            return self._json(200, self._run(ROUTES[parts[0]]))
        if len(parts) == 1 and parts[0] == "ring":
            tasks = child.run(self.server.config, ["task", "list"])
            audit = child.run(self.server.config, ["audit", "verify"])
            return self._json(200, ring.derive(tasks.code, tasks.text, audit.code))
        if len(parts) == 1 and parts[0] == "voice":
            return self._json(200, voicesignal.read(self.server.voice_path))
        if len(parts) == 1 and parts[0] == "galaxy":
            return self._json(200, self._galaxy())
        if len(parts) == 2 and parts[0] in DETAIL:
            if not ID_RE.match(parts[1]):
                return self._refuse(400, "invalid id")
            return self._json(200, self._run(DETAIL[parts[0]] + [parts[1]]))
        return self._refuse(404, "not found")

    def _run(self, args):
        result = child.run(self.server.config, args)
        return {"command": " ".join(args), "exit": result.code, "text": result.text,
                "truncated": result.truncated}

    def _galaxy(self):
        """The galaxy is drawn from the same read-only list commands as the panels; a failed list shows as an error."""
        outputs = {name: child.run(self.server.config, ROUTES[name]) for name in ("projects", "tasks", "notes", "results")}
        # A store with no project registry yet answers REGISTRY_MISSING: that truly means no projects, not a fault.
        if outputs["projects"].code != 0 and "REGISTRY_MISSING" in outputs["projects"].text:
            outputs["projects"] = types.SimpleNamespace(code=0, text="projects: 0\n")
        failed = [name for name, result in outputs.items() if result.code != 0]
        if failed:
            return {"error": "could not read: " + ", ".join(failed), "nodes": [], "links": [], "counts": {}}
        return galaxy.build(outputs["projects"].text, outputs["tasks"].text, outputs["notes"].text, outputs["results"].text)

    def _method_not_allowed(self):
        self._refuse(405, "read-only: GET only")

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = _method_not_allowed


class DashboardServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, config: str, voice_path: str = ""):
        super().__init__(("127.0.0.1", 0), Handler)
        child.command(config, [])  # refuse a relative config or a wrong interpreter at start
        self.config = config
        self.voice_path = voice_path or voicesignal.default_path(config)
        self.token = secrets.token_urlsafe(32)
        self.rate_hits = deque()
        self.rate_lock = threading.Lock()

    @property
    def url(self) -> str:
        return "http://127.0.0.1:%d/#t=%s" % (self.server_address[1], self.token)
