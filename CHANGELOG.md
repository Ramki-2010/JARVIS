# Changelog

All notable changes to JARVIS, newest first. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). No release has been cut: the Beta target moved on 2026-11-26 from 2026-11-29 to the first week of December 2026 (Beta plan Amendment 4) and tagging it is RK's act (`docs/beta/BETA_RELEASE_PROCEDURE.md`). Numbers are pull requests. Built from the list of merged pull requests on 2026-11-20, not from memory.

## [Unreleased] (towards the Beta, first week of December 2026)

### Added (not merged yet, towards the phone)
- Phone access over the private network: a remote profile with an allowlist, its own conversation, a fixed port, login plus token, a lockout, `scripts/make_remote_token.py`, `scripts/remote_gate.py`, `JARVIS_REMOTE=1` in the start script (ADR-0011 A4.6, A4.7, A4.8).

### Decided (documents only)
- The Beta date moves from 2026-11-29 to the first week of December 2026, on RK's word of 2026-11-26. Scope and acceptance are unchanged (Beta plan Amendment 4).
- Phone access over a private network, phone keyboard dictation, a remote allowlist profile, a login plus a long-lived token, and (A4.7) notes and to-dos from the phone, with confirmations bound to the side that proposed them (ADR-0011 Amendment 4, #82, #87, #88, #90). Nothing is built yet.
- ADR-0016, notes about sir, is in the register as PROPOSED (#93); nothing of it is built. Whether it is accepted is RK's decision.
- Register, START HERE, release notes and evidence brought up to date (#86); the pre-Phase-1 gate draft kept as a historical record (#89).

### Added
- Fetcher refuses any connection that reached a non-public address, checked on the connected socket before a request is sent (ADR-0014 Amendment 4, #95). `scripts/boundaries.py`, a read-only report of what can leave or reach into this machine (#96). Unit tests run on every pull request, advisory only (#94). Review checklist, pull-request template, changelog, release procedure with drills and an ideas list (#98). A test that data (model replies, headlines, notes) never becomes a launch or lookup request (#97).
- Dashboard text box (#77), microphone button, hold to talk (#78), phone-sized layout (#81).
- Several lookups in one request, such as the weather and the headlines together (#79).
- `scripts/free_memory.py` and `scripts/start-jarvis.cmd`: close the programs on RK's own list before JARVIS starts (#84).
- The model is placed on the GPU automatically when the voice is off, about 3.4 times faster (#85).
- Ring LISTENING and SPEAKING from the voice's real signal (#75); a glowing PREVIEW dock (#74).
- Offline time and date in 15 zones (#72). Governed local launch of apps, folders, files and games (#73). Weather, Hacker News and Indian headlines, read-only and allowlisted (#71).
- To-do list and a butler's manner (#68); project briefings (#67); the galaxy (#66); voice (#64, #65); text conversation (#63); read-only dashboard and status ring (#61).
- `sync_project_notes` (#70); a read-only wrapper and skill for Claude Code (#54); a static HTML snapshot (#53).

### Changed
- Persona no longer denies time, notes or weather, and the model is told the part of the day each turn (#92).
- Persona v2: opinions instead of disclaimers, a guard for "your kind" and "as an AI", a wider vocabulary (#83).

### Fixed
- "Too many requests" on the dashboard, measured and cured (#80).
- Natural speech for lookups, no canned weather refusal (#79).
- An unencodable character in piped output no longer crashes (#60).

### Security
- ADR-0011 to ADR-0015 accepted with their limits: loopback only, exact Host and Origin, per-launch token, strict POST validation, one allowlisted fetcher, governed launch.

## Phase 1 and the Beta foundations (2026-10-06 to 2026-11-04)

- Control plane: policy, capability evaluator, hash-chained audit, task, note, report, resume, project and doctor commands, with guards that prove `jarvis/` opens no socket and starts no process (#12 to #40).
- Beta workflow end to end with a hostile relayed result (#38); launcher, install check, backup and restore verify (#39).
- Accepted decisions: Phase 0 (ADR-0001 to ADR-0006, MCA-001, #2), ADR-0007 to ADR-0010, MCA-002 and MCA-003, the Beta plan and its amendments (#4 to #59).

## Not in any release yet

- A tag, signed or checksummed release files, and a changelog entry per version: see the release procedure.
