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
from datetime import datetime, timedelta
from typing import Callable, Iterator, List, Optional, Tuple

from advisor.conversation import Conversation
from advisor.lines import Lines
from advisor.runtime import ModelUnavailable
from advisor.sentences import sentences
from fetcher import keys as fetch_keys
from interaction import intents

Event = Tuple[str, str]

HELP_TEXT = ("I can show the status, run the health check, list projects, tasks and notes, verify the audit "
             "trail and tell you where we were. Ask me about a project, for example where we are on it. "
             "I keep your to-do list: ask what is on it, add something, or tick something off, and I will confirm first. "
             "I can note something down if you ask and then confirm. Beyond that we can simply talk, sir.")
TODO_PREFIX = "[todo"
TODO_LINE = re.compile(r"^(\d+)  (\S+)  (.*)$")
TODO_ITEM = re.compile(r"^\[todo\] (.+)$")
TODO_MARK = re.compile(r"^\[todo-(done|drop) (\d+)\]$")
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}
MAX_SPOKEN_ITEMS = 6
PROJECT_LINE = re.compile(r"^(\S+)\s+(.+?)\s+\[([^\]]+)\]$")  # the state can hold spaces, e.g. [no root registered]
NOTE_LINE = re.compile(r"^\s+#(\d+)\s+(\S+)\s+(\S+)\s+(\S+Z)\s+(.*)$")
TAG = re.compile(r"^\[(?:typed|spoken)\]\s*")
MAX_SPOKEN_NOTE = 220
GAP_TEXT = ("I have no network, browser or phone access in this version, sir, so I cannot do that. "
            "Shall I note it down for you instead?")
LOOKUP_HELP = ("I can also read today's weather for my saved places, the top Hacker News stories and Indian news headlines. ")
LOOKUP_GAP_TEXT = ("I can only look up today's weather for my saved places, Hacker News and the Indian headlines, sir, "
                   "and nothing else online. Shall I note it down for you instead?")
LOOKUP_NAMES = {"weather": "the weather service", "hn": "Hacker News", "news": "the news feeds"}
UNAVAILABLE_TEXT = "The conversation model is unavailable, sir. The rest of JARVIS is unaffected."
MAX_SHOWN = 6000


NL = chr(10)
TEASE_AT = 6  # open items before the list is gently teased about


class Controller:
    def __init__(self, conversation: Conversation, runner: Callable, project: str = "jarvis", spoken: bool = False, line_seed: Optional[int] = None, tease: bool = True, fetcher: Optional[Callable] = None):
        self.conversation = conversation
        self.runner = runner
        self.project = project
        self.provenance = "spoken" if spoken else "typed"
        self.pending: Optional[str] = None  # a note text awaiting the confirmation turn
        self.pending_todo: Optional[Tuple[str, int, str]] = None  # ("add"|"done"|"drop", note seq or 0, item text)
        self.lines = Lines(line_seed)
        self.fetcher = fetcher  # public-data lookups (ADR-0014); None means they are not set up
        self.tease = tease  # light teasing, only from counts JARVIS has actually read (switch: --no-teasing)

    def _write_note(self, text: str) -> Event:
        tagged = "[%s] %s" % (self.provenance, text)
        res = self.runner(["note", "add", "--project", self.project, "--text", tagged])
        if res.code == 0:
            return ("say", self.lines.say("noted"))
        return ("error", "I could not record that note, sir. Nothing was written.")

    def respond(self, text: str) -> Iterator[Event]:
        intent = intents.recognise(text)

        if self.pending_todo is not None:
            action, self.pending_todo = self.pending_todo, None
            if intent is not None and intent.kind == intents.CONFIRM:
                yield self._write_todo(*action)
                return
            if intent is not None and intent.kind == intents.DENY:
                yield ("say", self.lines.say("declined"))
                return
            # anything else abandons the proposal; fall through and treat the text normally
        if self.pending is not None:
            pending, self.pending = self.pending, None
            if intent is not None and intent.kind == intents.CONFIRM:
                yield self._write_note(pending)
                return
            if intent is not None and intent.kind == intents.DENY:
                yield ("say", self.lines.say("declined"))
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
                yield ("say", self.lines.say("on_screen", what=intent.family))
            else:
                yield ("error", "That command reported a problem, sir. The details are on screen.")
        elif intent.kind in (intents.TODO_LIST, intents.TODO_ADD, intents.TODO_DONE, intents.TODO_DROP):
            yield from self._todo(intent, text)
        elif intent.kind == intents.BRIEF:
            yield from self._brief(intent.text, soft=intent.args == ("soft",), original=text)
        elif intent.kind == intents.CAPTURE:
            self.pending = intent.text
            yield ("say", "You would like me to note: %s. Shall I note that down, sir?" % intent.text)
        elif intent.kind == intents.GAP:
            self.pending = intent.text
            yield ("say", LOOKUP_GAP_TEXT if self.fetcher else GAP_TEXT)
        elif intent.kind == intents.JOKE:  # vetted clean puns, not the model: a 9B model ignored the safety rule once
            yield ("say", self.lines.say("joke"))
        elif intent.kind in (intents.WEATHER, intents.HN, intents.NEWS):
            yield from self._lookup(intent, text)
        elif intent.kind == intents.HELP:
            yield ("say", HELP_TEXT + (" " + LOOKUP_HELP.strip() if self.fetcher else ""))
        elif intent.kind == intents.QUIT:
            yield ("say", "Very good, sir.")
            yield ("quit", "")
        elif intent.kind in (intents.CONFIRM, intents.DENY):
            yield ("say", self.lines.say("nothing_pending"))

    # ----- the to-do list: kept as project notes. "[todo] text" adds an item; "[todo-done N]" or
    # "[todo-drop N]" closes the item that note N holds. Nothing is edited or deleted: the open list is
    # worked out from the notes, and every change is a normal policy-checked, audited `note add`.
    def _todo_items(self) -> Optional[List[Tuple[int, str]]]:
        res = self.runner(["note", "list", "--project", self.project, "--text-prefix", TODO_PREFIX])
        if res.code != 0:
            return None
        items: dict = {}
        closed = set()
        for line in res.text.splitlines():
            m = TODO_LINE.match(line.strip())
            if not m:
                continue
            seq, body = int(m.group(1)), m.group(3)
            item, mark = TODO_ITEM.match(body), TODO_MARK.match(body)
            if item:
                items[seq] = item.group(1)
            elif mark and int(mark.group(2)) in items:
                closed.add(int(mark.group(2)))
        return [(seq, items[seq]) for seq in sorted(items) if seq not in closed]

    @staticmethod
    def _resolve(token: str, items: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        """Which open items a spoken reference points at: a number, an ordinal, or words in the item."""
        t = token.casefold().strip()
        m = re.fullmatch(r"(?:(?:number|item|task|no\.?) ?)?(\d{1,3})", t)
        n = int(m.group(1)) if m else next((v for k, v in ORDINALS.items() if re.fullmatch(r"(?:the )?%s(?: one| item)?" % k, t)), 0)
        if n:
            return [items[n - 1]] if 1 <= n <= len(items) else []
        words = [w for w in re.findall(r"[a-z0-9']+", t) if w not in ("the", "a", "an", "my", "to", "that", "it", "item", "one")]
        if not words:
            return []
        return [(seq, text) for seq, text in items if all(w in text.casefold() for w in words)]

    def _todo(self, intent, original: str) -> Iterator[Event]:
        if intent.kind == intents.TODO_ADD:
            if len(intent.text) > intents.MAX_TODO_CHARS:
                yield ("say", "That is rather long for a list item, sir. Do shorten it and I shall add it.")
                return
            self.pending_todo = ("add", 0, intent.text)
            yield ("say", "Shall I add %s to your list, sir?" % intent.text)
            return
        items = self._todo_items()
        if items is None:
            yield ("error", "I could not read your list, sir. Nothing has been changed.")
            return
        if intent.kind == intents.TODO_LIST:
            if not items:
                yield ("show", "To-do list: empty")
                yield ("say", self.lines.say("empty_list"))
                return
            yield ("show", "To-do list (%d):\n" % len(items) + "\n".join("%d. %s" % (i, t) for i, (_, t) in enumerate(items, 1)))
            yield ("say", "You have %d thing%s on your list, sir." % (len(items), "" if len(items) == 1 else "s"))
            for i, (_, t) in enumerate(items[:MAX_SPOKEN_ITEMS], 1):
                yield ("say", "%d. %s" % (i, t.rstrip(".") + "."))
            if len(items) > MAX_SPOKEN_ITEMS:
                yield ("say", "And %d more on screen, sir." % (len(items) - MAX_SPOKEN_ITEMS))
            return
        action = "done" if intent.kind == intents.TODO_DONE else "drop"
        found = self._resolve(intent.text, items)
        if not found:
            if intent.args == ("soft",):  # "dinner is done": not about the list, so ordinary conversation
                yield from self._converse(original)
            else:
                yield ("say", "I cannot find that on your list, sir." if items else "Your list is empty, sir.")
            return
        if len(found) > 1:
            numbered = ", ".join("%d, %s" % (items.index(f) + 1, f[1]) for f in found[:4])
            yield ("say", "That could be more than one, sir: %s. Which do you mean?" % numbered)
            return
        seq, text = found[0]
        self.pending_todo = (action, seq, text)
        yield ("say", "Shall I %s %s, sir?" % ("tick off" if action == "done" else "remove", text))

    def _write_todo(self, action: str, seq: int, text: str) -> Event:
        body = "[todo] " + text if action == "add" else "[todo-%s %d]" % (action, seq)
        res = self.runner(["note", "add", "--project", self.project, "--text", body])
        if res.code != 0:
            return ("error", "I could not update your list, sir. Nothing was written.")
        if action == "add" and self.tease:
            items = self._todo_items()  # a real count from the records, or no teasing
            if items is not None and len(items) >= TEASE_AT:
                return ("say", self.lines.say("added_many", n=str(len(items))))
        return ("say", self.lines.say({"add": "added", "done": "done", "drop": "dropped"}[action]))

    # ----- public-data lookups (ADR-0014). Authorised and audited by the control plane, made by the separate fetcher
    # program, worded here from fixed fields only. Fetched text is shown and spoken, never given to the model.
    def _lookup(self, intent, original: str) -> Iterator[Event]:
        name = {intents.WEATHER: "weather", intents.HN: "hn", intents.NEWS: "news"}[intent.kind]
        if self.fetcher is None:
            self.pending = original.strip()[:intents.MAX_CAPTURE_CHARS]
            yield ("say", GAP_TEXT)
            return
        if intent.kind == intents.WEATHER and intent.args == ("?",):
            known = ", ".join(v[0] for v in fetch_keys.PLACES.values())
            yield ("say", "I only know the weather for %s, sir." % known)
            return
        auth = self.runner(["fetch", "authorize", name])
        if auth.code != 0:
            yield ("say", "That lookup is not permitted, sir.")
            return
        res = self.fetcher(name, list(intent.args))
        hosts = res.hosts if res.hosts else ""
        result = "ok" if res.ok else ("refused" if res.error in ("RATE", "REFUSED", "NOT_SET_UP") else "failed")
        if res.ok and res.data.get("failed"):
            result = "partial"
        rec = ["fetch", "record", name, "--result", result, "--bytes", str(res.nbytes), "--ms", str(res.ms)]
        if hosts:
            rec += ["--hosts", hosts]
        self.runner(rec)
        if not res.ok:
            yield ("error", self._lookup_failure(name, res.error))
            return
        try:
            shown, spoken = {"weather": self._weather_text, "hn": self._hn_text, "news": self._news_text}[name](res.data, intent)
        except (KeyError, TypeError, ValueError, IndexError):
            yield ("error", "I could not read the reply from %s, sir." % LOOKUP_NAMES[name])
            return
        yield ("show", shown)
        for line in spoken:
            yield ("say", line)

    @staticmethod
    def _lookup_failure(name: str, code: str) -> str:
        if code == "NOT_SET_UP":
            return "The lookups are not set up on this machine yet, sir."
        if code == "RATE":
            return "A little patience, sir; I am limited to six lookups a minute."
        return "I could not reach %s, sir. Nothing else is affected." % LOOKUP_NAMES[name]

    @staticmethod
    def _weather_text(d: dict, intent):
        name = fetch_keys.PLACES[d["place"]][0]
        n = lambda v: str(int(round(v)))
        shown = ("Weather in %s: %s degrees, %s. Feels like %s. Today: high %s, low %s. Wind %s km/h. Chance of rain %d%%."
                 % (name, n(d["temp_c"]), d["conditions"], n(d["feels_c"]), n(d["high_c"]), n(d["low_c"]), n(d["wind_kmh"]), d["rain_pct"]))
        rain = ("rain is %s" % ("likely" if d["rain_pct"] >= 60 else "possible" if d["rain_pct"] >= 30 else "unlikely"))
        spoken = ["In %s it is %s degrees and %s, sir, feeling like %s." % (name, n(d["temp_c"]), d["conditions"], n(d["feels_c"])),
                  "Today's high is %s and the low %s, and %s." % (n(d["high_c"]), n(d["low_c"]), rain)]
        return shown, spoken

    @staticmethod
    def _hn_text(d: dict, intent):
        stories = d["stories"]
        shown = "Hacker News, top stories:" + NL + NL.join("%d. %s (%d points%s)" % (i, s["title"], s["score"], ", " + s["site"] if s["site"] else "")
                                                          for i, s in enumerate(stories, 1))
        spoken = ["The top stories on Hacker News, sir."] + ["%d. %s." % (i, s["title"].rstrip(".")) for i, s in enumerate(stories[:3], 1)]
        return shown, spoken

    @staticmethod
    def _ist(stamp: str) -> str:
        try:
            return (datetime.strptime(stamp, "%Y-%m-%dT%H:%MZ") + timedelta(hours=5, minutes=30)).strftime("%d %b %H:%M IST")
        except ValueError:
            return ""

    def _news_text(self, d: dict, intent):
        items, kw = d["items"], d.get("keyword", "")
        missing = d.get("failed") or []
        tail = (NL + "(No answer from: %s.)" % ", ".join(missing)) if missing else ""
        if not items:
            return ("No headlines about '%s' just now.%s" % (kw, tail) if kw else "No headlines.%s" % tail,
                    ["I find nothing on that in the current headlines, sir." if kw else "There are no headlines to read just now, sir."])
        shown = (("Headlines about '%s':" % kw if kw else "Indian headlines:") + NL) + NL.join(
            "%s: %s%s" % (i["source"], i["title"], " (%s)" % self._ist(i["time"]) if self._ist(i["time"]) else "") for i in items) + tail
        lead = "Here is what the headlines say about %s, sir." % kw if kw else "The headlines, sir."
        return shown, [lead] + ["%s: %s." % (i["source"], i["title"].rstrip(".")) for i in items[:5]]

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
