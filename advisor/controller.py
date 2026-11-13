"""Routes one utterance: intent layer first, conversation second (ADR-0013 A2 rule 1).

The deterministic intent layer sees every utterance. A recognised read intent
runs a fixed control-plane command through `runner` (the `interaction/child.py`
helper in real use; a fake in tests). A capture or an unsupported request only
ever *proposes* a note; the note is written only after a separate explicit
confirmation turn, through the existing `note add` command, which policy
evaluates and the audit chain records. Everything else is conversation, whose
output is text with no authority.

Events yielded: ("say", text) is spoken and shown; ("show", text) is shown only;
("error", text) is shown and spoken as a failure; ("quit", "").
"""

from typing import Callable, Iterator, Optional, Tuple

from advisor.conversation import Conversation
from advisor.runtime import ModelUnavailable
from advisor.sentences import sentences
from interaction import intents

Event = Tuple[str, str]

HELP_TEXT = ("I can show the status, run the health check, list projects, tasks and notes, verify the audit "
             "trail and tell you where we were. I can note something down if you ask and then confirm. "
             "Beyond that we can simply talk, sir.")
GAP_TEXT = ("I have no network, browser or phone access in this version, sir, so I cannot do that. "
            "Shall I note it down for you instead?")
UNAVAILABLE_TEXT = "The conversation model is unavailable, sir. The rest of JARVIS is unaffected."
MAX_SHOWN = 6000


class Controller:
    def __init__(self, conversation: Conversation, runner: Callable, project: str = "jarvis", spoken: bool = False):
        self.conversation = conversation
        self.runner = runner
        self.project = project
        self.provenance = "spoken" if spoken else "typed"
        self.pending: Optional[str] = None  # a note text awaiting the confirmation turn

    def _write_note(self, text: str) -> Event:
        tagged = "[%s] %s" % (self.provenance, text)
        res = self.runner(["note", "add", "--project", self.project, "--text", tagged])
        if res.code == 0:
            return ("say", "Noted, sir.")
        return ("error", "I could not record that note, sir. Nothing was written.")

    def respond(self, text: str) -> Iterator[Event]:
        intent = intents.recognise(text)

        if self.pending is not None:
            pending, self.pending = self.pending, None
            if intent is not None and intent.kind == intents.CONFIRM:
                yield self._write_note(pending)
                return
            if intent is not None and intent.kind == intents.DENY:
                yield ("say", "Very well, sir. I have not noted it.")
                return
            # anything else abandons the proposal; fall through and treat the text normally

        if intent is None:
            yield from self._converse(text)
            return
        if intent.kind == intents.READ:
            res = self.runner(list(intent.args))
            shown = res.text[:MAX_SHOWN]
            yield ("show", shown)
            if res.code == 0:
                yield ("say", "The %s is on screen, sir." % intent.family)
            else:
                yield ("error", "That command reported a problem, sir. The details are on screen.")
        elif intent.kind == intents.CAPTURE:
            self.pending = intent.text
            yield ("say", "You would like me to note: %s. Shall I note that down, sir?" % intent.text)
        elif intent.kind == intents.GAP:
            self.pending = intent.text
            yield ("say", GAP_TEXT)
        elif intent.kind == intents.HELP:
            yield ("say", HELP_TEXT)
        elif intent.kind == intents.QUIT:
            yield ("say", "Very good, sir.")
            yield ("quit", "")
        elif intent.kind in (intents.CONFIRM, intents.DENY):
            yield ("say", "There is nothing awaiting your answer, sir.")

    def _converse(self, text: str) -> Iterator[Event]:
        try:
            for sentence in sentences(self.conversation.stream_reply(text)):
                yield ("say", sentence)
        except ModelUnavailable:
            yield ("error", UNAVAILABLE_TEXT)
