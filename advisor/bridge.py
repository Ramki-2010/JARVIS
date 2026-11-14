"""What the dashboard is given: a text responder and a microphone session (ADR-0011 Amendments 2 and 3).

`page_responder(ctl, voice)` wraps the same `Controller.respond` the terminal uses, so a line from the page is the
same conversation: same intent layer, same confirmation turns, same policy and audit paths. Differences, all about
the page and nothing else: the line is tagged `typed` (or `spoken` when it came from the microphone button), a
`quit` request does not end the advisor from the page, and when a voice worker is running the replies are spoken
as the terminal speaks them.

`Mic` is one button-held listen at a time. It never touches audio: it asks the voice worker to listen (the same
worker, the same push-to-talk path, a button standing in for the key), releases it on request, and turns the heard
text into an ordinary turn. The worker alone opens the microphone, and the ring's LISTENING comes from the
worker's own live signal, not from anything here.
"""

import threading
from typing import Callable, Iterator, Optional, Tuple

from ui.turns import MicRefused

QUIT_TEXT = "To end the session, close the terminal, sir. The page cannot stop me."
HEARD_WAIT_S = 120.0   # longer than the worker's own longest listen plus recognition


def page_responder(ctl, voice=None, spoken: bool = False) -> Callable[[str], Iterator[Tuple[str, str]]]:
    def respond(text: str) -> Iterator[Tuple[str, str]]:
        saved = ctl.provenance
        ctl.provenance = "spoken" if spoken else "typed"
        try:
            for kind, out in ctl.respond(text):
                if kind == "quit":
                    yield ("show", QUIT_TEXT)
                    continue
                if voice is not None and kind in ("say", "error"):
                    voice.say(out)
                yield (kind, out)
        finally:
            ctl.provenance = saved
    return respond


def speech_wait(voice) -> Callable[[], None]:
    """Run after a turn's replies are stored: hold the exchange until the speaking is finished."""
    def wait() -> None:
        voice.wait_event("spoken", voice.send("wait"), timeout=120)
    return wait


class Mic:
    def __init__(self, voice, turns, ctl):
        self.voice, self.turns, self.ctl = voice, turns, ctl
        self._mu = threading.Lock()
        self._state = "idle"          # idle, listening (button held), finishing (released, being heard)
        self._job: Optional[int] = None
        self._seq = 0                 # counts finished listens, so the page shows each result once
        self._heard = ""
        self._turn: Optional[int] = None
        self._reason = ""

    def status(self) -> dict:
        with self._mu:
            return {"enabled": True, "state": self._state, "seq": self._seq, "heard": self._heard,
                    "turn": self._turn, "reason": self._reason}

    def start(self) -> None:
        with self._mu:
            if self._state != "idle":
                raise MicRefused("the microphone is already in use")
            if not self.turns.reserve("mic"):
                raise MicRefused("JARVIS is working on something; try again in a moment")
            try:
                self.voice.drain()
                self._job = self.voice.send("listen", hold="button")
            except (OSError, ValueError):
                self.turns.release()
                raise MicRefused("the voice worker is not running", 503)
            self._state, self._heard, self._turn, self._reason = "listening", "", None, ""
            job = self._job
        threading.Thread(target=self._hear, args=(job,), daemon=True).start()

    def stop(self) -> None:
        with self._mu:
            if self._state != "listening":
                raise MicRefused("the microphone is not listening")
            try:
                self.voice.send("mic_stop", target=self._job)
            except (OSError, ValueError):
                raise MicRefused("the voice worker is not running", 503)
            self._state = "finishing"

    def _hear(self, job: int) -> None:
        text, reason, turn = "", "the voice worker did not answer", None
        owns = True   # this session still holds the exchange lock; a started turn takes it over and releases it itself
        try:
            event = self.voice.wait_event("heard", job, timeout=HEARD_WAIT_S)
            if event is not None:
                text = str(event.get("text", "")).strip()
                reason = str(event.get("reason", "")) or "nothing was heard"
            if text:
                owns = False   # start_reserved releases the lock itself if it cannot start
                try:
                    turn = self.turns.start_reserved(text, page_responder(self.ctl, self.voice, spoken=True))
                except Exception:
                    text, reason = "", "the turn could not start"
        except Exception:
            text, reason = "", "the microphone session failed"
        finally:
            if owns:
                self.turns.release()
        with self._mu:
            self._state, self._job = "idle", None
            self._heard, self._turn, self._reason = text, turn, "" if text else reason
            self._seq += 1
