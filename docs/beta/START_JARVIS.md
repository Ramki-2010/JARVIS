# Starting JARVIS the usual way (and freeing memory first)

`scripts\start-jarvis.cmd` is RK's one-step start. It does three things in order:

1. **Frees memory.** Runs `scripts\free_memory.py --apply`, which closes the programs on RK's close list.
2. **Makes sure the model server is running.** If nothing answers on `127.0.0.1:11434` it starts Ollama (loopback only, models in `D:\JARVIS\models\ollama`) and waits up to a minute.
3. **Runs the advisor**, passing on every option given to the script.

```
scripts\start-jarvis.cmd --dashboard --voice-root D:\JARVIS\voice
```

To skip step 1 once: `set JARVIS_NO_FREE=1` before running it. If step 1 fails for any reason JARVIS still starts.

## The close list

`D:\JARVIS\governance\close_list.toml` is RK's file. Only RK edits it; JARVIS never reads, writes or runs anything about it. The format and an example are in `docs/examples/close_list.example.toml`.

Per program: `images` (its name in Task Manager's Details tab, without `.exe`), `force` (false = ask it to close and leave it open if it will not; true = end it after `grace` seconds), `grace`, and `last` (closed after all the others, for a VPN).

**See what it would do, closing nothing:** `py -3.14 scripts\free_memory.py`

**Rules no list can change**
- Never touched: Windows' own processes, Python and the shells, Ollama and its model server, the Claude desktop app and its tools, the antivirus.
- Names are plain program names: no path, no wildcard. At most 32 entries.
- A program is asked to close the way a person would (its window is told to close). Nothing is ended by force unless its entry says `force = true`.
- A program that will not close is left open and the script says so.
- The memory freed is measured from Windows' own available-memory figure before and after, never estimated.
- JARVIS the assistant cannot close anything; only this script, started by this launcher, can. It is not recorded in the audit chain; it writes `D:\JARVIS\free_memory.log`.

**Cost to know about.** Closing a program can lose unsaved work (a browser's open forms, a call in progress). Keep `force = false` for anything that holds something.

## What it is worth (measured 2026-11-16, before this script existed)

With nothing closed, the 9B model decoded at 10.8 tokens per second on the CPU, the same as the 10.7 measured at install; the CPU was about 98% idle and Windows was not swapping. So on that day the listed programs were not slowing the model, and closing them freed about 2.5 GB (mostly Zen) without a measurable change in speed. The model on the GPU decoded at 45 to 58 tokens per second (about four to five times faster) but fills the GPU, so it cannot be used while the voice is on. This script mainly helps when memory is genuinely short, for example loading the model on a busy day; the measured before and after is printed every time.

## Phone access (private network; RK's own steps, after the build is merged)

Off unless you ask for it. The phone reaches the dashboard only through your private network (Tailscale), only as your login, and with a token. Nothing is opened to the internet.

1. One-time: the settings file in your governance folder (see `docs/examples/remote.example.toml` for the shape; the real file holds your device's private name, your login and a fixed port, and is never committed).
2. Make the token and the phone link (run it yourself; the link is shown once and not stored): `py -3.14 scripts\make_remote_token.py --file D:\JARVIS\governance\remote.toml`. Open the link on the phone once and bookmark it. Run it again to rotate (the old link stops at the next launch); add `--revoke` to switch phone access off.
3. Publish the dashboard to your own devices only (your act; it persists until you switch it off): `tailscale serve --bg --https=443 http://127.0.0.1:<the fixed port>`. To stop publishing: `tailscale serve --https=443 off`.
4. Start with phone access: `set JARVIS_REMOTE=1` then `scripts\start-jarvis.cmd --dashboard ...`. The start script first runs `scripts\remote_gate.py`, which refuses (and starts JARVIS without phone access) unless Tailscale reports nothing published publicly (Funnel). `py -3.14 scripts\boundaries.py` shows the whole picture.

What the phone can do: talk, ask for the weather, headlines and the time, read status and records, add notes and to-dos and tick them off or drop them (each with the usual "yes"). It cannot open apps, files or games, use the microphone, quit JARVIS, or hear JARVIS speak on the laptop. Five wrong attempts in a minute switch phone access off until JARVIS restarts. The laptop must stay awake with JARVIS running.
