"""The dashboard's microphone button (ADR-0011 Amendment 3).

No microphone, no audio and no model: a fake voice worker records what it is asked, and a fake advisor answers.
Checks the strict route, the one-exchange-at-a-time rule, that INTERPRETING is not claimed while listening, that
a quick release cannot leave the microphone open, and that the worker's release bookkeeping is plain and bounded.
"""

import http.client
import io
import json
import os
import queue
import tempfile
import threading
import time
import unittest

from advisor.bridge import Mic, page_responder, speech_wait
from jarvis import cli
from ui import turns
from ui.server import DashboardServer
from voice.holds import KEEP, Holds


class FakeVoice:
    def __init__(self):
        self.sent = []
        self.said = []
        self.heard = queue.Queue()
        self.dead = False
        self._id = 0

    def send(self, cmd, **fields):
        if self.dead:
            raise OSError("pipe closed")
        self._id += 1
        self.sent.append((cmd, fields, self._id))
        return self._id

    def say(self, text):
        self.said.append(text)
        return 0

    def drain(self):
        pass

    def wait_event(self, name, job_id=None, timeout=1.0):
        if name == "spoken":   # the real worker answers "wait" once the speaker is quiet
            return {"event": "spoken", "id": job_id}
        try:
            return self.heard.get(timeout=timeout)
        except queue.Empty:
            return None


class FakeCtl:
    provenance = "typed"

    def __init__(self):
        self.seen = []

    def respond(self, text):
        self.seen.append((text, self.provenance))
        yield ("say", "Understood, sir.")


def settle(predicate, seconds=5):
    end = time.time() + seconds
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class HoldsTests(unittest.TestCase):
    def test_a_release_is_remembered_by_job_id_and_is_bounded(self):
        holds = Holds()
        self.assertFalse(holds.released(7))
        holds.release(7)           # a quick tap: the release can arrive before the listen starts
        self.assertTrue(holds.released(7))
        self.assertFalse(holds.released(8))
        for n in range(1000, 1000 + KEEP + 10):
            holds.release(n)
        self.assertFalse(holds.released(7))   # old ones fall away; the memory cannot grow without limit
        self.assertTrue(holds.released(1000 + KEEP + 9))


class TurnsLockTests(unittest.TestCase):
    def test_a_reserved_listen_blocks_turns_but_is_not_interpreting(self):
        t = turns.Turns(lambda text: [("say", "x")])
        self.assertTrue(t.reserve("mic"))
        self.assertTrue(t.occupied())
        self.assertFalse(t.busy())                 # INTERPRETING is not claimed while only listening
        self.assertIsNone(t.submit("hello"))       # nothing else may run meanwhile
        t.release()
        self.assertFalse(t.occupied())

    def test_speech_after_the_replies_is_not_interpreting(self):
        gate, seen = threading.Event(), {}
        t = turns.Turns(lambda text: [("say", "x")], after=lambda: (seen.update(busy=t.busy(), occupied=t.occupied()), gate.wait(5)))
        number = t.submit("hi")
        self.assertTrue(settle(lambda: "busy" in seen))
        self.assertEqual(t.get(number)["state"], "done")   # the replies are already out
        self.assertEqual(seen, {"busy": False, "occupied": True})
        gate.set()
        self.assertTrue(settle(lambda: not t.occupied()))

    def test_a_failing_after_hook_still_releases(self):
        def boom():
            raise RuntimeError("x")
        t = turns.Turns(lambda text: [("say", "x")], after=boom)
        t.submit("hi")
        self.assertTrue(settle(lambda: not t.occupied()))


class MicTests(unittest.TestCase):
    def setUp(self):
        self.voice, self.ctl = FakeVoice(), FakeCtl()
        self.turns = turns.Turns(page_responder(self.ctl, self.voice), speech_wait(self.voice))
        self.mic = Mic(self.voice, self.turns, self.ctl)

    def test_start_asks_the_worker_to_listen_with_the_button_and_claims_nothing_else(self):
        self.mic.start()
        self.assertEqual(self.voice.sent[0][:2], ("listen", {"hold": "button"}))
        self.assertEqual(self.mic.status()["state"], "listening")
        self.assertFalse(self.turns.busy())
        with self.assertRaises(turns.MicRefused):
            self.mic.start()                       # one listen at a time

    def test_stop_names_the_listen_it_ends_and_a_stop_while_idle_is_refused(self):
        with self.assertRaises(turns.MicRefused):
            self.mic.stop()
        self.mic.start()
        job = self.voice.sent[0][2]
        self.mic.stop()
        self.assertEqual(self.voice.sent[1][:2], ("mic_stop", {"target": job}))
        self.assertEqual(self.mic.status()["state"], "finishing")

    def test_heard_text_becomes_a_spoken_turn_that_is_answered_and_spoken(self):
        self.mic.start()
        self.mic.stop()
        self.voice.heard.put({"event": "heard", "text": "what is the status", "id": 1})
        self.assertTrue(settle(lambda: self.mic.status()["state"] == "idle"))
        status = self.mic.status()
        self.assertEqual(status["heard"], "what is the status")
        self.assertEqual(status["seq"], 1)
        number = status["turn"]
        self.assertTrue(settle(lambda: (self.turns.get(number) or {}).get("state") == "done"))
        self.assertEqual(self.turns.get(number)["events"], [["say", "Understood, sir."]])
        self.assertEqual(self.ctl.seen, [("what is the status", "spoken")])   # tagged as heard, not typed
        self.assertEqual(self.ctl.provenance, "typed")                          # and restored
        self.assertEqual(self.voice.said, ["Understood, sir."])                 # replies are spoken
        self.assertTrue(settle(lambda: not self.turns.occupied()))

    def test_nothing_heard_says_why_and_frees_the_exchange(self):
        self.mic.start()
        self.voice.heard.put({"event": "heard", "text": "", "reason": "too short", "id": 1})
        self.assertTrue(settle(lambda: self.mic.status()["state"] == "idle"))
        status = self.mic.status()
        self.assertEqual((status["heard"], status["turn"], status["reason"], status["seq"]), ("", None, "too short", 1))
        self.assertFalse(self.turns.occupied())
        self.assertEqual(self.ctl.seen, [])

    def test_a_silent_worker_ends_the_session_and_frees_the_exchange(self):
        import advisor.bridge as bridge
        saved, bridge.HEARD_WAIT_S = bridge.HEARD_WAIT_S, 0.2
        try:
            self.mic.start()
            self.assertTrue(settle(lambda: self.mic.status()["state"] == "idle"))
        finally:
            bridge.HEARD_WAIT_S = saved
        self.assertIn("did not answer", self.mic.status()["reason"])
        self.assertFalse(self.turns.occupied())

    def test_busy_or_dead_worker_is_refused_and_leaves_nothing_held(self):
        self.assertTrue(self.turns.reserve("turn"))
        with self.assertRaises(turns.MicRefused) as ctx:
            self.mic.start()
        self.assertEqual(ctx.exception.status, 409)
        self.turns.release()
        self.voice.dead = True
        with self.assertRaises(turns.MicRefused) as ctx:
            self.mic.start()
        self.assertEqual(ctx.exception.status, 503)
        self.assertFalse(self.turns.occupied())
        self.assertEqual(self.mic.status()["state"], "idle")


class ResponderTests(unittest.TestCase):
    def test_typed_lines_are_spoken_only_when_a_voice_exists(self):
        ctl, voice = FakeCtl(), FakeVoice()
        self.assertEqual(list(page_responder(ctl, voice)("hello")), [("say", "Understood, sir.")])
        self.assertEqual(voice.said, ["Understood, sir."])
        quiet = FakeVoice()
        list(page_responder(FakeCtl())("hello"))
        self.assertEqual(quiet.said, [])


class MicRouteBase(unittest.TestCase):
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
        cls.voice, cls.ctl = FakeVoice(), FakeCtl()
        cls.server = DashboardServer(cls.cfg, "", page_responder(cls.ctl, cls.voice))
        cls.server.mic = Mic(cls.voice, cls.server.turns, cls.ctl)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def post(self, body, token=True, origin=True, host=None, ctype="application/json"):
        self.server.rate_hits.clear()
        raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        headers = {"Host": host or "127.0.0.1:%d" % self.port, "Content-Length": str(len(raw))}
        if ctype:
            headers["Content-Type"] = ctype
        if token:
            headers["X-JARVIS-Token"] = self.server.token if token is True else token
        if origin:
            headers["Origin"] = "http://127.0.0.1:%d" % self.port if origin is True else origin
        conn.request("POST", "/api/mic", body=raw, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, json.loads(data) if data else {}

    def get_chat(self):
        self.server.rate_hits.clear()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("GET", "/api/chat", headers={"Host": "127.0.0.1:%d" % self.port, "X-JARVIS-Token": self.server.token})
        data = json.loads(conn.getresponse().read())
        conn.close()
        return data


class MicRouteTests(MicRouteBase):
    def tearDown(self):
        try:
            self.server.mic.stop()
        except turns.MicRefused:
            pass
        self.voice.heard.put({"event": "heard", "text": "", "reason": "test over", "id": 0})
        settle(lambda: self.server.mic.status()["state"] == "idle")
        while not self.voice.heard.empty():
            self.voice.heard.get_nowait()

    def test_start_and_stop_follow_the_session_and_the_page_can_read_the_state(self):
        status, body = self.post({"action": "start"})
        self.assertEqual((status, body["state"]), (202, "listening"))
        chat = self.get_chat()
        self.assertEqual(chat["mic"]["state"], "listening")
        self.assertFalse(chat["busy"])           # listening is not INTERPRETING
        self.assertTrue(chat["occupied"])
        self.assertEqual(self.post({"action": "start"})[0], 409)
        status, body = self.post({"action": "stop"})
        self.assertEqual((status, body["state"]), (202, "finishing"))
        self.assertEqual(self.post({"action": "stop"})[0], 409)

    def test_strict_bodies(self):
        listens = len([c for c, _f, _i in self.voice.sent if c == "listen"])
        cases = {"unknown action": {"action": "record"}, "missing": {}, "extra field": {"action": "start", "x": 1},
                 "wrong field": {"mode": "start"}, "not a string": {"action": 1}, "duplicate": b'{"action": "start", "action": "stop"}',
                 "not json": b"start", "list": b'["start"]', "oversize": b'{"action": "' + b"x" * 2000 + b'"}'}
        for name, body in cases.items():
            with self.subTest(name):
                self.assertIn(self.post(body)[0], (400, 413))
        self.assertEqual(self.server.mic.status()["state"], "idle")
        self.assertEqual(len([c for c, _f, _i in self.voice.sent if c == "listen"]), listens)

    def test_all_the_shared_rules_apply(self):
        good = {"action": "start"}
        self.assertEqual(self.post(good, origin=False)[0], 403)
        self.assertEqual(self.post(good, origin="http://evil.example")[0], 403)
        self.assertEqual(self.post(good, host="evil.example:%d" % self.port)[0], 403)
        self.assertEqual(self.post(good, token=False)[0], 403)
        self.assertEqual(self.post(good, token="wrong")[0], 403)
        self.assertEqual(self.post(good, ctype="text/plain")[0], 415)
        self.assertEqual(self.server.mic.status()["state"], "idle")

    def test_a_busy_exchange_or_dead_worker_is_reported_not_queued(self):
        self.assertTrue(self.server.turns.reserve("turn"))
        try:
            status, body = self.post({"action": "start"})
            self.assertEqual(status, 409)
            self.assertIn("working on something", body["error"])
        finally:
            self.server.turns.release()
        self.voice.dead = True
        try:
            self.assertEqual(self.post({"action": "start"})[0], 503)
        finally:
            self.voice.dead = False
        self.assertFalse(self.server.turns.occupied())


class NoMicRouteTests(unittest.TestCase):
    def test_without_a_microphone_the_route_is_absent_and_the_page_is_told_so(self):
        with tempfile.TemporaryDirectory() as base:
            data, gov, home = (os.path.join(base, n) for n in ("data", "gov", "home"))
            for d in (data, gov, home):
                os.makedirs(d)
            cfg = os.path.join(base, "jarvis-test.toml")
            with open(cfg, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\nuser_home = '%s'\n" % (data, gov, home))
            server = DashboardServer(cfg, "", lambda text: [("say", "x")])    # a text box but no microphone
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                port = server.server_address[1]
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
                body = b'{"action": "start"}'
                conn.request("POST", "/api/mic", body=body, headers={"Host": "127.0.0.1:%d" % port, "Content-Length": str(len(body)),
                             "Content-Type": "application/json", "Origin": "http://127.0.0.1:%d" % port, "X-JARVIS-Token": server.token})
                self.assertEqual(conn.getresponse().status, 405)
                conn.close()
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
                conn.request("GET", "/api/chat", headers={"Host": "127.0.0.1:%d" % port, "X-JARVIS-Token": server.token})
                self.assertEqual(json.loads(conn.getresponse().read())["mic"], {"enabled": False})
                conn.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
