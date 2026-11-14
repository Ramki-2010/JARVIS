"""The live voice signal the dashboard ring reads (ADR-0012 D3 item 5, ADR-0011 D4).

The voice worker is the only program that really holds the microphone and the speaker, so it is the only source of
this signal. It reports two facts and nothing else:

  * LISTENING: the microphone has been opened and not yet closed.
  * SPEAKING: audio has been handed to the speaker and its length (as queued) has not yet run out.

The state is written to <voice folder>\\state\\voice_state.json as {"state", "at", "pid"}. While it is not IDLE the file is
rewritten about once a second, and the reader ignores anything older than a few seconds, so a worker that is killed
cannot leave the ring showing LISTENING. Nothing here records audio, text or a transcript.
"""

import json
import os
import threading
import time

STATE_DIR = "state"
STATE_FILE = "voice_state.json"
STATES = ("IDLE", "LISTENING", "SPEAKING")


def path_for(root: str) -> str:
    return os.path.join(root, STATE_DIR, STATE_FILE)


class LiveState:
    def __init__(self, root: str, clock=time.time, mono=time.monotonic, interval: float = 0.2, heartbeat: float = 1.0):
        self.path = path_for(root)
        self._clock, self._mono = clock, mono
        self._interval, self._heartbeat = interval, heartbeat
        self._mic = False
        self._audio_until = 0.0
        self._last = None
        self._wrote_at = 0.0
        self._stop = threading.Event()
        self._thread = None

    # ----- facts, reported by the worker at the moment they happen
    def mic_open(self, is_open: bool) -> None:
        self._mic = bool(is_open)
        self.tick()

    def audio_queued(self, seconds: float) -> None:
        """Audio was just handed to the speaker; `seconds` is how much is queued in all (not yet played)."""
        if seconds > 0:
            self._audio_until = max(self._audio_until, self._mono() + float(seconds))
        self.tick()

    # ----- state and file
    def state(self) -> str:
        if self._mic:
            return "LISTENING"
        return "SPEAKING" if self._mono() < self._audio_until else "IDLE"

    def tick(self) -> None:
        state, now = self.state(), self._mono()
        if state != self._last or (state != "IDLE" and now - self._wrote_at >= self._heartbeat):
            self._write(state)
            self._last, self._wrote_at = state, now

    def _write(self, state: str) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"state": state, "at": self._clock(), "pid": os.getpid()}, fh)
            os.replace(tmp, self.path)
        except OSError:
            pass   # the signal is best-effort; a failure never touches the voice itself

    def start(self) -> None:
        self._write("IDLE")
        self._last, self._wrote_at = "IDLE", self._mono()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            self.tick()

    def stop(self) -> None:
        self._stop.set()
        self._mic, self._audio_until = False, 0.0
        self._write("IDLE")
