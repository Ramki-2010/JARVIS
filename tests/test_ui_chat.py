"""The dashboard's conversation box (ADR-0011 Amendment 2, tests A2.6).

A fake `respond` stands in for the advisor, so these tests need no model, no microphone and no network.
Every refusal listed in the amendment is checked, plus the one-turn-at-a-time rule and the bridge.
"""

import http.client
import io
import json
import os
import tempfile
import threading
import time
import unittest

from advisor.bridge import QUIT_TEXT, page_responder
from jarvis import cli
from ui import page, turns
from ui.server import DashboardServer
from tests.test_ui import imported, parse, py_files


class FakeAdvisor:
    def __init__(self):
        self.gate = threading.Event()
        self.gate.set()
        self.seen = []

    def respond(self, text):
        self.seen.append(text)
        self.gate.wait(10)
        if text == "boom":
            raise RuntimeError("secret detail")
        if text == "markup":
            yield ("say", "<b onclick=x>bold</b>")
            return
        yield ("say", "You said: " + text)
        yield ("show", "shown only")
        yield ("quit", "ignored")  # not a kind the page may show


class Base(unittest.TestCase):
    respond = True

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
        assert cli.main(["--config", cls.cfg, "init"], io.StringIO()) == cli.EXIT_OK
        cls.advisor = FakeAdvisor()
        cls.server = DashboardServer(cls.cfg, "", cls.advisor.respond if cls.respond else None)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        self.advisor.gate.set()
        deadline = time.time() + 5
        while self.server.turns.busy() and time.time() < deadline:
            time.sleep(0.02)

    @property
    def origin(self):
        return "http://127.0.0.1:%d" % self.port

    def post(self, body, token=True, origin=True, host=None, ctype="application/json", path="/api/say", length=None, extra=None):
        self.server.rate_hits.clear()  # these tests are not about the rate limit
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        headers = {"Host": host or "127.0.0.1:%d" % self.port, "Content-Length": str(len(raw) if length is None else length)}
        if ctype is not None:
            headers["Content-Type"] = ctype
        if token:
            headers["X-JARVIS-Token"] = self.server.token if token is True else token
        if origin:
            headers["Origin"] = self.origin if origin is True else origin
        headers.update(extra or {})
        conn.request("POST", path, body=raw, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, (json.loads(data) if data else {})

    def get(self, path, token=True):
        self.server.rate_hits.clear()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        headers = {"Host": "127.0.0.1:%d" % self.port}
        if token:
            headers["X-JARVIS-Token"] = self.server.token
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, json.loads(data)

    def finish(self, number, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            status, body = self.get("/api/turn/%d" % number)
            if body.get("state") == "done":
                return body
            time.sleep(0.02)
        self.fail("the turn did not finish")


class SayRouteTests(Base):
    def test_a_good_line_runs_one_turn_and_returns_what_the_advisor_said(self):
        status, body = self.post({"text": "hello there"})
        self.assertEqual(status, 202)
        done = self.finish(body["turn"])
        self.assertEqual(done["events"], [["say", "You said: hello there"], ["show", "shown only"]])  # the quit event is not a page kind
        self.assertEqual(self.get("/api/chat")[1], {"enabled": True, "busy": False})

    def test_bad_bodies_are_refused_and_never_reach_the_advisor(self):
        before = len(self.advisor.seen)
        cases = {
            "unknown field": ({"text": "a", "extra": 1}, 400),
            "missing field": ({}, 400),
            "other field only": ({"line": "a"}, 400),
            "duplicate field": (b'{"text": "a", "text": "b"}', 400),
            "not an object": (b'["a"]', 400),
            "not json": (b"hello", 400),
            "not a string": ({"text": 5}, 400),
            "empty": ({"text": ""}, 400),
            "blank": ({"text": "   "}, 400),
            "over 400 chars": ({"text": "x" * 401}, 400),
            "control character": ({"text": "a\u0007b"}, 400),
            "newline": ({"text": "a\nb"}, 400),
            "oversize body": (b'{"text": "' + b"x" * 2000 + b'"}', 413),
        }
        for name, (body, expected) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.post(body)[0], expected)
        self.assertEqual(len(self.advisor.seen), before)

    def test_exactly_400_characters_is_allowed(self):
        status, body = self.post({"text": "y" * 400})
        self.assertEqual(status, 202)
        self.finish(body["turn"])

    def test_oversize_is_refused_from_the_declared_size_before_parsing(self):
        before = len(self.advisor.seen)
        self.assertEqual(self.post(b'{"text": "' + b"x" * 5000 + b'"}')[0], 413)
        self.assertEqual(len(self.advisor.seen), before)

    def test_wrong_content_type_and_chunked_and_missing_length(self):
        self.assertEqual(self.post({"text": "a"}, ctype="text/plain")[0], 415)
        self.assertEqual(self.post({"text": "a"}, ctype="application/json; charset=utf-8")[0], 415)  # strict: the exact type
        self.assertEqual(self.post({"text": "a"}, ctype=None)[0], 415)
        self.assertEqual(self.post({"text": "a"}, extra={"Transfer-Encoding": "chunked"})[0], 400)

    def test_host_origin_and_token_are_all_required(self):
        good = {"text": "a"}
        self.assertEqual(self.post(good, origin=False)[0], 403)                      # Origin is required on a mutation
        self.assertEqual(self.post(good, origin="http://evil.example")[0], 403)
        self.assertEqual(self.post(good, host="evil.example:%d" % self.port)[0], 403)
        self.assertEqual(self.post(good, host="127.0.0.1:1")[0], 403)
        self.assertEqual(self.post(good, token=False)[0], 403)                       # a correct Origin never replaces the token
        self.assertEqual(self.post(good, token="wrong")[0], 403)
        self.assertEqual(self.post(good, origin="http://localhost:%d" % self.port, host="localhost:%d" % self.port)[0], 202)

    def test_only_the_say_route_accepts_a_post(self):
        for path in ("/api/status", "/api/say/x", "/api/say?x=1", "/", "/api/turn/1"):
            with self.subTest(path):
                self.assertEqual(self.post({"text": "a"}, path=path)[0], 405)

    def test_a_second_line_while_a_turn_runs_is_refused_and_the_ring_signal_is_real(self):
        self.advisor.gate.clear()
        status, body = self.post({"text": "slow"})
        self.assertEqual(status, 202)
        deadline = time.time() + 5
        while not self.server.turns.busy() and time.time() < deadline:
            time.sleep(0.02)
        self.assertEqual(self.get("/api/chat")[1]["busy"], True)                      # INTERPRETING's only source
        self.assertEqual(self.get("/api/turn/%d" % body["turn"])[1]["state"], "running")
        self.assertEqual(self.post({"text": "second"})[0], 409)
        self.advisor.gate.set()
        self.finish(body["turn"])
        self.assertEqual(self.get("/api/chat")[1]["busy"], False)                     # and it clears the moment the turn ends

    def test_a_terminal_turn_blocks_the_page_the_same_way(self):
        with self.server.turns.exclusive():
            self.assertEqual(self.get("/api/chat")[1]["busy"], True)
            self.assertEqual(self.post({"text": "a"})[0], 409)
        self.assertEqual(self.get("/api/chat")[1]["busy"], False)

    def test_a_failed_turn_is_reported_without_leaking_detail(self):
        status, body = self.post({"text": "boom"})
        done = self.finish(body["turn"])
        self.assertEqual(done["events"][0][0], "error")
        self.assertIn("RuntimeError", done["events"][0][1])
        self.assertNotIn("secret detail", json.dumps(done))
        self.assertEqual(self.get("/api/chat")[1]["busy"], False)

    def test_markup_in_a_reply_stays_text(self):
        status, body = self.post({"text": "markup"})
        self.assertEqual(self.finish(body["turn"])["events"], [["say", "<b onclick=x>bold</b>"]])  # delivered as data; the page uses textContent
        html = page.html("n0nce")
        self.assertNotIn("innerHTML", html)
        self.assertNotIn("insertAdjacentHTML", html)
        self.assertNotIn("document.write", html)

    def test_turn_route_needs_the_token_and_refuses_unknown_turns(self):
        self.assertEqual(self.get("/api/turn/1", token=False)[0], 403)
        self.assertEqual(self.get("/api/turn/999999")[0], 404)
        self.assertEqual(self.get("/api/turn/abc")[0], 404)
        self.assertEqual(self.get("/api/chat", token=False)[0], 403)

    def test_only_the_last_few_turns_are_kept(self):
        numbers = []
        for i in range(turns.KEEP + 3):
            status, body = self.post({"text": "t%d" % i})
            self.finish(body["turn"])
            numbers.append(body["turn"])
        self.assertEqual(self.get("/api/turn/%d" % numbers[0])[0], 404)
        self.assertEqual(self.get("/api/turn/%d" % numbers[-1])[0], 200)


class ReadOnlyWithoutAdvisorTests(Base):
    respond = False

    def test_the_route_is_absent_and_the_page_is_told_so(self):
        self.assertEqual(self.post({"text": "a"})[0], 405)
        self.assertEqual(self.get("/api/chat")[1], {"enabled": False, "busy": False})
        self.assertEqual(self.get("/api/turn/1")[0], 404)


class ParseTests(unittest.TestCase):
    def test_parse_say_returns_the_text_untouched(self):
        self.assertEqual(turns.parse_say(b'{"text": "  hi \\u00e9  "}'), "  hi é  ")

    def test_non_utf8_is_refused(self):
        with self.assertRaises(turns.BadRequest):
            turns.parse_say(b'{"text": "\xff"}')

    def test_clean_removes_control_characters_but_keeps_newlines_and_bounds_length(self):
        self.assertEqual(turns.clean("say", "a\x07b\nc"), ("say", "a b\nc"))
        self.assertEqual(len(turns.clean("say", "z" * 10000)[1]), turns.MAX_EVENT)


class BridgeTests(unittest.TestCase):
    class Ctl:
        provenance = "spoken"

        def __init__(self):
            self.during = None

        def respond(self, text):
            self.during = self.provenance
            yield ("say", "ok")
            yield ("quit", "")

    def test_the_page_line_is_typed_and_the_mode_is_restored_and_quit_does_not_end_anything(self):
        ctl = self.Ctl()
        events = list(page_responder(ctl)("hello"))
        self.assertEqual(ctl.during, "typed")
        self.assertEqual(ctl.provenance, "spoken")
        self.assertEqual(events, [("say", "ok"), ("show", QUIT_TEXT)])


class StaticTests(unittest.TestCase):
    def test_ui_adds_no_advisor_model_fetch_or_launch_import(self):
        for path in py_files("ui"):
            for name in imported(parse(path)):
                with self.subTest(file=path, module=name):
                    self.assertNotIn(name.split(".")[0], {"advisor", "fetcher", "subprocess", "jarvis"})
                    self.assertFalse(name.startswith("interaction.") and name not in ("interaction.child",) and name != "interaction")


if __name__ == "__main__":
    unittest.main()
