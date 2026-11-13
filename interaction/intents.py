"""The deterministic intent layer (ADR-0011 D3, ADR-0013 Amendment 1 A2).

Every utterance, typed or spoken, is seen here first. This module decides, by
fixed patterns only, whether the text is one of a small set of known intents.
A recognised read intent maps to a fixed argument list for the control-plane
command layer; nothing from the utterance is ever placed in that list. Text that
matches nothing is conversation, and conversation has no authority.

No model is used here and no model output is read here. No process is started
here (the one place that does is `interaction/child.py`).
"""

import re
from typing import NamedTuple, Optional, Tuple

READ = "READ"
BRIEF = "BRIEF"
TODO_LIST = "TODO_LIST"
TODO_ADD = "TODO_ADD"
TODO_DONE = "TODO_DONE"
TODO_DROP = "TODO_DROP"
CAPTURE = "CAPTURE"
GAP = "GAP"
CONFIRM = "CONFIRM"
DENY = "DENY"
HELP = "HELP"
QUIT = "QUIT"

MAX_CAPTURE_CHARS = 1000


class Intent(NamedTuple):
    family: str
    kind: str
    args: Tuple[str, ...] = ()
    text: str = ""


# Fixed argument lists. The utterance never contributes to these.
_READ_FAMILIES = (
    ("status", ("status",), (
        r"(?:(?:show|give|tell) )?(?:me )?(?:what is |what's )?(?:the |your )?(?:system |control plane |jarvis )?status(?: report)?",
        r"how is (?:the )?(?:system|control plane) (?:doing|running)",
    )),
    ("doctor", ("doctor",), (
        r"(?:run |do )?(?:a |the )?(?:health check|doctor|diagnostics|self check)",
        r"check (?:your |the )?(?:own )?health",
    )),
    ("projects", ("project", "list"), (
        r"(?:list|show)(?: me)?(?: all| my| the)* projects",
        r"what projects (?:do i have|are there|are registered)",
    )),
    ("tasks", ("task", "list"), (
        r"(?:list|show)(?: me)?(?: all| my| the)* tasks",
        r"what tasks (?:do i have|are there|are open)",
    )),
    ("notes", ("note", "list"), (
        r"(?:list|show|read)(?: me)?(?: all| my| the)* notes",
        r"what notes (?:do i have|are there)",
    )),
    ("audit", ("audit", "verify"), (
        r"(?:verify|check) (?:the )?audit(?: log| chain| trail)?",
        r"is the audit (?:log |chain |trail )?(?:intact|ok|fine|healthy)",
    )),
    ("resume", ("resume",), (
        r"where were we",
        r"(?:resume|catch me up|brief me)",
        r"(?:give me )?(?:a )?(?:summary|overview)(?: of everything)?",
    )),
)

_READ_COMPILED = tuple((fam, args, tuple(re.compile(p) for p in pats)) for fam, args, pats in _READ_FAMILIES)

# "Where are we on X": the project name is only a lookup token. It is matched by the caller against the
# registry's own ids and names and is never placed in a command; a name that matches nothing is refused.
_NAME = r"(?P<name>[a-z0-9][a-z0-9 ._-]{0,40})"
_BRIEF_NAMED = tuple(re.compile(p) for p in (
    r"where are we (?:on|with|at with|at on|in) " + _NAME,
    r"what(?:'s| is) the (?:status|stage|state|progress) (?:of|on|with|in) " + _NAME,
    r"what stage (?:is|are we (?:at )?(?:on|in|with)) " + _NAME + r"(?: at)?",
    r"what (?:are we|have we been) (?:working on|doing) (?:in|on|with|for) " + _NAME,
    r"what(?:'s| is) (?:happening|going on) (?:in|on|with) " + _NAME,
    r"(?:brief me|catch me up|update me) on " + _NAME,
))
# Looser phrasing: if the name is not a registered project the text is ordinary conversation (args == ("soft",)).
_BRIEF_SOFT = re.compile(r"tell me about " + _NAME)
# every project at once
_BRIEF_ALL = tuple(re.compile(p) for p in (
    r"what are (?:all )?(?:my|our) projects",
    r"tell me about (?:all )?(?:my|our) projects",
    r"what (?:am i|are we) working on",
    r"what have (?:i|we) been (?:working on|doing)",
    r"what(?:'s| is) (?:happening|going on)",
    r"what stage are we (?:at|in)",
    r"where are we (?:at )?with (?:everything|all (?:of )?(?:my|our) projects)",
))
_GENERIC_NAMES = frozenset({"my projects", "our projects", "everything", "all my projects", "all our projects", "it", "that", "this"})

# To-do list (kept as notes, see advisor/controller.py). The wording of an item is the user's own and is only
# ever stored and read back as text; what to do (add, list, tick off, drop) is decided by these fixed patterns.
_TD = r"to ?-?do"
_TODO_LIST = tuple(re.compile(p) for p in (
    r"(?:what(?:'s| is) on|read|show|list|tell me)(?: me)?(?: my| the| our)? " + _TD + r"(?: list)?",
    r"what(?:'s| is) on (?:my|the|our) list",
    r"what do i (?:still )?(?:have|need) to do",
    r"what(?:'s| is) (?:left|outstanding|pending) (?:to do|on (?:my|the) list)",
))
_TODO_ADD = tuple(re.compile(p, re.I | re.S) for p in (
    r"(?:add|put) (?P<x>.+?) (?:to|on|onto) (?:my |the |our )?" + _TD + r"(?: list)?",
    r"(?:add|put) (?P<x>.+?) (?:to|on|onto) (?:my |the |our )?list",
    r"add (?:a )?" + _TD + r"(?: item)?[:,]? ?(?P<x>.+)",
    _TD + r"(?: item)?[:,] ?(?P<x>.+)",
    r"remind me to (?P<x>.+)",
))
_TODO_DONE_STRICT = tuple(re.compile(p) for p in (
    r"(?:mark|set) (?P<x>.+?) (?:as )?(?:done|complete|completed|finished)(?: (?:on|in|from) (?:my |the )?(?:" + _TD + r" )?list)?",
    r"(?:tick|cross|check|strike) off (?P<x>.+?)(?: (?:from|on) (?:my |the )?(?:" + _TD + r" )?list)?",
))
_TODO_DONE_SOFT = re.compile(r"(?P<x>.+) (?:is|are) (?:done|finished|complete|completed)")
_TODO_DROP = re.compile(r"(?:remove|delete|drop|scratch) (?P<x>.+?) from (?:my |the )?(?:" + _TD + r" )?list")
MAX_TODO_CHARS = 300


def _todo(text: str, t: str) -> Optional[Intent]:
    for pat in _TODO_LIST:
        if pat.fullmatch(t):
            return Intent("todo", TODO_LIST)
    m = _TODO_DROP.fullmatch(t)
    if m:
        return Intent("todo", TODO_DROP, ("strict",), m.group("x").strip())
    for pat in _TODO_DONE_STRICT:
        m = pat.fullmatch(t)
        if m and m.group("x").strip():
            return Intent("todo", TODO_DONE, ("strict",), m.group("x").strip())
    m = _TODO_DONE_SOFT.fullmatch(t)
    if m and m.group("x").strip():
        return Intent("todo", TODO_DONE, ("soft",), m.group("x").strip())
    # adding: take the user's own wording (case and punctuation intact) from the original text
    body = re.sub(_LEAD.pattern, "", text.strip(), count=1, flags=re.I).rstrip(" .!?,;:")
    body = re.sub(_TAIL.pattern, "", body, flags=re.I).strip()
    for pat in _TODO_ADD:
        m = pat.fullmatch(body)
        if m:
            item = m.group("x").strip(" ,;:")
            if len(item) < 2:
                return None
            return Intent("todo", TODO_ADD, (), item[:MAX_TODO_CHARS + 1])
    return None


_HELP = re.compile(r"help|what can you do|what are your commands|what can i say")
_QUIT = re.compile(r"quit|exit|goodbye|good bye|bye|that will be all|that is all")
_CONFIRM = re.compile(r"(?:yes|yeah|yep|yup|sure|correct|affirmative|confirm|confirmed|ok|okay)(?: please)?|please do|go ahead|do it|yes please|that is right|that's right")
_DENY = re.compile(r"no|nope|nah|negative|don't|do not|cancel|never mind|nevermind|no thanks|no thank you|not now")
_CAPTURE = re.compile(r"(?:make a note|take a note|note down|note|remember|write down|jot down|add a note)(?: that| of| to self)?[,:]?\s+(.+)", re.DOTALL)

# Requests the Beta has no means to do. JARVIS must say so plainly and offer to note them down.
_GAP = re.compile(
    r"\b(?:weather|forecast|browse|browser|website|web page|webpage|web site|google|search (?:the )?(?:web|internet|online)|"
    r"look (?:it |that )?up online|news headlines|stock price|bitcoin price|e-?mail|send (?:a |an )?(?:message|text|whatsapp)|"
    r"phone call|call (?:my|him|her|them|mum|mom|dad)|play (?:some )?(?:music|a song|spotify)|set (?:a |an )?(?:alarm|timer|reminder)|"
    r"book (?:a |an )?(?:table|flight|hotel|cab|ticket)|order (?:some |a |an )?(?:food|pizza|groceries)|turn (?:on|off) the (?:light|lights|fan|tv)|"
    r"open (?:the )?(?:app|application|chrome|youtube|url|link)|check (?:the |this )?(?:listing|price|score))\b"
)

_LEAD = re.compile(r"^(?:(?:hey|hi|hello|ok|okay)[, ]+)?(?:jarvis[, ]+)?(?:(?:please|kindly)[, ]+)?(?:(?:can|could|would|will) you (?:please )?)?")
_TAIL = re.compile(r"(?:[, ]+(?:please|sir|jarvis))+$")


_TAIL_KEEP_NAME = re.compile(r"(?:[, ]+(?:please|sir))+$")  # a project may itself be called "jarvis"


def normalise(text: str, keep_name: bool = False) -> str:
    t = (text or "").replace("’", "'").replace("‘", "'").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = t.rstrip(" .!?,;:")
    t = _LEAD.sub("", t, count=1)
    t = (_TAIL_KEEP_NAME if keep_name else _TAIL).sub("", t)
    return t.strip(" .!?,;:")


_FILLER_END = re.compile(r"(?:\s+(?:at|now|right now|currently|today))+$")


def _brief(t: str) -> Optional[Intent]:
    if any(p.fullmatch(t) for p in _BRIEF_ALL):
        return Intent("brief", BRIEF, (), "")
    for pat in _BRIEF_NAMED:
        m = pat.fullmatch(t)
        if m:
            name = _FILLER_END.sub("", m.group("name")).strip(" .-_")
            if name in _GENERIC_NAMES:
                return Intent("brief", BRIEF, (), "")
            if name.startswith("the "):
                name = name[4:].strip()
            return Intent("brief", BRIEF, (), name) if name else None
    soft = _BRIEF_SOFT.fullmatch(t)
    if soft:
        name = soft.group("name").strip(" .-_")
        if name in _GENERIC_NAMES:
            return Intent("brief", BRIEF, (), "")
        return Intent("brief", BRIEF, ("soft",), name[4:].strip() if name.startswith("the ") else name)
    return None


def recognise(text: str) -> Optional[Intent]:
    """Return the intent for `text`, or None when it is conversation."""
    if not isinstance(text, str) or not text.strip():
        return None
    t = normalise(text)
    if not t:
        return None
    if _CONFIRM.fullmatch(t):
        return Intent("confirm", CONFIRM)
    if _DENY.fullmatch(t):
        return Intent("deny", DENY)
    if _QUIT.fullmatch(t):
        return Intent("quit", QUIT)
    if _HELP.fullmatch(t):
        return Intent("help", HELP)
    found = _todo(text, t) or _brief(t) or _brief(normalise(text, keep_name=True))
    if found:
        return found
    for family, args, patterns in _READ_COMPILED:
        for pat in patterns:
            if pat.fullmatch(t):
                return Intent(family, READ, args)
    cap = _CAPTURE.fullmatch(t)
    if cap:
        body = text.strip()
        # take the user's own wording (case and punctuation intact) after the trigger phrase
        m = re.match(r"(?is)^\W*(?:(?:hey|hi|ok|okay)[, ]+)?(?:jarvis[, ]+)?(?:(?:please|kindly)[, ]+)?(?:(?:can|could|would|will) you (?:please )?)?"
                     r"(?:make a note|take a note|note down|note|remember|write down|jot down|add a note)(?: that| of| to self)?[,:]?\s+(.+)$", body)
        note = (m.group(1) if m else cap.group(1)).strip()
        if note.lower() in ("that", "of", "to self"):
            return None
        if 3 <= len(note) <= MAX_CAPTURE_CHARS:
            return Intent("capture", CAPTURE, (), note)
        return None
    if _GAP.search(t):
        return Intent("gap", GAP, (), text.strip()[:MAX_CAPTURE_CHARS])
    return None
