"""The live voice signal behind the ring's LISTENING and SPEAKING (ADR-0012 D3 item 5, ADR-0011 D4).

No microphone or speaker is used: the worker side is driven with a fake clock, the reader with fixed times.
"""

import json
import os
import tempfile
import unittest

from ui import voicesignal
from voice import livestate


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class LiveStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clock = Clock()
        self.live = livestate.LiveState(self.tmp.name, clock=self.clock, mono=self.clock)

    def written(self):
        with open(self.live.path, encoding="utf-8") as fh:
            return json.load(fh)

    def test_idle_until_something_real_happens(self):
        self.assertEqual(self.live.state(), "IDLE")
        self.live.tick()
        self.assertEqual(self.written()["state"], "IDLE")

    def test_the_microphone_open_is_listening_and_closing_ends_it(self):
        self.live.mic_open(True)
        self.assertEqual(self.written()["state"], "LISTENING")
        self.live.mic_open(False)
        self.assertEqual(self.written()["state"], "IDLE")

    def test_queued_audio_is_speaking_only_for_its_length(self):
        self.live.audio_queued(2.0)
        self.assertEqual(self.written()["state"], "SPEAKING")
        self.clock.t += 1.9
        self.live.tick()
        self.assertEqual(self.live.state(), "SPEAKING")
        self.clock.t += 0.2
        self.live.tick()
        self.assertEqual(self.written()["state"], "IDLE")

    def test_no_audio_queued_is_never_speaking(self):
        self.live.audio_queued(0.0)
        self.live.audio_queued(-3.0)
        self.assertEqual(self.live.state(), "IDLE")

    def test_the_microphone_outranks_speaking_because_speech_closes_it_anyway(self):
        self.live.audio_queued(5.0)
        self.live.mic_open(True)
        self.assertEqual(self.live.state(), "LISTENING")

    def test_a_running_state_is_refreshed_so_a_dead_worker_goes_stale(self):
        self.live.mic_open(True)
        first = self.written()["at"]
        self.clock.t += 1.2
        self.live.tick()
        self.assertGreater(self.written()["at"], first)
        before = os.path.getmtime(self.live.path)
        self.live.mic_open(False)
        self.clock.t += 5
        self.live.tick()                      # idle is written once, not every second
        self.assertEqual(self.written()["at"], 1001.2)
        self.assertGreaterEqual(os.path.getmtime(self.live.path), before)

    def test_stop_writes_idle_and_the_file_holds_nothing_else(self):
        self.live.mic_open(True)
        self.live.stop()
        data = self.written()
        self.assertEqual(data["state"], "IDLE")
        self.assertEqual(sorted(data), ["at", "pid", "state"])

    def test_an_unwritable_place_never_raises(self):
        blocked = os.path.join(self.tmp.name, "file")
        open(blocked, "w").close()
        live = livestate.LiveState(blocked, clock=self.clock, mono=self.clock)
        live.mic_open(True)                   # the state folder cannot be made: ignored
        self.assertEqual(live.state(), "LISTENING")


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "voice_state.json")

    def put(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text if isinstance(text, str) else json.dumps(text))

    def read(self, at=1000.0, now=1001.0):
        return voicesignal.read(self.path, now=lambda: now)["state"]

    def test_a_fresh_listening_or_speaking_state_is_reported(self):
        for state in ("LISTENING", "SPEAKING"):
            self.put({"state": state, "at": 1000.0})
            self.assertEqual(self.read(), state)

    def test_stale_future_missing_or_damaged_means_idle(self):
        self.assertEqual(self.read(), "IDLE")                                  # no file
        self.put({"state": "LISTENING", "at": 1000.0})
        self.assertEqual(self.read(now=1004.0), "IDLE")                        # older than 3 seconds
        self.assertEqual(self.read(now=990.0), "IDLE")                         # from the future
        for bad in ("not json", "[]", "null", '{"state": "THINKING", "at": 1000}', '{"state": "IDLE", "at": 1000}',
                    '{"state": "LISTENING"}', '{"state": "LISTENING", "at": "1000"}', '{"state": "LISTENING", "at": true}'):
            self.put(bad)
            self.assertEqual(self.read(), "IDLE", bad)

    def test_an_oversized_file_is_refused(self):
        self.put({"state": "LISTENING", "at": 1000.0, "pad": "x" * 2000})
        self.assertEqual(self.read(), "IDLE")

    def test_the_default_place_is_next_to_the_governance_folder(self):
        path = voicesignal.default_path(os.path.join("X:\\", "install", "governance", "jarvis.toml"))
        self.assertEqual(path, os.path.join("X:\\", "install", "voice", "state", "voice_state.json"))

    def test_writer_and_reader_agree(self):
        clock = Clock()
        live = livestate.LiveState(self.tmp.name, clock=clock, mono=clock)
        live.mic_open(True)
        self.assertEqual(voicesignal.read(live.path, now=clock)["state"], "LISTENING")
        clock.t += 10
        self.assertEqual(voicesignal.read(live.path, now=clock)["state"], "IDLE")   # a worker that went quiet is not LISTENING


if __name__ == "__main__":
    unittest.main()
