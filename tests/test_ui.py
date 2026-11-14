"""Stage A dashboard (ADR-0011 D2, D3, D4; Beta plan BU-1, BU-1b, BU-2, BU-3).

Static checks on ui/ and interaction/, the child-process helper, the ring logic,
and the server's refusals, run against a temporary JARVIS install.
"""

import ast
import http.client
import io
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

from interaction import child
from jarvis import cli
from tests import astguard
from ui import page, ring
from ui.server import DashboardServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_ROOTS = {"socket", "ssl", "http", "urllib", "socketserver", "asyncio", "xmlrpc", "ftplib",
                 "smtplib", "poplib", "imaplib", "telnetlib", "webbrowser", "wsgiref", "selectors"}


def py_files(folder):
    root = os.path.join(REPO, folder)
    return sorted(os.path.join(root, f) for f in os.listdir(root) if f.endswith(".py"))


def parse(path):
    with open(path, "r", encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def imported(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


class StaticTests(unittest.TestCase):
    def test_only_the_four_named_process_creating_references_and_no_shell(self):
        """interaction/child.py starts the control plane (ADR-0011 D2); interaction/voice_child.py starts the
        voice worker (ADR-0012 D2); interaction/fetch_child.py starts the public-data fetcher (ADR-0014 D2); interaction/launch_child.py starts one catalog program (ADR-0015 D2). No other place in ui/, interaction/, advisor/ or voice/ may start a process."""
        sites = []
        for folder in ("ui", "interaction", "advisor", "voice"):
            for path in py_files(folder):
                for finding in astguard.scan(parse(path)):
                    with self.subTest(file=path, finding=finding):
                        self.assertNotIn(finding.rule, ("dynamic", "star-import"))
                    if finding.rule == "process":
                        sites.append((os.path.relpath(path, REPO), finding.name))
        self.assertEqual(sites, [(os.path.join("interaction", "child.py"), "subprocess.run"),
                                 (os.path.join("interaction", "fetch_child.py"), "subprocess.run"),
                                 (os.path.join("interaction", "launch_child.py"), "subprocess.Popen"),
                                 (os.path.join("interaction", "voice_child.py"), "subprocess.Popen")])
        for name in ("child.py", "voice_child.py", "fetch_child.py", "launch_child.py"):
            tree = parse(os.path.join(REPO, "interaction", name))
            resolve = astguard.resolver(tree)
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and astguard.is_process(resolve(n.func) or "")]
            self.assertEqual(len(calls), 1, name)
            self.assertNotIn("shell", [kw.arg for kw in calls[0].keywords], name)

    def test_network_imports_are_limited(self):
        for folder, allowed in (("ui", {"http.server"}), ("interaction", set()), ("voice", set())):
            for path in py_files(folder):
                for name in imported(parse(path)):
                    if name.split(".")[0] in NETWORK_ROOTS:
                        with self.subTest(file=path, module=name):
                            self.assertIn(name, allowed)

    def test_only_the_fetcher_package_may_use_network_modules_or_its_network_code(self):
        """ADR-0014 D2. fetcher/ is the one place with socket, ssl, http.client or urllib; nothing else imports
        fetcher.net, fetcher.lookups or fetcher.rss (the fetcher runs as its own program), and the control plane
        never imports fetcher at all. fetcher.keys is plain data and may be imported by the intent layer."""
        fetcher_files = py_files("fetcher")
        self.assertTrue(any(f.endswith("net.py") for f in fetcher_files))
        for folder in ("jarvis", "advisor", "interaction", "voice", "ui"):
            files = []
            for dirpath, _d, names in os.walk(os.path.join(REPO, folder)):
                files += [os.path.join(dirpath, n) for n in names if n.endswith(".py")]
            for path in files:
                for name in imported(parse(path)):
                    with self.subTest(file=path, module=name):
                        if folder == "jarvis":
                            self.assertNotEqual(name.split(".")[0], "fetcher")
                        elif name.split(".")[0] == "fetcher":
                            self.assertEqual(name, "fetcher.keys" if name != "fetcher" else "fetcher")
        for path in fetcher_files:
            for name in imported(parse(path)):
                self.assertNotIn(name.split(".")[0], {"jarvis", "advisor", "interaction", "voice", "ui", "subprocess", "multiprocessing", "ctypes"}, path)
            for finding in astguard.scan(parse(path)):
                self.assertNotIn(finding.rule, ("process", "dynamic", "star-import"), (path, finding))

    def test_control_plane_does_not_import_surfaces(self):
        for dirpath, _d, files in os.walk(os.path.join(REPO, "jarvis")):
            for f in files:
                if f.endswith(".py"):
                    for name in imported(parse(os.path.join(dirpath, f))):
                        self.assertNotIn(name.split(".")[0], {"ui", "interaction"})

    def test_ui_does_not_import_control_plane_internals(self):
        for path in py_files("ui") + py_files("interaction"):
            for name in imported(parse(path)):
                with self.subTest(file=path, module=name):
                    self.assertNotEqual(name.split(".")[0], "jarvis")


class ChildCommandTests(unittest.TestCase):
    def test_command_uses_the_running_interpreter_by_absolute_path(self):
        cfg = os.path.join(tempfile.gettempdir(), "x.toml")
        cmd = child.command(cfg, ["status"])
        self.assertEqual(cmd[0], sys.executable)
        self.assertTrue(os.path.isabs(cmd[0]))
        self.assertEqual(cmd[1:7], ["-E", "-s", "-m", "jarvis", "--config", cfg])
        self.assertEqual(cmd[7:], ["status"])

    def test_refusals(self):
        with self.assertRaises(child.ChildRefused):
            child.command("relative.toml", [])
        with self.assertRaises(child.ChildRefused):
            child.command(os.path.abspath("x.toml"), ["bad\x00arg"])
        fake = types.SimpleNamespace(version_info=(3, 10, 0), executable=sys.executable)
        with mock.patch.object(child, "sys", fake):
            with self.assertRaises(child.ChildRefused):
                child.command(os.path.abspath("x.toml"), [])

    def test_environment_is_minimal(self):
        self.assertTrue(set(child.environment()) <= {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"})


class RingTests(unittest.TestCase):
    def test_states_come_from_records(self):
        self.assertEqual(ring.derive(0, "tasks: none\n", 0)["state"], "IDLE")
        self.assertEqual(ring.derive(0, "a RUNNING L2 p\nb BLOCKED L2 p\n", 0)["state"], "RUNNING")
        self.assertEqual(ring.derive(0, "a BLOCKED L2 p\nb COMPLETED_UNVERIFIED L2 p\n", 0)["state"], "WAITING")
        done = ring.derive(0, "a FAILED L2 p\nb COMPLETED_UNVERIFIED L2 p\ntasks: 2\n", 0)
        self.assertEqual(done["state"], "COMPLETED")
        self.assertIn("not verified", done["detail"])
        self.assertEqual(ring.derive(0, "a CANCELLED L2 p\n", 0)["state"], "CANCELLED")
        self.assertEqual(ring.derive(7, "", 0)["state"], "ERROR")
        self.assertEqual(ring.derive(0, "a RUNNING L2 p\n", 5)["state"], "AUDIT_FAULT")

    def test_ring_never_claims_voice_or_thinking(self):
        for text in ("", "a RUNNING L2 p\n", "a DEFERRED L4 p\n"):
            self.assertNotIn(ring.derive(0, text, 0)["state"], {"LISTENING", "SPEAKING", "INTERPRETING", "THINKING"})


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = cls.tmp.name
        data, gov, home = (os.path.join(base, n) for n in ("data", "gov", "home"))
        for d in (data, gov, home):
            os.makedirs(d)
        cls.cfg = os.path.join(base, "jarvis-test.toml")
        with open(cls.cfg, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\nuser_home = '%s'\n" % (data, gov, home))
        with open(os.path.join(gov, "revocations.toml"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("schema_version = 1\ncapabilities = []\nprojects = []\ncontract_hashes = []\n")
        code = cli.main(["--config", cls.cfg, "init"], io.StringIO())
        assert code == cli.EXIT_OK, code
        cls.server = DashboardServer(cls.cfg)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def request(self, path, method="GET", token=True, host=None, origin=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=90)
        headers = {"Host": host or "127.0.0.1:%d" % self.port}
        if token:
            headers["X-JARVIS-Token"] = self.server.token if token is True else token
        if origin:
            headers["Origin"] = origin
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp, data

    def test_voice_route_needs_the_token_and_reports_only_a_fresh_real_signal(self):
        self.assertEqual(self.request("/api/voice", token=False)[0].status, 403)
        self.assertEqual(self.request("/api/voice", method="POST")[0].status, 405)
        saved = self.server.voice_path
        try:
            with tempfile.TemporaryDirectory() as tmp:
                self.server.voice_path = os.path.join(tmp, "voice_state.json")
                self.assertEqual(json.loads(self.request("/api/voice")[1]), {"state": "IDLE"})     # no signal: idle
                with open(self.server.voice_path, "w", encoding="utf-8") as fh:
                    json.dump({"state": "LISTENING", "at": time.time()}, fh)
                self.assertEqual(json.loads(self.request("/api/voice")[1]), {"state": "LISTENING"})
                with open(self.server.voice_path, "w", encoding="utf-8") as fh:
                    json.dump({"state": "LISTENING", "at": time.time() - 60}, fh)
                self.assertEqual(json.loads(self.request("/api/voice")[1]), {"state": "IDLE"})     # stale: idle
        finally:
            self.server.voice_path = saved

    def test_bound_to_loopback_on_a_random_port(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertNotEqual(self.port, 0)
        self.assertNotIn("?", self.server.url)
        self.assertIn("#t=", self.server.url)

    def test_preview_dock_is_labelled_and_never_a_record(self):
        _, data = self.request("/", token=False)
        page = data.decode("utf-8")
        for needle in ("COMING LATER (PREVIEW, NOT RECORDS)", "preview-memory", "preview-research", "preview-evidence", "drawDock("):
            self.assertIn(needle, page)
        self.assertIn('n.kind === "preview" ? "PREVIEW  not built yet"', page)   # the inspector never calls a preview a record

    def test_page_has_strict_headers_and_no_cors(self):
        resp, data = self.request("/", token=False)
        self.assertEqual(resp.status, 200)
        policy = resp.getheader("Content-Security-Policy")
        self.assertIn("default-src 'none'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn("unsafe-inline", policy)
        self.assertEqual(resp.getheader("X-Content-Type-Options"), "nosniff")
        self.assertIsNone(resp.getheader("Access-Control-Allow-Origin"))
        self.assertIn(b"J.A.R.V.I.S.", data)
        self.assertNotIn(b"innerHTML", data)

    def test_token_is_required_for_data(self):
        self.assertEqual(self.request("/api/status", token=False)[0].status, 403)
        self.assertEqual(self.request("/api/status", token="wrong")[0].status, 403)
        resp, data = self.request("/api/status")
        self.assertEqual(resp.status, 200)
        body = json.loads(data)
        self.assertEqual(body["exit"], 0)
        self.assertIn("JARVIS status", body["text"])

    def test_host_and_origin_must_be_exact(self):
        self.assertEqual(self.request("/api/status", host="evil.example:%d" % self.port)[0].status, 403)
        self.assertEqual(self.request("/api/status", host="127.0.0.1:1")[0].status, 403)
        self.assertEqual(self.request("/api/status", origin="http://evil.example")[0].status, 403)
        self.assertEqual(self.request("/api/status", origin="http://127.0.0.1:%d" % self.port)[0].status, 200)
        self.assertEqual(self.request("/api/status", host="localhost:%d" % self.port)[0].status, 200)

    def test_read_only_and_strict_routes(self):
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            self.assertEqual(self.request("/api/status", method=method)[0].status, 405)
        self.assertEqual(self.request("/api/nope")[0].status, 404)
        self.assertEqual(self.request("/api/task/BAD..ID!")[0].status, 400)
        self.assertEqual(self.request("/api/task/a/b")[0].status, 404)
        self.assertEqual(self.request("/api/status", body=b"x")[0].status, 400)

    def test_ring_for_an_empty_store_is_idle(self):
        resp, data = self.request("/api/ring")
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(data)["state"], "IDLE")

    def test_galaxy_route_needs_the_token_and_is_read_only(self):
        self.assertEqual(self.request("/api/galaxy", token=False)[0].status, 403)
        self.assertEqual(self.request("/api/galaxy", method="POST")[0].status, 405)
        resp, data = self.request("/api/galaxy")
        self.assertEqual(resp.status, 200)
        body = json.loads(data)
        self.assertEqual(body["counts"]["live_nodes"], 0)  # an empty store: no invented records
        self.assertEqual({n["kind"] for n in body["nodes"]}, {"preview"})

    def test_every_listed_route_runs_its_command(self):
        for name in ("doctor", "projects", "tasks", "notes", "results", "audit", "resume"):
            with self.subTest(route=name):
                resp, data = self.request("/api/" + name)
                self.assertEqual(resp.status, 200)
                self.assertIn("exit", json.loads(data))


class PageTests(unittest.TestCase):
    def test_csp_without_nonce_allows_no_script(self):
        self.assertIn("script-src 'none'", page.csp(""))
        self.assertIn("script-src 'nonce-abc'", page.csp("abc"))
