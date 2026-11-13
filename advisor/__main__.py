"""Text conversation with JARVIS: `py -3.14 -m advisor --config <absolute governance path>`.

Reads the approved model list (RK's governance file), checks the model against
it, then loops: one line in, intent layer first, conversation second. The
model runs on the CPU by default (Setup A, RK decision 2026-11-13) so the
cloned voice can have the GPU. `--timing` prints the measured delays.
"""

import argparse
import os
import sys
import time

from advisor import approved
from advisor.controller import UNAVAILABLE_TEXT, Controller
from advisor.conversation import Conversation
from advisor.runtime import ModelUnavailable, OllamaClient
from interaction import child

DEFAULT_MODEL = "qwen3.5:9b"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="advisor")
    ap.add_argument("--config", required=True, help="absolute path of the governance jarvis.toml")
    ap.add_argument("--approved", help="approved model list (default: models.toml next to --config)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--project", default="jarvis")
    ap.add_argument("--num-gpu", type=int, default=0, help="model layers on the GPU (0 = CPU only, Setup A)")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--timing", action="store_true")
    args = ap.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass

    list_path = args.approved or os.path.join(os.path.dirname(args.config), "models.toml")
    client = OllamaClient(port=args.port)
    conversation = None
    try:
        entries = approved.load(list_path)
        approved.check(entries, args.model, client.tags())
        conversation = Conversation(client, args.model, {"num_gpu": args.num_gpu})
        t0 = time.perf_counter()
        print("loading the model..." if conversation.warm() else "the model did not load")
        if args.timing:
            print("  [model ready in %.1f s]" % (time.perf_counter() - t0))
    except (approved.NotApproved, ModelUnavailable) as exc:
        print("conversation is off: %s" % exc)
        print(UNAVAILABLE_TEXT)

    ctl = Controller(conversation, lambda a: child.run(args.config, a), project=args.project) if conversation else None
    print("JARVIS text conversation. Say 'help' for what I can do, 'quit' to leave.")
    while True:
        try:
            line = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if ctl is None:
            print("jarvis> " + UNAVAILABLE_TEXT)
            continue
        t0 = time.perf_counter()
        first = None
        for kind, text in ctl.respond(line):
            if first is None and kind == "say":
                first = time.perf_counter() - t0
            if kind == "quit":
                return 0
            print(("jarvis> " if kind in ("say", "error") else "") + text)
        if args.timing and first is not None:
            print("  [first sentence after %.2f s, total %.2f s]" % (first, time.perf_counter() - t0))


if __name__ == "__main__":
    raise SystemExit(main())
