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

import re
from typing import Callable, Iterator, List, Optional, Tuple

from advisor.conversation import Conversation
from advisor.runtime import ModelUnavailable
from advisor.sentences import sentences
from interaction import intents

Event = Tuple[str, str]

HELP_TEXT = ("I can show the status, run the health check, list projects, tasks and notes, verify the audit "
             "trail and tell you where we were. Ask me about a project, for example where we are on it. "
             "I can note something down if you ask and then confirm. Beyond that we can simply talk, sir.")
PROJECT_LINE = re.compile(r"^(\S+)\s+(.+?)\s+\[([^\]]+)\]$")  # the state can hold spaces, e.g. [no root registered]
NOTE_LINE = re.compile(r"^\s+#(\d+)\s+(\S+)\s+(\S+)\s+(\S+Z)\s+(.*)$")
TAG = re.compile(r"^\[(?:typed|spoken)\]\s*")
MAX_SPOKEN_NOTE = 220
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
        elif intent.kind == intents.BRIEF:
            yield from self._brief(intent.text, soft=intent.args == ("soft",), original=text)
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

    # ----- project briefings: read-only, deterministic, built from the project's own records
    def _registered(self) -> Optional[List[Tuple[str, str]]]:
        res = self.runner(["project", "list"])
        if res.code != 0:
            return None
        found = [m.groups()[:2] for m in (PROJECT_LINE.match(line.strip()) for line in res.text.splitlines()) if m]
        return [(pid, name) for pid, name in found]

    @staticmethod
    def _first_sentence(text: str, limit: int = 220) -> str:
        text = " ".join(text.split())
        cut = re.search(r"[.!?](?:\s|$)", text)
        out = text[: cut.end()].strip() if cut and cut.end() <= limit else text[:limit].rstrip()
        return out if out.endswith((".", "!", "?")) else out + "."

    def _summary(self, pid: str, name: str, info: str, resume: str) -> str:
        """One spoken paragraph from the records. Nothing here comes from a model."""
        desc = next((line.split(":", 1)[1].strip() for line in info.splitlines() if line.startswith("description:")), "-")
        parts = [name + "."]
        if desc and desc != "-":
            parts.append(self._first_sentence(desc))
        unfinished = re.search(r"^unfinished tasks: (\d+)", resume, re.M)
        done = re.search(r"^recent finished tasks: \d+ of (\d+)", resume, re.M)
        n_open, n_done = (int(unfinished.group(1)) if unfinished else 0), (int(done.group(1)) if done else 0)
        if n_open == 0 and n_done == 0:
            parts.append("There are no tasks on record.")
        else:
            parts.append("%d unfinished and %d closed task%s on record." % (n_open, n_done, "" if n_done == 1 else "s"))
        notes, in_notes = [], False
        for line in resume.splitlines():
            if line.startswith("latest notes"):
                in_notes = True
            elif line.startswith("relayed results"):
                in_notes = False
            elif in_notes:
                m = NOTE_LINE.match(line)
                if m:
                    notes.append(TAG.sub("", m.group(5)))
        if notes:
            parts.append("Latest note: " + self._first_sentence(notes[0], MAX_SPOKEN_NOTE))
        else:
            parts.append("I have no notes on it yet.")
        return " ".join(parts)

    def _brief(self, token: str, soft: bool = False, original: str = "") -> Iterator[Event]:
        registered = self._registered()
        if registered is None:
            yield ("error", "I could not read the project list, sir.")
            return
        if not registered:
            yield ("say", "No projects are registered yet, sir.")
            return
        if token:
            wanted = token.casefold()
            chosen = [(pid, name) for pid, name in registered if wanted in (pid.casefold(), name.casefold())]
            if not chosen and soft:  # "tell me about Bali": not a project, so it is simply conversation
                yield from self._converse(original)
                return
            if not chosen:
                names = ", ".join(name for _, name in registered)
                yield ("say", "I do not have a project called %s, sir. The registered ones are %s." % (token, names))
                return
        else:
            chosen = registered
        shown, spoken = [], []
        for pid, name in chosen:  # pid comes from the registry listing above, never from the utterance
            resume = self.runner(["resume", "--project", pid])
            info = self.runner(["project", "show", pid])
            if resume.code != 0 or info.code != 0:
                yield ("error", "I could not read the records for %s, sir." % name)
                return
            shown.append("== %s ==\n%s" % (name, resume.text.rstrip()))
            spoken.append(self._summary(pid, name, info.text, resume.text))
        yield ("show", "\n\n".join(shown)[:MAX_SHOWN])
        if len(chosen) > 1:
            yield ("say", "You have %d projects, sir." % len(chosen))
        for line in spoken:
            yield ("say", line)

    def _converse(self, text: str) -> Iterator[Event]:
        try:
            for sentence in sentences(self.conversation.stream_reply(text)):
                yield ("say", sentence)
        except ModelUnavailable:
            yield ("error", UNAVAILABLE_TEXT)
