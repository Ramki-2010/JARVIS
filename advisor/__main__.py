"""Conversation with JARVIS: `py -3.14 -m advisor --config <absolute governance path> [--voice-root D:\\JARVIS\\voice] [--listen]`.

Reads the approved model list (RK's governance file), checks the model against
it, then loops: one utterance in, intent layer first, conversation second.
The model's placement is chosen automatically (RK, 2026-11-16, refining Setup A of 2026-11-13): with `--voice-root` it
runs on the CPU so the cloned voice can have the GPU; without voice nothing needs the GPU, so the server places the
model there as far as memory allows (about four to five times faster here). `--num-gpu N` overrides. With `--voice-root` each spoken sentence goes to
the voice worker as soon as it is complete; if the voice cannot start, the
conversation simply continues in text. With `--listen` the utterance comes from
the microphone while the push-to-talk key (Right Ctrl) is held. `--timing` prints
the measured delays.
"""

import argparse
import contextlib
import os
import sys
import threading
import time

from advisor import approved, guard, remote_config
from advisor.controller import UNAVAILABLE_TEXT, Controller
from advisor.bridge import Mic, page_responder, speech_wait
from advisor.conversation import Conversation
from advisor.lines import daypart
from advisor.persona import PERSONA_PLAIN, PERSONA_TEASING
from advisor.style_bank import flavour
from advisor.runtime import ModelUnavailable, OllamaClient
from interaction import child

DEFAULT_MODEL = "qwen3.5:9b"


def model_options(num_gpu, voice_root, num_thread) -> dict:
    """The model-server options. An explicit --num-gpu always wins. Otherwise: voice on means the CPU (the voice needs the GPU);
    voice off means no setting at all, so the server places the model on the GPU as far as memory allows and falls back
    to the CPU for the rest, instead of failing when something else is using the GPU."""
    options = {}
    if num_gpu is not None:
        options["num_gpu"] = num_gpu
    elif voice_root:
        options["num_gpu"] = 0
    if num_thread and num_thread > 0:
        options["num_thread"] = num_thread
    return options


def release_stale(client, model: str) -> bool:
    """Without voice, drop a copy of the model that an earlier session loaded onto the CPU. The server reuses a loaded model
    as it is, whatever is asked for now, so without this a text session after a voice session would stay on the CPU.
    Returns True if it dropped one. A model already fully on the GPU is kept."""
    try:
        for m in client.loaded():
            if m["name"] == model and m["size"] and m["size_vram"] < m["size"]:
                client.unload(model)
                return True
    except ModelUnavailable:
        pass
    return False


def placement(client, model: str, num_gpu, voice_root) -> str:
    """Where the model really sits, measured from the server (never assumed), with the reason it was chosen."""
    why = "chosen with --num-gpu" if num_gpu is not None else "automatic: the voice has the GPU" if voice_root else "automatic: no voice, so the GPU is free"
    try:
        for m in client.loaded():
            if m["name"] == model:
                share = round(100.0 * m["size_vram"] / m["size"]) if m["size"] else 0
                return "%d%% of the model is in GPU memory (%s)" % (share, why)
    except ModelUnavailable:
        pass
    return "not reported by the server (%s)" % why


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
    ap.add_argument("--num-gpu", type=int, default=None, help="model layers on the GPU (0 = CPU only). Default: automatic - CPU when --voice-root is given (the voice has the GPU), otherwise the server decides and uses the GPU")
    ap.add_argument("--num-thread", type=int, default=0, help="CPU threads for the model (0 = the runtime's choice)")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--voice-root", help="absolute path of the voice folder; omit for text only")
    ap.add_argument("--fetch-root", help="absolute path of the fetcher folder (holds python314); default: the 'fetcher' folder next to the governance folder")
    ap.add_argument("--no-fetch", action="store_true", help="switch the public-data lookups (weather, news) off for this run")
    ap.add_argument("--catalog", help="the launch catalog (default: launch_catalog.toml next to --config); without one, nothing is opened")
    ap.add_argument("--no-launch", action="store_true", help="switch opening apps, folders, files and games off for this run")
    ap.add_argument("--listen", action="store_true", help="take input from the microphone (push-to-talk) instead of the keyboard")
    ap.add_argument("--dashboard", action="store_true", help="also serve the dashboard page, with a conversation box, on this machine only")
    ap.add_argument("--remote-file", help="absolute path of RK's private remote-access settings (ADR-0011 A4.6); with --dashboard it also lets the phone reach the dashboard through the private network. Off unless given and valid")
    ap.add_argument("--timing", action="store_true")
    ap.add_argument("--no-teasing", action="store_true", help="plain wit only: JARVIS will not tease you")
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
        options = model_options(args.num_gpu, args.voice_root, args.num_thread)
        if args.num_gpu is None and not args.voice_root:
            release_stale(client, args.model)   # automatic placement needs a fresh load, not a leftover CPU one
        seed = int(time.time())
        conversation = Conversation(client, args.model, options, persona=(PERSONA_PLAIN if args.no_teasing else PERSONA_TEASING) + flavour(seed), seed=seed)
        conversation.scrub = guard.scrub
        conversation.daypart = lambda: daypart(time.localtime().tm_hour)
        t0 = time.perf_counter()
        greeting = conversation.warm("Hello. It is %s here." % daypart(time.localtime().tm_hour))
        print("the model is ready" if greeting else "the model did not load")
        if greeting:
            print("  model placement: " + placement(client, args.model, args.num_gpu, args.voice_root))
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

    fetcher = None
    if not args.no_fetch:
        from interaction.fetch_child import Fetcher, FetchRefused, default_root, interpreter
        root = args.fetch_root or default_root(args.config)
        try:
            interpreter(root)
            fetcher = Fetcher(root)
        except FetchRefused as exc:
            print("the public-data lookups are off (%s)" % exc)
    launcher = catalog_source = None
    if not args.no_launch:
        from interaction import launch_catalog
        from interaction.launch_child import start
        catalog_path = args.catalog or os.path.join(os.path.dirname(os.path.abspath(args.config)), "launch_catalog.toml")
        first = launch_catalog.load(catalog_path)
        if first is None:
            print("opening apps and folders is off (no launch catalog yet)")
        else:
            for notice in first.notices:
                print(notice)
            print("launch catalog: %d entries" % first.count())
            launcher, catalog_source = start, (lambda: launch_catalog.load(catalog_path))
    ctl = Controller(conversation, lambda a: child.run(args.config, a), project=args.project, spoken=listening, line_seed=int(time.time()), tease=not args.no_teasing, fetcher=fetcher, launcher=launcher, catalog_source=catalog_source) if conversation else None
    dash = None
    turn_lock = contextlib.nullcontext
    if args.dashboard:
        from ui.server import DashboardServer
        if ctl is None:
            print("the dashboard has no conversation box while the conversation is off")
        voice_path = os.path.join(args.voice_root, "state", "voice_state.json") if args.voice_root else ""
        gate = remote_respond = None
        fixed_port = 0
        if args.remote_file:
            from ui.remote import RemoteGate
            try:
                rcfg = remote_config.load(args.remote_file)
                gate, fixed_port = RemoteGate(rcfg.hostname, rcfg.login, rcfg.token_sha256), rcfg.port
            except remote_config.RemoteConfigError as exc:
                print("remote access is OFF: %s" % exc)
        if gate is not None and ctl is not None:   # the phone's own conversation: its own history, no launching, no voice
            rconv = Conversation(client, args.model, conversation.options, persona=conversation.persona, seed=conversation.seed + 1)
            rconv.scrub, rconv.daypart = conversation.scrub, conversation.daypart
            rctl = Controller(rconv, lambda a: child.run(args.config, a), project=args.project, line_seed=int(time.time()) + 1, tease=not args.no_teasing,
                              fetcher=fetcher, launcher=None, catalog_source=None, remote=True)
            remote_respond = page_responder(rctl, None)
        elif gate is not None:
            print("remote access is OFF: the conversation is off, so there is nothing for the phone to talk to")
            gate = None
            fixed_port = 0
        try:
            dash = DashboardServer(args.config, voice_path, page_responder(ctl, voice) if ctl else None, speech_wait(voice) if (ctl and voice) else None,
                                   port=fixed_port, remote_gate=gate, remote_respond=remote_respond)
        except OSError:
            if gate is None:
                raise
            print("remote access is OFF: port %d is already in use, and I will not pick another" % fixed_port)
            gate = remote_respond = None
            dash = DashboardServer(args.config, voice_path, page_responder(ctl, voice) if ctl else None, speech_wait(voice) if (ctl and voice) else None)
        if ctl and voice and voice.ready_info.get("stt", False) and not listening:
            dash.mic = Mic(voice, dash.turns, ctl)   # the page's microphone button; replies are spoken
        threading.Thread(target=dash.serve_forever, daemon=True).start()
        turn_lock = dash.turns.exclusive
        print("dashboard (this machine only; keep this window open): " + dash.url)
        if gate is not None:
            print("  phone access: ON, fixed port %d (127.0.0.1 only). It reaches the phone only once the private network publishes it: tailscale serve --bg --https=443 http://127.0.0.1:%d" % (fixed_port, fixed_port))
            print("  the phone needs the remote link from scripts/make_remote_token.py (shown once, not stored); no apps are opened and nothing is spoken for the phone")
        print("  text box: %s; microphone button: %s; spoken replies: %s" % (
            "on" if ctl else "off (conversation is off)", "on" if dash.mic else "off (needs the voice worker with speech recognition, and not --listen)", "on" if voice else "off"))
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
            t_submit = time.time()
            first_say = None
            first_audio = None
            first_id = None
            with turn_lock():  # a page turn, a page microphone listen and a terminal turn never overlap
                if voice:
                    voice.drain()  # forget events left over from the previous turn
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
        if dash:
            dash.shutdown()
            dash.server_close()
        if voice:
            voice.stop()


if __name__ == "__main__":
    raise SystemExit(main())
