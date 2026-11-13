"""Stock phrases for JARVIS's fixed replies, so they have manner without a model call.

Deterministic: each pool is used in turn (first use of each pool is the plain line), so tests and runs are
repeatable. Original wording only. A phrase may colour a reply but must never state anything that is not
known: no "all is well", no claims about the world. Wit stays out of errors, refusals about risk, and records.
"""

import random
from typing import Dict, Optional, Tuple

POOLS: Dict[str, Tuple[str, ...]] = {
    "noted": ("Noted, sir.", "Consider it noted, sir.", "Duly noted, sir. I shall try not to misplace it.", "Written down, sir.",
              "Safely recorded, sir. I have a decent memory for ink.", "Filed, sir. Somewhere sensible, I trust.",
              "Got it, sir. It is in the book now.", "Taken down, sir, word for word."),
    "declined": ("Very well, sir. I have not noted it.", "As you wish, sir. Nothing has been written.",
                 "Quite so, sir. It goes no further.", "Understood, sir. The page stays clean.",
                 "Say no more, sir. I have forgotten it already.", "Consider it unsaid, sir."),
    "added": ("Added to your list, sir.", "On the list it goes, sir.", "Added, sir. The list grows, as lists do.",
              "Done, sir. One more for the pile.", "Down it goes, sir. Future you has been warned.",
              "Added, sir. I shall not let it slip.", "On the list, sir. It does rather accumulate."),
    "done": ("Ticked off, sir.", "Done and dusted, sir.", "Crossed off, sir. A small victory, but we take those.",
             "Marked done, sir. Well played.", "One fewer, sir. Progress, of a sort.",
             "Struck through, sir. Most satisfying.", "Finished, sir. I shall pretend I never doubted you."),
    "added_many": ("Added, sir. That makes {n} open items. Ambitious.", "Noted, sir. {n} on the list now; the list is winning.",
                   "On it goes, sir. {n} items. I admire the optimism.", "Added, sir. {n} outstanding. Do pace yourself."),
    "joke": ("I shall do my best, sir. Why did the scarecrow win an award? He was outstanding in his field.",
             "Very well, sir. I told a chemistry joke, but there was no reaction.",
             "If I may, sir: I used to be a banker, but I lost interest.",
             "A small one, sir. Why can you not trust stairs? They are always up to something.",
             "Briefly, sir. I would tell you a joke about time, but it would take too long.",
             "Of course, sir. What do you call a fake noodle? An impasta."),
    "dropped": ("Struck from the list, sir.", "Removed, sir. Out of sight, out of mind.", "Gone, sir.",
                "Dropped, sir. Some things are better for it.", "Taken off, sir. No hard feelings, I trust.",
                "Off the list, sir, and off my conscience."),
    "empty_list": ("Your list is clear, sir.", "Nothing on your list at present, sir. A rare condition.",
                   "The list is empty, sir. Do enjoy it while it lasts.", "Not a thing outstanding, sir. Suspicious, almost."),
    "on_screen": ("The {what} is on screen, sir.", "Here is the {what}, sir.", "The {what} is on screen, sir. Do take your time.",
                  "The {what}, sir, as requested.", "Up it comes, sir: the {what}.", "The {what} is yours to read, sir."),
    "nothing_pending": ("There is nothing awaiting your answer, sir.", "I have asked nothing of you at present, sir.",
                        "Nothing is waiting on you, sir. A pleasant change.", "No questions outstanding, sir."),
}


class Lines:
    def __init__(self, seed: Optional[int] = None) -> None:
        """With no seed the order is fixed (tests). With a seed each pool starts at its own place, so sessions differ."""
        self._n: Dict[str, int] = {}
        if seed is not None:
            rng = random.Random(seed)
            for name, options in POOLS.items():
                self._n[name] = rng.randrange(len(options))

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
