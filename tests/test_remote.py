"""Phone access over the private network (ADR-0011 Amendment 4: A4.6 and A4.7). Tests required by A4.6.8, plus the points a review raised.

No real network, no real proxy, no model: a stand-in conversation answers, and requests are made with chosen headers to a server on
an ephemeral loopback port. The names used here are placeholders (never RK's real hostname or login).
Pinned: remote access is off unless a valid gate is given; every request is local or remote by its headers, never by its address;
a remote request needs the exact Host, the one login, the remote token (its hash) and, on a mutation, the exact Origin, each
header exactly once; the two tokens never cross; the phone sees only an allowlist; the phone never sees the laptop's microphone
or turns; confirmations belong to the side that proposed them; five failures switch remote access off and local use goes on.
"""

import hashlib
import http.client
import io
import json
import os
import tempfile
import threading
import time
import unittest

from advisor import bridge, remote_config
from advisor.controller import REMOTE_ALLOWED, Controller
from interaction import intents
from jarvis import cli
from ui import remote, turns
from ui.server import DashboardServer

HOST = "laptop.example.ts.net"
LOGIN = "someone@example"
TOKEN = "remote-token-for-tests-0123456789abcdef0123456789"
DIGEST = hashlib.sha256(TOKEN.encode()).hexdigest()


def make_config(base):
    data, gov, home = (os.path.join(base, n) for n in ("data", "gov", "home"))
    for d in (data, gov, home):
        os.makedirs(d)
    cfg = os.path.join(base, "jarvis-test.toml")
    with open(cfg, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\nuser_home = '%s'\n" % (data, gov, home))
    with open(os.path.join(gov, "revocations.toml"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("schema_version = 1\ncapabilities = []\nprojects = []\ncontract_hashes = []\n")
    assert cli.main(["--config", cfg, "init"], io.StringIO()) == cli.EXIT_OK
    return cfg


class Mic:
    """A microphone stand-in that holds something private the phone must never see."""

    def status(self):
        return {"enabled": True, "state": "idle", "seq": 3, "heard": "LAPTOP-ONLY-HEARD-TEXT", "turn": 1, "reason": ""}


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cfg = make_config(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.after_calls = []
        self.local_seen, self.remote_seen = [], []

        def local(text):
            self.local_seen.append(text)
            yield ("say", "local: " + text)

        def remote_answer(text):
            self.remote_seen.append(text)
            yield ("say", "remote: " + text)

        self.gate = remote.RemoteGate(HOST, LOGIN, DIGEST)
        self.server = DashboardServer(self.cfg, "", local, lambda: self.after_calls.append(1), mic=Mic(), remote_gate=self.gate, remote_respond=remote_answer)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    # ----- requests with exactly the headers given
    def raw(self, method, path, headers, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for name, value in headers:
                conn.putheader(name, value)
            data = body.encode() if isinstance(body, str) else body
            if data is not None:
                conn.putheader("Content-Length", str(len(data)))
            conn.endheaders(data)
            resp = conn.getresponse()
            payload = resp.read()
            try:
                return resp.status, json.loads(payload.decode("utf-8"))
            except ValueError:
                return resp.status, payload.decode("utf-8", "replace")
        finally:
            conn.close()

    def local_headers(self, post=False):
        h = [("Host", "127.0.0.1:%d" % self.port), ("X-JARVIS-Token", self.server.token)]
        if post:
            h += [("Origin", "http://127.0.0.1:%d" % self.port), ("Content-Type", "application/json")]
        return h

    def remote_headers(self, post=False, token=TOKEN, login=LOGIN, host=HOST, origin=None):
        h = [("Host", host), ("Tailscale-User-Login", login), ("X-Forwarded-For", "100.64.0.9"), ("X-Forwarded-Proto", "https")]
        if token is not None:
            h.append(("X-JARVIS-Token", token))
        if post:
            h += [("Origin", origin if origin is not None else "https://" + HOST), ("Content-Type", "application/json")]
        return h

    def say_remote(self, text="hello", **kw):
        return self.raw("POST", "/api/say", self.remote_headers(post=True, **kw), json.dumps({"text": text}))

    def wait_done(self, headers_fn, number):
        for _ in range(100):
            code, body = self.raw("GET", "/api/turn/%d" % number, headers_fn())
            if code == 200 and body.get("state") == "done":
                return body
            if code != 200:
                return code
            time.sleep(0.05)
        self.fail("turn never finished")


class RemoteOffByDefault(unittest.TestCase):
    def test_without_a_gate_a_third_host_is_refused_and_every_request_is_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = DashboardServer(make_config(tmp), "", lambda t: iter([("say", "x")]))
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                self.assertIsNone(server.remote_gate)
                self.assertIsNone(server.remote_respond)
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request("GET", "/", headers={"Host": HOST})
                self.assertEqual(conn.getresponse().status, 403)
                conn.close()
            finally:
                server.shutdown()
                server.server_close()

    def test_a_fixed_port_that_is_taken_fails_to_bind_and_is_never_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_config(tmp)
            first = DashboardServer(cfg, "", None)
            try:
                with self.assertRaises(OSError):
                    DashboardServer(cfg, "", None, port=first.server_address[1])
            finally:
                first.server_close()
            again = DashboardServer(cfg, "", None, port=first.server_address[1])   # once free it can be taken again straight away
            again.server_close()


class Classification(Base):
    def test_local_use_still_works_with_the_local_token_when_remote_is_on(self):
        self.assertEqual(self.raw("GET", "/", self.local_headers())[0], 200)
        self.assertEqual(self.raw("GET", "/api/status", self.local_headers())[0], 200)
        code, body = self.raw("POST", "/api/say", self.local_headers(post=True), json.dumps({"text": "hi"}))
        self.assertEqual(code, 202)
        self.assertIsInstance(self.wait_done(self.local_headers, body["turn"]), dict)
        self.assertEqual(self.local_seen, ["hi"])

    def test_a_proxy_header_with_a_loopback_host_is_refused_even_with_the_local_token(self):
        for extra in (("X-Forwarded-For", "100.64.0.9"), ("Tailscale-User-Login", LOGIN), ("Forwarded", "for=1.2.3.4"), ("X-Real-IP", "1.2.3.4")):
            with self.subTest(header=extra[0]):
                self.assertEqual(self.raw("GET", "/api/status", self.local_headers() + [extra])[0], 403)
                code, _b = self.raw("POST", "/api/say", self.local_headers(post=True) + [extra], json.dumps({"text": "x"}))
                self.assertEqual(code, 403)
        self.assertEqual(self.local_seen, [])

    def test_two_host_headers_are_refused(self):
        h = self.local_headers() + [("Host", "evil.example")]
        self.assertEqual(self.raw("GET", "/api/status", h)[0], 400)


class RemoteRequests(Base):
    def test_the_page_loads_on_the_host_and_login_alone(self):
        code, body = self.raw("GET", "/", self.remote_headers(token=None))
        self.assertEqual(code, 200)
        self.assertIn("linkDead", body)

    def test_a_good_remote_request_reads_the_records(self):
        for path in ("/api/status", "/api/live", "/api/chat", "/api/projects", "/api/tasks", "/api/notes", "/api/audit", "/api/resume", "/api/doctor"):
            with self.subTest(path=path):
                self.assertEqual(self.raw("GET", path, self.remote_headers())[0], 200)

    def test_every_missing_or_wrong_credential_is_one_generic_refusal(self):
        cases = {
            "no token": self.remote_headers(token=None),
            "wrong token": self.remote_headers(token=TOKEN + "x"),
            "the local token": self.remote_headers(token=self.server.token),
            "wrong login": self.remote_headers(login="other@example"),
            "no login": [h for h in self.remote_headers() if h[0] != "Tailscale-User-Login"],
            "two tokens": self.remote_headers() + [("X-JARVIS-Token", TOKEN)],
            "two logins": self.remote_headers() + [("Tailscale-User-Login", LOGIN)],
            "another host": self.remote_headers(host="other.example.ts.net"),
            "wrong origin": self.remote_headers() + [("Origin", "https://evil.example")],
        }
        for name, headers in cases.items():
            self.gate._locked = False
            self.gate._fails.clear()
            with self.subTest(case=name):
                code, body = self.raw("GET", "/api/status", headers)
                self.assertEqual((code, body), (403, {"error": "not allowed"}), name)

    def test_a_mutation_needs_the_exact_origin_and_the_token(self):
        for name, kw in {"no origin": None, "http origin": "http://" + HOST, "other origin": "https://evil.example", "wrong token": "tok"}.items():
            self.gate._locked = False
            self.gate._fails.clear()
            with self.subTest(case=name):
                if name == "no origin":
                    headers = [h for h in self.remote_headers(post=True) if h[0] != "Origin"]
                    code, _b = self.raw("POST", "/api/say", headers, json.dumps({"text": "x"}))
                elif name == "wrong token":
                    code, _b = self.say_remote(token="tok")
                else:
                    code, _b = self.say_remote(origin=kw)
                self.assertEqual(code, 403)
        self.assertEqual(self.remote_seen, [])

    def test_the_remote_token_is_refused_on_a_local_request(self):
        h = [("Host", "127.0.0.1:%d" % self.port), ("X-JARVIS-Token", TOKEN)]
        self.assertEqual(self.raw("GET", "/api/status", h), (403, {"error": "token required"}))

    def test_a_remote_line_goes_to_the_phones_own_conversation_and_is_never_spoken(self):
        code, body = self.say_remote("what is on my list")
        self.assertEqual(code, 202)
        result = self.wait_done(self.remote_headers, body["turn"])
        self.assertEqual(result["events"], [["say", "remote: what is on my list"]])
        self.assertNotIn("origin", result)
        self.assertEqual((self.local_seen, self.remote_seen), ([], ["what is on my list"]))
        time.sleep(0.2)
        self.assertEqual(self.after_calls, [])   # no waiting for speech after a remote turn
        code, body = self.raw("POST", "/api/say", self.local_headers(post=True), json.dumps({"text": "hi"}))
        self.wait_done(self.local_headers, body["turn"])
        for _ in range(40):
            if self.after_calls:
                break
            time.sleep(0.05)
        self.assertEqual(self.after_calls, [1])  # a local turn still does

    def test_the_phone_cannot_read_the_laptops_turns_or_microphone(self):
        _c, body = self.raw("POST", "/api/say", self.local_headers(post=True), json.dumps({"text": "private"}))
        self.wait_done(self.local_headers, body["turn"])
        self.assertEqual(self.raw("GET", "/api/turn/%d" % body["turn"], self.remote_headers())[0], 404)
        code, live = self.raw("GET", "/api/live", self.remote_headers())
        self.assertNotIn("LAPTOP-ONLY-HEARD-TEXT", json.dumps(live))
        self.assertEqual(live["chat"]["mic"], {"enabled": False})
        code, local_live = self.raw("GET", "/api/live", self.local_headers())
        self.assertIn("LAPTOP-ONLY-HEARD-TEXT", json.dumps(local_live))   # the laptop still sees its own

    def test_the_microphone_route_and_everything_unnamed_is_refused_for_the_phone(self):
        code, body = self.raw("POST", "/api/mic", self.remote_headers(post=True), json.dumps({"action": "start"}))
        self.assertEqual((code, body), (403, {"error": "the microphone is not available from the phone"}))
        for path in ("/api/voice", "/api/mic", "/api/unknown", "/elsewhere", "/api/turn/abc", "/api/project/../x"):
            with self.subTest(path=path):
                self.assertIn(self.raw("GET", path, self.remote_headers())[0], (400, 404))
        for method in ("PUT", "DELETE", "PATCH"):
            self.assertEqual(self.raw(method, "/api/say", self.remote_headers(post=True), "{}")[0], 405)
        self.assertEqual(self.raw("POST", "/api/tasks", self.remote_headers(post=True), "{}")[0], 405)

    def test_body_rules_apply_to_the_phone_too(self):
        big = json.dumps({"text": "x" * 2000})
        self.assertEqual(self.raw("POST", "/api/say", self.remote_headers(post=True), big)[0], 413)
        bad_type = [h for h in self.remote_headers(post=True) if h[0] != "Content-Type"] + [("Content-Type", "text/plain")]
        self.assertEqual(self.raw("POST", "/api/say", bad_type, json.dumps({"text": "x"}))[0], 415)
        self.assertEqual(self.say_remote("   ")[0], 400)
        self.assertEqual(self.remote_seen, [])

    def test_five_failures_switch_remote_off_and_local_use_goes_on(self):
        for _ in range(5):
            self.raw("GET", "/api/status", self.remote_headers(token="wrong"))
        self.assertTrue(self.gate.locked)
        code, body = self.raw("GET", "/api/status", self.remote_headers())
        self.assertEqual((code, body), (403, {"error": "remote access is switched off"}))
        self.assertEqual(self.say_remote("hi")[0], 403)
        self.assertEqual(self.raw("GET", "/api/status", self.local_headers())[0], 200)

    def test_the_phone_has_its_own_rate_buckets(self):
        now = time.monotonic()
        self.server.rate_remote.extend([now] * 40)
        self.assertEqual(self.raw("GET", "/api/status", self.remote_headers())[0], 429)
        self.assertEqual(self.raw("GET", "/api/status", self.local_headers())[0], 200)


class GateUnit(unittest.TestCase):
    class H(dict):
        """A header set with get_all, as http.client's has."""

        def __init__(self, pairs):
            super().__init__()
            self.pairs = pairs

        def get_all(self, name, default=None):
            values = [v for k, v in self.pairs if k.lower() == name.lower()]
            return values or default

        def keys(self):
            return [k for k, _v in self.pairs]

    def headers(self, **over):
        pairs = {"Host": HOST, "Tailscale-User-Login": LOGIN, "X-JARVIS-Token": TOKEN}
        pairs.update(over)
        return self.H([(k, v) for k, v in pairs.items() if v is not None])

    def test_check_matrix(self):
        gate = remote.RemoteGate(HOST, LOGIN, DIGEST)
        self.assertTrue(gate.check(self.headers(), post=False, need_token=True))
        self.assertTrue(gate.check(self.headers(**{"X-JARVIS-Token": None}), post=False, need_token=False))
        self.assertFalse(gate.check(self.headers(**{"X-JARVIS-Token": None}), post=False, need_token=True))
        self.assertFalse(gate.check(self.headers(), post=True, need_token=True))            # a mutation needs the Origin
        self.assertTrue(gate.check(self.headers(Origin="https://" + HOST), post=True, need_token=True))
        self.assertFalse(gate.check(self.headers(Origin="https://" + HOST + ":443"), post=True, need_token=True))
        self.assertFalse(gate.check(self.headers(Host=HOST + ":443"), post=False, need_token=True))   # the phone's Host has no port

    def test_failures_lock_only_inside_the_window(self):
        now = [0.0]
        gate = remote.RemoteGate(HOST, LOGIN, DIGEST, clock=lambda: now[0])
        for _ in range(4):
            gate.fail()
            now[0] += 20.0   # four failures spread over a minute and more
        self.assertFalse(gate.locked)
        for _ in range(5):
            gate.fail()
        self.assertTrue(gate.locked)

    def test_proxy_headers_are_recognised_in_any_case(self):
        self.assertTrue(remote.has_proxy_headers(self.H([("tailscale-user-login", "x")])))
        self.assertTrue(remote.has_proxy_headers(self.H([("X-FORWARDED-FOR", "x")])))
        self.assertTrue(remote.has_proxy_headers(self.H([("Forwarded", "x")])))
        self.assertFalse(remote.has_proxy_headers(self.H([("Host", "x"), ("Accept", "y")])))


class FakeModel:
    """Stands in for the model: reaching it means a line was treated as ordinary conversation."""

    def stream_reply(self, text):
        return iter(["Conversation reply."])


class RemoteConversation(unittest.TestCase):
    """The phone's controller: an allowlist with default deny, its own pending state, marked records."""

    def setUp(self):
        self.calls, self.started, self.fetched = [], [], []

        class R:
            def __init__(self, code=0, text=""):
                self.code, self.text, self.truncated = code, text, False

        self.R = R
        self.list_text = ""

        def runner(args):
            self.calls.append(list(args))
            if args[:2] == ["note", "list"]:
                return R(0, self.list_text)
            return R(0, "")

        self.runner = runner
        self.catalog_calls = 0

    def make(self, remote_side, **kw):
        return Controller(FakeModel(), self.runner, remote=remote_side, fetcher=lambda n, a: self.fetched.append((n, a)), **kw)

    def say(self, ctl, text):
        return [t for _k, t in ctl.respond(text)]

    def test_every_intent_kind_is_either_allowed_or_refused_by_name(self):
        kinds = {v for k, v in vars(intents).items() if k.isupper() and isinstance(v, str) and v == k}
        refused = {"LAUNCH", "QUIT"}
        self.assertEqual(kinds - REMOTE_ALLOWED, refused | (kinds - REMOTE_ALLOWED - refused))
        self.assertTrue(refused <= kinds)
        self.assertFalse(REMOTE_ALLOWED & refused)
        self.assertTrue(REMOTE_ALLOWED <= kinds, REMOTE_ALLOWED - kinds)

    def test_launching_and_quitting_are_refused_with_a_plain_sentence_and_start_nothing(self):
        launched = []
        ctl = self.make(True, launcher=lambda exe, args: launched.append(exe), catalog_source=lambda: None)
        for phrase in ("open task manager", "launch steam", "play dune", "open my movies folder"):
            out = self.say(ctl, phrase)
            self.assertEqual(out, ["I cannot open apps, files or games from the phone, sir. That is for the laptop."], phrase)
        self.assertEqual(self.say(ctl, "quit"), ["I cannot end the session from the phone, sir. That is for the laptop."])
        self.assertEqual(launched, [])
        self.assertFalse([c for c in self.calls if c[0] in ("launch", "fetch")])
        self.assertIsNone(ctl.pending)
        self.assertIsNone(ctl.pending_launch)
        self.assertFalse([c for c in self.calls if c[:2] == ["note", "add"]])   # a "yes" afterwards has nothing to confirm
        self.say(ctl, "yes")
        self.assertFalse([c for c in self.calls if c[:2] == ["note", "add"]])

    def test_no_task_command_is_ever_run_from_the_phone(self):
        ctl = self.make(True)
        for phrase in ("cancel task 1", "create a task to tidy up", "delete all my notes", "run the health check", "show my tasks"):
            self.say(ctl, phrase)
        for call in self.calls:
            self.assertNotIn(call[:2], (["task", "cancel"], ["task", "create"]), call)
            self.assertIn(call[0], ("status", "doctor", "project", "task", "note", "audit", "resume", "result", "report"), call)
            if call[0] == "task":
                self.assertIn(call[1], ("list", "show"))

    def test_confirmations_belong_to_the_side_that_proposed_them(self):
        local, phone = self.make(False), self.make(True)
        self.say(local, "make a note that the milk is low")
        self.assertIsNotNone(local.pending)
        self.say(phone, "yes")                                  # a phone "yes" cannot confirm the laptop's proposal
        self.assertFalse([c for c in self.calls if c[:2] == ["note", "add"]])
        self.assertIsNotNone(local.pending)                     # and it did not clear it
        self.say(phone, "make a note that the bread is stale")
        self.say(local, "yes")                                  # a laptop "yes" cannot confirm the phone's
        self.assertFalse([c for c in self.calls if c[:2] == ["note", "add"] and "bread" in c[-1]])
        self.assertIsNone(local.pending)
        self.assertIsNotNone(phone.pending)
        self.say(phone, "yes")
        added = [c[-1] for c in self.calls if c[:2] == ["note", "add"]]
        self.assertEqual(len(added), 2)                          # the laptop's own "yes" confirmed the laptop's own note, and only that
        self.assertTrue(added[0].startswith("[typed] ") and "milk" in added[0], added)
        self.assertTrue(added[1].startswith("[remote] ") and "bread" in added[1], added)

    def test_an_unconfirmed_phone_proposal_lapses_on_the_next_line(self):
        phone = self.make(True)
        self.say(phone, "make a note that the bread is stale")
        self.say(phone, "what time is it")
        self.say(phone, "yes")
        self.assertFalse([c for c in self.calls if c[:2] == ["note", "add"]])

    def test_a_phone_todo_is_added_ticked_and_dropped_marked_remote_and_read_back_cleanly(self):
        phone = self.make(True)
        self.say(phone, "add buy milk to my to-do list")
        self.say(phone, "yes")
        body = [c[-1] for c in self.calls if c[:2] == ["note", "add"]][-1]
        self.assertEqual(body, "[todo] buy milk [remote]")
        self.list_text = "1  jarvis  [todo] buy milk [remote]\n2  jarvis  [todo] call home\n"
        out = self.say(phone, "what is on my to-do list")
        self.assertIn("buy milk", " ".join(out))
        self.assertNotIn("[remote]", " ".join(out))
        self.say(phone, "tick off buy milk")
        self.say(phone, "yes")
        done = [c[-1] for c in self.calls if c[:2] == ["note", "add"]][-1]
        self.assertEqual(done, "[todo-done 1] [remote]")
        self.list_text += "3  jarvis  [todo-done 1] [remote]\n"
        self.assertNotIn("buy milk", " ".join(self.say(phone, "what is on my to-do list")))
        self.say(phone, "remove call home from my list")
        self.say(phone, "yes")
        self.assertEqual([c[-1] for c in self.calls if c[:2] == ["note", "add"]][-1], "[todo-drop 2] [remote]")

    def test_old_records_without_the_marker_still_read(self):
        ctl = self.make(False)
        self.list_text = "1  jarvis  [todo] old item\n2  jarvis  [todo-done 1]\n"
        self.assertEqual(ctl._todo_items(), [])
        self.list_text = "1  jarvis  [todo] old item\n"
        self.assertEqual(ctl._todo_items(), [(1, "old item")])

    def test_lookups_notes_and_reading_work_from_the_phone(self):
        from interaction.fetch_child import FetchResult
        ctl = Controller(FakeModel(), self.runner, remote=True, fetcher=lambda n, a: FetchResult(True, "", "api.open-meteo.com", 1, 1, {"place": "kumbakonam", "temp_c": 20.0, "feels_c": 20.0, "conditions": "clear", "wind_kmh": 5.0, "high_c": 25.0, "low_c": 15.0, "rain_pct": 0}))
        out = self.say(ctl, "what is the weather")
        self.assertIn("20 degrees", " ".join(out))
        self.assertTrue(self.say(ctl, "what time is it"))

    def test_a_remote_responder_marks_lines_remote_and_never_speaks(self):
        spoken = []

        class Voice:
            def say(self, text):
                spoken.append(text)

        ctl = self.make(True)
        respond = bridge.page_responder(ctl, None)
        list(respond("make a note that the bread is stale"))
        self.assertEqual(ctl.provenance, "remote")
        self.assertEqual(spoken, [])
        local = self.make(False)
        list(bridge.page_responder(local, Voice())("what time is it"))
        self.assertTrue(spoken)   # the laptop's still speaks
        self.assertEqual(local.provenance, "typed")


class RemoteConfigTests(unittest.TestCase):
    GOOD = '[remote]\nhostname = "%s"\nlogin = "%s"\nport = 47000\ntoken_sha256 = "%s"\n' % (HOST, LOGIN, DIGEST)

    def bad(self, text, fragment):
        with self.assertRaises(remote_config.RemoteConfigError) as cm:
            remote_config.parse(text)
        self.assertIn(fragment, str(cm.exception))
        self.assertNotIn(DIGEST, str(cm.exception))

    def test_a_good_file(self):
        cfg = remote_config.parse(self.GOOD)
        self.assertEqual((cfg.hostname, cfg.login, cfg.port, cfg.token_sha256), (HOST, LOGIN, 47000, DIGEST))

    def test_every_malformed_file_keeps_remote_off_with_a_reason(self):
        self.bad("not toml [", "not valid TOML")
        self.bad("[other]\nx = 1\n", "exactly one [remote]")
        self.bad(self.GOOD + "extra = 1\n", "must hold exactly")
        self.bad(self.GOOD.replace("login", "logon"), "must hold exactly")
        for host in ("Laptop.example.ts.net", "laptop.example.ts.net:443", "localhost", "laptop.example.com", "ts.net", "a b.ts.net", ""):
            self.bad(self.GOOD.replace(HOST, host), "hostname")
        self.bad(self.GOOD.replace(LOGIN, "bad login!"), "login")
        for port in ("80", "70000", '"47000"', "true"):
            self.bad(self.GOOD.replace("port = 47000", "port = " + port), "port")
        self.bad(self.GOOD.replace(DIGEST, ""), "no remote token")
        self.bad(self.GOOD.replace(DIGEST, DIGEST.upper()), "64 lower-case")
        self.bad(self.GOOD.replace(DIGEST, DIGEST[:-1]), "64 lower-case")

    def test_a_missing_file_keeps_remote_off(self):
        with self.assertRaises(remote_config.RemoteConfigError):
            remote_config.load(os.path.join(tempfile.gettempdir(), "no-such-remote-file.toml"))

    def test_the_example_file_is_valid_toml_but_not_switched_on(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "examples", "remote.example.toml")
        with open(path, encoding="utf-8") as fh:
            with self.assertRaises(remote_config.RemoteConfigError) as cm:
                remote_config.parse(fh.read())
        self.assertIn("no remote token", str(cm.exception))   # placeholders, empty hash: it cannot switch anything on


class TurnTags(unittest.TestCase):
    def test_origin_is_stored_and_a_remote_turn_skips_the_speech_wait(self):
        waited = []
        t = turns.Turns(lambda text: iter([("say", "x")]), lambda: waited.append(1))
        self.assertTrue(t.reserve("turn"))
        n = t.start_reserved("hi", None, origin="remote", speak=False)
        for _ in range(60):
            e = t.get(n)
            if e["state"] == "done":
                break
            time.sleep(0.02)
        self.assertEqual(e["origin"], "remote")
        time.sleep(0.1)
        self.assertEqual(waited, [])


if __name__ == "__main__":
    unittest.main()
