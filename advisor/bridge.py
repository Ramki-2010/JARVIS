"""The one function the dashboard's text box is given (ADR-0011 Amendment 2).

`page_responder(ctl)` wraps the same `Controller.respond` the terminal uses, so a line typed on the page is the
same conversation: same intent layer, same confirmation turns, same policy and audit paths. Two differences, both
about the page and nothing else: the line is always tagged `typed` (even when the terminal is in microphone mode),
and a `quit` request does not end the advisor from the page. Replies are shown on the page only; nothing is spoken.
"""

from typing import Callable, Iterator, Tuple

QUIT_TEXT = "To end the session, close the terminal, sir. The page cannot stop me."


def page_responder(ctl) -> Callable[[str], Iterator[Tuple[str, str]]]:
    def respond(text: str) -> Iterator[Tuple[str, str]]:
        saved = ctl.provenance
        ctl.provenance = "typed"
        try:
            for kind, out in ctl.respond(text):
                yield ("show", QUIT_TEXT) if kind == "quit" else (kind, out)
        finally:
            ctl.provenance = saved
    return respond
