# Beta build and runtime evidence, 2026-11-14 to 2026-11-16

**Status: evidence record, NON-AUTHORITATIVE.** It grants no authority. Accepted ADRs, MCAs and RK's chat word win. Written by Local Claude on the Beta machine. Labels: `MEASURED` (Local Claude ran it and saw the result), `RK OBSERVED` (RK reported it from use; Local Claude did not see it), `RK DECISION`, `UNVERIFIED`. It continues [`new-laptop-beta-evidence-2026-11-13.md`](new-laptop-beta-evidence-2026-11-13.md), which ended at `main` 06e65e3 (PR #61).

Machine: as in the 2026-11-13 record (i7-14650HX, 24 logical processors, 31.6 GiB RAM, RTX 5070 Laptop 8151 MiB, Windows 11 Home).

## 1. Repository state (MEASURED, 2026-11-16, after the last merge)

| Item | Result |
|---|---|
| `main` | `8ce943e`, working tree clean |
| Test suite | 808 tests, OK, 2 skipped (was 724 before this period's last eight pull requests) |
| Open pull requests | none |
| GitHub ruleset `protect-main` (id 24887473) | enforcement active; rules `deletion`, `non_fast_forward`, `pull_request`; the ruleset's digest was identical before and after the merges |
| Audit chain | `audit verify` OK, tail sequence 48. Sequence 44 to 48 are the two real lookups (weather, headlines) run by the post-merge check |
| Governance folder | `jarvis.toml`, `registry.toml`, `revocations.toml`, `contracts` unchanged since Phase 1 and 2026-11-13. Files RK directed Local Claude to write: `launch_catalog.toml` (2026-11-14), `models.toml` (2026-11-14), `close_list.toml` (2026-11-16, edited later the same day at RK's word) |

## 2. What was built and merged since the last record

| PR | What |
|---|---|
| #62 to #68 | The 2026-11-13 evidence; the text conversation core (ADR-0013 A1); voice wiring; voice onset and tone fix; project briefings; the to-do list and wit; the read-only galaxy |
| #69 to #71 | ADR-0014 and the public-data lookups (weather, Hacker News, Indian headlines), each authorised and audited |
| #72 to #74 | Offline clock and time zones; governed local launch (ADR-0015); the glowing PREVIEW tray |
| #75 | The ring's LISTENING and SPEAKING from the voice worker's real live signal (ADR-0012 Amendment 2) |
| #76, #77 | ADR-0011 Amendment 2 and the dashboard conversation box (`POST /api/say`, one turn at a time, option H1) |
| #78 | The microphone button (ADR-0011 Amendment 3): `POST /api/mic`; the voice worker gains `listen` with `hold: button` and `mic_stop`; replies spoken |
| #79 | Natural speech for lookups: several requests in one breath; weather is no longer a refusal |
| #80 | "Too many requests" fix: one combined status poll, a separate bound for cheap state reads, panels refreshed only while shown |
| #81 | A phone-sized layout for the dashboard |
| #82 | ADR-0011 Amendment 4: options for reaching the dashboard from a phone. **Options only: no option chosen, nothing built or in force** |
| #83 | Persona v2: opinions instead of disclaimers; `advisor/guard.py` removes "your kind" and "as an AI" constructions; wider vocabulary bank |
| #84 | `scripts/free_memory.py` and `scripts/start-jarvis.cmd` (RK's own launcher; JARVIS itself cannot close programs) |
| #85 | The advisor picks the model's GPU placement automatically (voice off: GPU; voice on: CPU) |

## 3. Measurements (MEASURED, 2026-11-16, `qwen3.5:9b`, Ollama 0.40.16)

| Measurement | Result |
|---|---|
| Decode speed, CPU only, with everything open | 10.8 tokens/s (the 2026-11-13 benchmark was 10.7). CPU about 98% idle, Windows not paging (about 5 pages/s). RAM used 84% at one reading with 5.0 GiB free after the model was loaded |
| Decode speed, model fully on the GPU | 45 to 58 tokens/s; a reply in about 1.5 s against about 7 s |
| Voice model GPU use (2026-11-13 voice record) | peak 6.68 GiB of 8 GiB, so the language model cannot also sit on the GPU while the voice is on |
| Automatic placement, voice off | 87% of the model in GPU memory (about 6.8 GiB free at the time), 37 tokens/s, reply about 2 s; model ready in 5.5 s; first sentence 0.36 s (2.2 s on the CPU). The server reuses a model already loaded on the CPU whatever options are sent, so the advisor drops a CPU-loaded copy first |
| Closing programs and speed | not changed: with nothing closed the model already ran at its benchmark speed. The listed programs use about 5 GiB in a dry run; the closer has not been run for real on RK's programs |
| Dashboard request rate (one tab, one reply) | peak 31 requests per 5 s against a limit of 40 before the fix; peak 17 after, about 5 of them starting a command |
| Persona replay against the real model (2 conversations x 16 turns, old persona against new) | "your kind" 1 to 0; declines to hold an opinion 1 to 0; tic words (modest, humble, indeed, remain, perhaps) 23 to 13; distinct openings 26 to 25 of 32 (no gain); average reply 43.8 to 41.7 words; average time 10.1 s to 13.6 s |

## 4. RK OBSERVED

In a real spoken conversation on 2026-11-14 to 16 the path microphone, speech recognition, turn, spoken reply worked end to end. RK reported: a weather and headlines request refused, three "too many requests" messages that lost replies, standard-sounding replies, "your kind", and a narrow vocabulary. Each was reproduced or measured and fixed in #79, #80 and #83. Speech recognition mishearings (for example "Indian with rights") remain.

## 5. RK DECISIONS this period

Option H1 for the conversation box (advisor serves the page). Merge all open pull requests in order (2026-11-16). Write `models.toml` for `qwen3.5:9b` only. The close list: Teams, Spotify, Settings, WhatsApp, Tixati, Zen, ChatGPT, Codex, Discord, Steam's web helper, Copilot, Epic Games Launcher, Phone Link and Windscribe (last); all closed by force after a short polite request, interruptions accepted. The advisor chooses the GPU automatically when voice is off.

## 6. UNVERIFIED or not done

- A real press of the microphone button and the ring's colours during it; a very quick tap on the real device.
- `scripts/free_memory.py --apply` on RK's real programs (how Zen, Tixati and the tray apps respond; whether closing the Windscribe app disconnects the VPN).
- Any phone browser (the layout was checked only in a 375 x 812 emulation). Reaching the dashboard from a phone is not built (ADR-0011 Amendment 4, undecided).
- A voice session started straight after a text session (the code forces the model back to the CPU first; not run with the voice worker).
- The persona text review (ADR-0013 A6.3); the persona on RK's own sentences beyond the 32-reply replay.
- Two dashboard tabs over a long session; publisher feed terms for the headlines; junctions and mapped drives for launch containment.
