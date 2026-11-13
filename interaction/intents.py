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


def normalise(text: str) -> str:
    t = (text or "").replace("’", "'").replace("‘", "'").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = t.rstrip(" .!?,;:")
    t = _LEAD.sub("", t, count=1)
    t = _TAIL.sub("", t)
    return t.strip(" .!?,;:")


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
