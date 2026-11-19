"""One conversation session (ADR-0013 Amendment 1 A2).

History lives in memory for the session only and is discarded with it. The
model sees the fixed persona and the conversation so far, nothing else: no
file content, no governance content, no policy internals. The reply is text.
"""

from typing import Dict, Iterator, List

from advisor import style_bank
from advisor.persona import PERSONA
from advisor.runtime import ModelUnavailable, OllamaClient

MAX_USER_CHARS = 2000
MAX_TURNS = 12


class Conversation:
    def __init__(self, client: OllamaClient, model: str, options: Dict[str, object] = None, persona: str = PERSONA, seed: int = 0):
        self.client, self.model, self.persona, self.seed = client, model, persona, seed
        # A little warmer and with a repeat penalty, so a small model does not settle into a few stock replies (RK's review).
        self.options = dict({"num_ctx": 4096, "temperature": 0.85, "top_p": 0.92, "top_k": 60, "repeat_penalty": 1.12, "num_predict": 120},
                            **(options or {}))
        self.history: List[Dict[str, str]] = []
        self.turns = 0
        self.daypart = None  # optional: a function giving the part of the day from the machine clock, told to the model each turn
        self.scrub = None  # optional: a function that cleans a reply before it is remembered (advisor.guard.scrub)

    def _messages(self, user_text: str) -> List[Dict[str, str]]:
        recent = [m["content"] for m in self.history if m["role"] == "assistant"]
        now = " It is %s here now (the machine's clock)." % self.daypart() if self.daypart else ""
        msgs = [{"role": "system", "content": self.persona + now + style_bank.turn_hint(self.seed, self.turns, recent)}]
        msgs.extend(self.history[-2 * MAX_TURNS:])
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def stream_reply(self, user_text: str) -> Iterator[str]:
        text = (user_text or "").strip()[:MAX_USER_CHARS]
        if not text:
            return
        parts: List[str] = []
        for piece in self.client.chat_stream(self.model, self._messages(text), self.options):
            parts.append(piece)
            yield piece
        reply = "".join(parts).strip()
        if reply and self.scrub is not None:
            reply = self.scrub(reply).strip()  # remember what was actually said, not a phrase the guard removed
        self.turns += 1
        if reply:
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": reply})

    def note_exchange(self, user_text: str, jarvis_text: str) -> None:
        """Remember a deterministic exchange (for follow-up wording only)."""
        self.history.append({"role": "user", "content": user_text.strip()[:MAX_USER_CHARS]})
        self.history.append({"role": "assistant", "content": jarvis_text.strip()[:MAX_USER_CHARS]})

    def warm(self, opening: str = "Hello.") -> str:
        """Load the model and make a short greeting as the first real exchange, so the persona prompt is
        already processed when the user's first line arrives (a continuation is much faster than a fresh
        prompt on this model). `opening` may name the part of the day so the model does not guess it.
        Returns the greeting, or "" if the model is unavailable."""
        try:
            greeting = "".join(self.stream_reply(opening))
            return greeting.strip()
        except ModelUnavailable:
            return ""
