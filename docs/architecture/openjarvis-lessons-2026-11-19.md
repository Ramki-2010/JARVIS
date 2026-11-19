# What we can learn from OpenJarvis (2026-11-19)

**NON-AUTHORITATIVE.** A comparison written by Local Claude at RK's request. It decides nothing; any change it suggests needs its own decision under ADR-0001. Do not confuse the project below with this one: it is an unrelated open-source project that shares the name.

## Sources and what was and was not read

Read: the project's README on GitHub (`open-jarvis/OpenJarvis`), its Stanford "Scaling Intelligence" blog post, its documentation home page, and the documentation pages on memory and security architecture. **Not read: its source code**, and the pages on tools, system access, learning, telemetry and skills (the pages gave names only). Everything below is what those pages say, not what the code does. Product facts may have changed since.

## What it is

Apache-2.0 framework for personal AI that runs on the user's own device, from the Hazy Research and Scaling Intelligence groups at Stanford. Stated design: shared building blocks for on-device agents, evaluation that counts energy, latency and money alongside accuracy, and a learning loop that improves models, prompts and settings from locally kept usage traces. Local by default; cloud only as a fallback. It describes five parts: a model catalogue, an inference engine layer (Ollama and others, with hardware detection and a health command), agents (several kinds, including scheduled and always-on ones), tools and memory, and learning.

## Side by side

| Topic | OpenJarvis (per its pages) | JARVIS here | Assessment |
|---|---|---|---|
| Local-first model | Ollama and others, picks an engine from the hardware | Ollama, one approved model, GPU or CPU chosen automatically and reported | Same idea; ours is narrower and governed by an approved-models list |
| Health check | `doctor` command | `doctor` command, install check | Same |
| Permissions and audit | Guardrails are opt-in wrappers (warn, redact or block); an append-only audit table for security events; a sensitive-file check on file reads | Default-deny policy, hash-chained audit with an anchor, secret-location list, confirmation turns | Ours is stricter by default. Their opt-in default is the weaker choice |
| Memory | A searchable store of document chunks with retrieval and an injection size cap; delete one or clear all. The pages describe no user profile or fact extraction (a profile tool is named only) | None between sessions today; ADR-0016 proposes confirmed one-line notes | Their memory is document search, not "learning about the user", so there is little to copy for RK's request |
| Learning | Fine-tuning, prompt optimisation and engine tuning from local traces | None; ADR-0016 only stores confirmed notes | Heavy for this laptop, hard to reverse, and trains on personal data without a confirmation step. Not for the Beta |
| Skills | Portable skill format, importable from other projects and GitHub | Governed launch catalogue of approved apps | Importing third-party skills means running outsiders' instructions or code. Against our rules for now |
| Scheduling | Scheduled and always-on agents (a morning digest, a monitor) | Nothing runs unless asked | Needs a long-running process surface and an ADR |
| Efficiency | Measures latency, throughput and energy per query with a bench command | `--timing` and measured scripts, evidence in `docs/environment/` | A repeatable bench script would help |
| Interface | Command line, browser app, desktop apps | Dashboard, voice, phone via a private network | Comparable |

## Ideas worth taking, in order of value (none adopted)

1. **Scan before saving (cheap, deterministic).** Their secret and personal-data scanners run on text before it is stored or sent. Adopted in ADR-0016 D6 for notes about sir, and the same check could guard ordinary notes.
2. **A size budget on anything injected into the model.** They cap injected memory (about 2,048 tokens, a minimum relevance). ADR-0016 D5 adopts the same idea with a hard cap.
3. **Delete one and clear all as first-class controls.** Adopted in ADR-0016 D4.
4. **A repeatable bench script** reporting time to first word, tokens per second and the part of the model on the GPU, so measurements such as the 37 against 11 tokens per second can be rerun on any machine. Engineering item, no governance needed beyond review.
5. **A scheduled morning briefing** (weather and headlines at a set time). Attractive, but it needs a process that runs without being asked; post-Beta and an ADR.
6. **Hardware detection at start** to explain placement. Mostly done (the advisor reports where the model sits).

## Ideas rejected for now, and why

Model or prompt training from traces (heavy, personal data, hard to reverse); importing skills from other projects (untrusted code and instructions); opt-in guardrails (we default to refusing); a vector memory (not needed for one-line notes, adds a dependency, and installs need RK's per-item approval).

## UNVERIFIED

That the documentation matches the code; how their audit, approval and sandbox modules behave (only their names were visible); how their memory behaves in use. Worth a second look at their security pages and source only if RK wants a deeper comparison.
