"""Stock phrases for JARVIS's fixed replies, so they have manner without a model call.

Deterministic: each pool is used in turn (first use of each pool is the plain line), so tests and runs are
repeatable. Original wording only. A phrase may colour a reply but must never state anything that is not
known: no "all is well", no claims about the world. Wit stays out of errors, refusals about risk, and records.
"""

from typing import Dict, Tuple

POOLS: Dict[str, Tuple[str, ...]] = {
    "noted": ("Noted, sir.", "Consider it noted, sir.", "Duly noted, sir. I shall try not to misplace it.", "Written down, sir."),
    "declined": ("Very well, sir. I have not noted it.", "As you wish, sir. Nothing has been written.",
                 "Quite so, sir. It goes no further."),
    "added": ("Added to your list, sir.", "On the list it goes, sir.", "Added, sir. The list grows, as lists do."),
    "done": ("Ticked off, sir.", "Done and dusted, sir.", "Crossed off, sir. A small victory, but we take those."),
    "dropped": ("Struck from the list, sir.", "Removed, sir. Out of sight, out of mind.", "Gone, sir."),
    "empty_list": ("Your list is clear, sir.", "Nothing on your list at present, sir. A rare condition."),
    "on_screen": ("The {what} is on screen, sir.", "Here is the {what}, sir.", "The {what} is on screen, sir. Do take your time."),
    "nothing_pending": ("There is nothing awaiting your answer, sir.", "I have asked nothing of you at present, sir."),
}


class Lines:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}

    def say(self, pool: str, **fields: str) -> str:
        options = POOLS[pool]
        i = self._n.get(pool, 0)
        self._n[pool] = i + 1
        return options[i % len(options)].format(**fields)


def daypart(hour: int) -> str:
    """A plain word for the hour, used so the model does not guess the time of day."""
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"
