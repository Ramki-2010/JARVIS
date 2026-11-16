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
