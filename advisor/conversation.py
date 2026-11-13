"""One conversation session (ADR-0013 Amendment 1 A2).

History lives in memory for the session only and is discarded with it. The
model sees the fixed persona and the conversation so far, nothing else: no
file content, no governance content, no policy internals. The reply is text.
"""

from typing import Dict, Iterator, List

from advisor.persona import PERSONA
from advisor.runtime import ModelUnavailable, OllamaClient

MAX_USER_CHARS = 2000
MAX_TURNS = 12


class Conversation:
    def __init__(self, client: OllamaClient, model: str, options: Dict[str, object] = None, persona: str = PERSONA):
        self.client, self.model, self.persona = client, model, persona
        self.options = dict({"num_ctx": 4096, "temperature": 0.7, "num_predict": 160}, **(options or {}))
        self.history: List[Dict[str, str]] = []

    def _messages(self, user_text: str) -> List[Dict[str, str]]:
        msgs = [{"role": "system", "content": self.persona}]
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
        if reply:
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": reply})

    def note_exchange(self, user_text: str, jarvis_text: str) -> None:
        """Remember a deterministic exchange (for follow-up wording only)."""
        self.history.append({"role": "user", "content": user_text.strip()[:MAX_USER_CHARS]})
        self.history.append({"role": "assistant", "content": jarvis_text.strip()[:MAX_USER_CHARS]})

    def warm(self) -> bool:
        """Load the model into memory ahead of the first turn. Changes no history. False if unavailable."""
        try:
            for _ in self.client.chat_stream(self.model, [{"role": "user", "content": "Hello."}], dict(self.options, num_predict=1)):
                pass
            return True
        except ModelUnavailable:
            return False
