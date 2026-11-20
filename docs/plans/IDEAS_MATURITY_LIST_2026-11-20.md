# Ideas and their maturity (2026-11-20)

**NON-AUTHORITATIVE.** A working list, not a plan. It does not change the Beta plan, any ADR or the cut order. Every item says how ready it is, using a vocabulary borrowed from another open-source project's roadmap:

- **Ready**: well scoped; the path is clear; needs RK's word to start.
- **Design Needed**: the idea is clear but needs an ADR or amendment first (RK decides; ADR-0001).
- **Research-Stage**: exploratory; measure or investigate before designing.
- **Decided**: RK's decision is recorded (the accepted record is named).

| Item | Maturity | Where it stands |
|---|---|---|
| Phone access over a private network (Tailscale), dictation, remote profile, notes and to-dos from the phone | Decided (ADR-0011 A4.6, A4.7), **not built** | Needs RK's laptop steps and a measurement of what the proxy sends; then one build session |
| Notes about sir: confirmed, forgettable observations (ADR-0016) | Design Needed (PROPOSED, PR 93) | RK merges; then a build session; measure usefulness on RK's own sentences |
| Tests on every pull request | Ready (PR 94, advisory) | RK merges; making it a required check is a separate word |
| Resolved-address check on lookups (ADR-0014 A4) | Ready (PR 95) | Awaiting RK's merge |
| Read-only boundaries report | Ready (PR 96) | Awaiting RK's merge |
| Review checklist, pull-request template, changelog, release procedure | Ready (PR 98, this one) | Awaiting RK's merge |
| A tagged Beta release with checksums | Decided to prepare; the tag is RK's act | At the Beta cut, after the drills |
| Dependency-advisory alerts on the repository | Ready (alerts only; automatic upgrade pull requests stay off) | A repository setting, switched on by Local Claude on RK's word of 2026-11-20 (the vulnerability-alerts setting only; see the pull request that adds this list) |
| A rule test: text from the phone, a lookup or a note about sir never reaches a launch request or a lookup query | Ready for what exists (PR 97); the phone and notes cases wait for their builds | Listed as required tests in ADR-0011 A4.6.8 and ADR-0016 |
| A repeatable speed-test script (time to first word, tokens per second, share of the model on the GPU) | Ready | Small operator script; nothing governed |
| Hardware detection summary at start | Ready (mostly done: placement is reported) | Optional polish |
| A scheduled morning briefing (weather and headlines at a set time) | Design Needed | Needs something that runs without being asked: a new process surface, so an ADR first; after the Beta |
| Anything that learns from conversations beyond confirmed notes (training, tuning) | Research-Stage | Not planned; heavy, personal data, hard to reverse |
| Importing other projects' skills or tools | Research-Stage | Against current rules (untrusted instructions); not planned |
| A message-app front end (Telegram, WhatsApp) | Research-Stage | Every message passes a third party; not planned; the private network is the chosen phone route |
| "2" for "Two" in film titles; fuzzy spelling | Ready | From the 2026-11-16 handoff |
| Speech-recognition mishearings ("Indian with rights") | Research-Stage | Needs measured examples |
| Persona review (ADR-0013 A6.3) | Waiting on RK's comments | Apply against the numbering of the sheet on `main` |
