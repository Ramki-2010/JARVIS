"""A deterministic last check on what the model says (ADR-0013 A1, persona review A6.3).

The persona asks the model not to recite "as an artificial intelligence" disclaimers, not to refuse to hold an
opinion, and never to speak of sir's "kind". A 9B model sometimes does anyway, and one such phrase ("your kind") was
awkward and could read as insulting. This module removes any sentence containing one of those constructions before
it is shown or spoken; if nothing is left, a stock line in the butler's manner is used instead. It only ever removes
or replaces text. It grants nothing and checks nothing about facts.
"""

import re
from typing import Iterable, Iterator

BANNED = re.compile(
    r"\byour (?:kind|species)\b|\byou humans\b|\bhumankind\b|\bmankind\b|\bpeople like you\b|\bhumans? (?:always|often|tend|are)\b"
    r"|\bas an? (?:ai|a\.i\.|artificial intelligence|language model|llm|machine|program)\b"
    r"|\bi(?: am|'m) (?:just|only|merely|simply|nothing but) an? (?:ai|artificial intelligence|language model|llm|program|machine)\b"
    r"|\bi (?:do not|don't|cannot|can't|am unable to|lack the capacity to) (?:truly |really |actually )?(?:have|feel|possess|experience|hold|form) "
    r"(?:any |a |an )?(?:personal |real |genuine )?(?:desires?|feelings?|emotions?|opinions?|preferences?|views?|love)\b"
    r"|\bcapacity for (?:love|emotion|feeling)\b|\bwithout (?:personal )?(?:desires?|feelings?|emotions?)\b"
    r"|\bi (?:cannot|can't|could not|couldn't|should not|shouldn't) (?:offer|give|share|express|have) (?:you )?(?:an?|any|my) (?:personal )?(?:opinion|view|preference)s?\b",
    re.IGNORECASE)


def allowed(sentence: str) -> bool:
    """True if the sentence may be shown and spoken."""
    return BANNED.search(sentence or "") is None


def scrub(text: str) -> str:
    """The text without any sentence the guard would remove (used so the model's memory matches what was said)."""
    from advisor.sentences import sentences
    return " ".join(s for s in sentences([text]) if allowed(s))


def filtered(sentences: Iterable[str], fallback: str) -> Iterator[str]:
    """Pass the allowed sentences through; if the model said nothing that is allowed, say `fallback` once."""
    spoke = False
    for sentence in sentences:
        if allowed(sentence):
            spoke = True
            yield sentence
    if not spoke:
        yield fallback
