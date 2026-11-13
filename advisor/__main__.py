"""Conversation with JARVIS: `py -3.14 -m advisor --config <absolute governance path> [--voice-root D:\\JARVIS\\voice] [--listen]`.

Reads the approved model list (RK's governance file), checks the model against
it, then loops: one utterance in, intent layer first, conversation second.
The model runs on the CPU by default (Setup A, RK decision 2026-11-13) so the
cloned voice can have the GPU. With `--voice-root` each spoken sentence goes to
the voice worker as soon as it is complete; if the voice cannot start, the
conversation simply continues in text. With `--listen` the utterance comes from
the microphone while the push-to-talk key (Right Ctrl) is held. `--timing` prints
the measured delays.
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


def _start_voice(root: str):
    from interaction.voice_child import VoiceRefused, VoiceWorker
    try:
        worker = VoiceWorker(root)
        if worker.start():
            return worker
        print("the voice did not start (%s); continuing in text" % (worker.error or "no reason given"))
        worker.stop()
    except (VoiceRefused, OSError) as exc:
        print("the voice is unavailable (%s); continuing in text" % exc)
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="advisor")
    ap.add_argument("--config", required=True, help="absolute path of the governance jarvis.toml")
    ap.add_argument("--approved", help="approved model list (default: models.toml next to --config)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--project", default="jarvis")
    ap.add_argument("--num-gpu", type=int, default=0, help="model layers on the GPU (0 = CPU only, Setup A)")
    ap.add_argument("--num-thread", type=int, default=0, help="CPU threads for the model (0 = the runtime's choice)")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--voice-root", help="absolute path of the voice folder; omit for text only")
    ap.add_argument("--listen", action="store_true", help="take input from the microphone (push-to-talk) instead of the keyboard")
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
    greeting = ""
    try:
        entries = approved.load(list_path)
        approved.check(entries, args.model, client.tags())
        options = {"num_gpu": args.num_gpu}
        if args.num_thread > 0:
            options["num_thread"] = args.num_thread
        conversation = Conversation(client, args.model, options)
        t0 = time.perf_counter()
        greeting = conversation.warm()
        print("the model is ready" if greeting else "the model did not load")
        if args.timing:
            print("  [model ready in %.1f s]" % (time.perf_counter() - t0))
    except (approved.NotApproved, ModelUnavailable) as exc:
        print("conversation is off: %s" % exc)
        print(UNAVAILABLE_TEXT)

    voice = _start_voice(args.voice_root) if args.voice_root else None
    if voice and not voice.ready_info.get("stt", False):
        print("speech recognition is unavailable (%s); the voice will speak, and you can type" % (voice.ready_info.get("stt_problem") or "unknown reason"))
    listening = bool(args.listen and voice and voice.ready_info.get("stt", False))
    if args.listen and not listening:
        print("the microphone is not available; using the keyboard")

    ctl = Controller(conversation, lambda a: child.run(args.config, a), project=args.project, spoken=listening) if conversation else None
    print("JARVIS conversation. Say or type 'help' for what I can do, 'quit' to leave.")
    if greeting:
        print("jarvis> " + greeting)
        if voice:
            voice.say(greeting)
    try:
        while True:
            if listening:
                print("(hold Right Ctrl and speak)")
                jid = voice.send("listen")
                ev = voice.wait_event("heard", jid, timeout=60)
                line = (ev or {}).get("text", "")
                if not line:
                    continue
                print("you (heard)> " + line)
            else:
                try:
                    line = input("you> ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    return 0
            if ctl is None:
                print("jarvis> " + UNAVAILABLE_TEXT)
                continue
            if voice:
                voice.drain()  # forget events left over from the previous turn
            t_submit = time.time()
            first_say = None
            first_audio = None
            first_id = None
            for kind, text in ctl.respond(line):
                if kind == "quit":
                    return 0
                if kind == "say" and first_say is None:
                    first_say = time.time() - t_submit
                print(("jarvis> " if kind in ("say", "error") else "") + text)
                if voice and kind in ("say", "error"):
                    sent = voice.say(text)
                    first_id = first_id or sent
            if voice and args.timing and first_say is not None:
                ev = voice.wait_event("first_audio", first_id, timeout=60)
                if ev:
                    first_audio = ev["at"] - t_submit
                print("  [first sentence ready %.2f s, first spoken word %s after you finished]" %
                      (first_say, "%.2f s" % first_audio if first_audio is not None else "not heard"))
            elif args.timing and first_say is not None:
                print("  [first sentence ready %.2f s]" % first_say)
            if voice:
                voice.wait_event("spoken", voice.send("wait"), timeout=120)
    finally:
        if voice:
            voice.stop()


if __name__ == "__main__":
    raise SystemExit(main())
