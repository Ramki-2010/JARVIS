# JARVIS Presence Layer and Fast-Track Proposal v0.1

**Status:** DRAFT FOR REVIEW. NON-AUTHORITATIVE. Not approved. Not an ADR and not an MCA. It amends nothing, creates no code and starts no phase.
**Date:** 2026-10-21
**Depends on:** Master Context 0.1-r1, MCA-001, ADR-0001 to ADR-0007 (accepted), and the draft `JARVIS_INFORMATION_AND_MEMORY_ARCHITECTURE_v0.1.md` (draft, merged in PR #5).

> **Update, later on 2026-10-21.** The text below is unchanged from when it was written. RK approved publishing it; that does not accept the proposals in it. Since it was written:
> - Python: RK chose option A. CPython 3.14.7 is installed alongside 3.10, and ADR-0006 records the decision (PR #7). Python 3.10's end of life is 2026-10-01 per the Python developer guide.
> - `D:\JARVIS\governance\` and `D:\JARVIS\data\` were created on RK's instruction and passed the LF-14 check.
> - `.gitattributes` (LF): decided, and committed on the `phase-1/control-plane` branch, not yet merged.
> - Phase 1 has started on RK's instruction.
> - The initial user-secret locations and the build-session permission mode are decided in ADR-0008 (PR #8).
> - Section 6's first four gates and section 7 questions 1 to 3 are therefore resolved. Questions 4 and 5 remain open.

Labels as in the architecture draft: `VERIFIED`, `UNKNOWN`, `MASTER CONTEXT POLICY`, `PROPOSED`, `USER AUTHORITY REQUIRED`, `LOCAL FACT CHECK REQUIRED`.

## 1. What RK asked for, and what RK settled

Request (chat, 2026-10-21): a JARVIS with a reactive on-screen face that moves as it speaks, as in the films; a voice line; a memory system that loads only what a task needs. Source material: a how-to video transcript and four open-source projects (section 2).

Settled by RK in this session (recorded as stated preferences; binding only through RK's recorded acceptance, ADR-0001 D6):

- The change must **not complicate the existing process**, must **fast-track** the work, and must **not add a phase**.
- Voice is **local only**.
- Memory uses **Obsidian as a viewer**.
- The look is **orb plus HUD**: a particle orb that deforms with the voice, with holographic status panels around it.

> **JARVIS:** Four answers, sir, and not one of them adds a phase. I shall try not to take that as a challenge.

## 2. Source review (Master Context 40.10 format)

Last checked 2026-10-21 from the public pages only. Repository activity dates were not shown, so recency is `UNKNOWN`. Default decision is WATCH / STUDY (MC 40.10). Nothing is integrated by this document.

| Project | License | Relevance | Security relevance | Limitations | Proposed decision |
|---|---|---|---|---|---|
| `jaredrhod/ai-visualizer` | AGPL-3.0-or-later | The face. Four canvas designs; driven by a state file and a 64-sample waveform; stdlib Python server bound to 127.0.0.1; plain HTML/JS | Low. Loopback only; custom faces are arbitrary JS; outbound calls not documented | AGPL: copying it into our Apache-2.0 repo would pull the code toward AGPL | STUDY, then reimplement the orb and HUD ourselves. No code copied |
| `jaredrhod/backtalk` | AGPL-3.0-or-later | The voice. Push-to-talk, local Whisper in, local Kokoro out, optional ElevenLabs cloud | **High in two places:** a global keyboard listener; an auto-approve mode (`bypassPermissions`) that a spoken command can switch on by having the agent edit its own config | Needs a Claude subscription, `uv`, `espeak-ng`, about 1 GB of models | STUDY the architecture. **Reject** the auto-approve behaviour outright (ADR-0001 D9, MC 12 L5). Reimplement, no copying |
| `jaredrhod/ai-memory-vault` | CC BY-SA 4.0 | Memory. Boot file, vault index, daily note, memory redirect; progressive loading so the agent does not read everything | Medium. Agent write access to the vault is not described on the page | Persona shipped in the template is profane, not ours | STUDY the pattern. Our `START HERE.md` already plays the vault-index role for sessions |
| `Panniantong/Agent-Reach` | MIT | Web and social reach for an agent (research phase) | **High for cookie-based platforms:** it reuses browser logins and stores cookies; it asks agents to run installers with exec permission | Platform blocks make it unstable | WATCH. Revisit only at the Research phase, and only the no-credential routes (web read, YouTube subtitles, RSS, keyless search). No cookie-based platforms |
| `jaredrhod/barehands` (webcam hand control) | not read | Named on the site only | UNKNOWN | Not assessed | WATCH. Not assessed in this review |
| The how-to video | n/a | Needs only Claude Code and Obsidian. Steps: a boot file with identity and rules, a vault index as a map, then a voice line and a visualizer | n/a | Transcript only; the creator is not named in it | Used as a concept reference |

`UNKNOWN`: the contents of the voice and visualizer prompts the site says it offers; I did not retrieve them and they are not needed, since we reimplement.

## 3. Fit with the existing roadmap: no new phase

Current phase order, MCA-001 (accepted): P1 Deterministic Control Plane; P2 Manual Worker Bridge; P3 Local Isolation; P4 Controlled Coding and Verification; P5 Research Engine and Autonomous R&D; P6 Scheduler and Background Autonomy; P7 Functional Dashboard.

Principle: the face and voice are a **presence layer**. They display status and carry speech. They hold **no authority**, decide nothing, approve nothing and sit outside the governance core.

| Existing phase | What the presence layer adds | Cost to the phase |
|---|---|---|
| **P1** Control Plane | One addition inside work already planned: the CLI `status` command also emits a machine-readable status snapshot (state, task, autonomy level, verification, errors) written as a file. This is the contract the face reads. No server, no network, no model | A schema and one output format; no new component |
| **P2** Manual Worker Bridge | Optional, outside JARVIS: the local voice adapter may front RK's own Claude Code sessions as a developer aid. JARVIS is not involved and no permission mode changes | None to JARVIS |
| **P3** Local Isolation | Any presence server binds to loopback only and runs under the isolation rules like any other process | A checklist line |
| **P4, P6** | Unchanged | None |
| **First phase where JARVIS itself calls a model** (`UNKNOWN`: no accepted record fixes it; Phase 1 has none, ADR-0002 D1; the unaccepted gate draft suggested the research engine, now P5) | The voice adapter attaches behind whatever model interface that phase builds: local speech-in, local speech-out. This is the first time JARVIS itself can speak | An adapter behind an interface that phase builds anyway |
| **P7** Functional Dashboard | The dashboard **is** the face: orb for state, HUD panels for the MC 23 fields (status, project, task, action, model, tools, level, verification, errors; pause, resume, stop, logs, report) | Same dashboard, richer skin |

**Where the time is saved:** the face is front-end only and needs just the status snapshot from P1. It can therefore be built **in parallel** by a separate session on demo data while the control plane is built, instead of waiting for P7. That is the fast-track, and it adds no phase and does not change the order of any phase.

Master Context text that this touches (`USER AUTHORITY REQUIRED`; a Master Context change needs an accepted MCA, ADR-0001 G-01 and G-15):

- §23 "do not build the cinematic UI yet" and §25 "voice is not part of v0.1": they would need a narrow amendment saying that presence-layer front-end work may proceed in parallel at any time, on status data only, without authority.
- §24 (the 3D Knowledge Galaxy) stays later and is untouched. The orb and HUD are not the Galaxy.
- §30 Phase 7 and MCA-001 wording: no phase added, removed or reordered.

Whether to draft that amendment (an MCA-002) is RK's call. This document does not draft it.

## 4. Guardrails (all `PROPOSED`, grounded in accepted records)

1. **No authority.** The presence layer cannot approve, grant or change anything. A spoken "yes" is not approval: approval is RK's recorded act (ADR-0001 D6).
2. **No permission bypass.** No voice command may change a permission mode, rule, ruleset or config. The permission mode of a session that can modify the repository is itself a trigger (G-07).
3. **Local only.** Speech recognition and synthesis run on the machine. No audio leaves it. Any cloud voice is a separate decision (G-06, G-08, zero-spend).
4. **Loopback and read-only.** Any server binds to 127.0.0.1 and serves only the face and the status snapshot. Custom faces are untrusted code.
5. **Signals live outside the repo.** The status file and voice-state or waveform files are operational state. They go under `D:\JARVIS\data\` (ADR-0007; layout is decision D-17 in the architecture draft), never in the repository.
6. **Licenses.** The repository is Apache-2.0. We reimplement; we do not copy AGPL or share-alike material.
7. **Voice of the character.** The face and voice speak in the Briefing voice (sir, dry wit) from the architecture draft. Phase 1 CLI output stays in Record voice.
8. **Installs.** Whisper, Kokoro and their system dependencies are software installs (G-13) and need RK's explicit instruction at that step.

## 5. Memory

PROPOSED, consistent with the architecture draft and ADR-0007:

- Memory content lives under `D:\JARVIS\data\memory\` (layout `UNKNOWN`, ADR-0007 D5, decision D-17). Obsidian is the human-facing window over it. It is not a source of truth and not authority.
- Progressive loading as in the video: a short index that maps what exists, so a task loads only the notes it needs. `START HERE.md` is already this for build sessions.
- Persona text for Claude Code sessions (a `CLAUDE.md` persona) is decision D-7 and stays open. Today `CLAUDE.md` has no persona.

## 6. Fast-track: what actually gates the start of Phase 1

My reading of the accepted records. Phase 1 starts only on RK's instruction (`START HERE.md`).

| Gate | Why it gates | Status | Recommended |
|---|---|---|---|
| Python option and install | ADR-0006 left it `Not decided` (U-11). Installed Python is 3.10.11, which lacks `tomllib`. The Python 3.10 end-of-life month is October 2026; the exact day is unverified (the PEP and a secondary source disagree on precision), and it may already be past | **Open. RK decision.** The install is G-13 | Decide the version now; it is the single biggest unblocker. After install, run ADR-0006 V-1 checks |
| Create `D:\JARVIS\`, `governance\`, `data\` and run the LF-14 check | ADR-0004 §9 and ADR-0007 §9: before Phase 1 writes anything | **Open. Needs RK's instruction** | Instruct it, then I run the read-only check |
| `.gitattributes` to pin LF | ADR-0006 D-5; `core.autocrlf=true` | Open, small | Decide with the batch |
| RK's instruction to start | START HERE | Open | After the three above |

Not on the critical path for Phase 1 (deferrable, with reason):

- **Secret store location (G-07):** Phase 1 makes no network call and its loader rejects secret-like keys (ADR-0002 D1).
- **Audit anchor ref and path (G-12):** ADR-0005 ties the GitHub check to the first anchor push, not to Phase 1 start. `UNKNOWN` whether Phase 1 exit (CP-1) requires it; check before relying on this.
- **Backup, session-handoff location, `memory\` layout (D-15, D-17):** none is read by Phase 1.
- **Architecture-draft decisions D-2, D-3, D-5 to D-17:** none blocks Phase 1.

So three small decisions and one instruction stand between today and a running Phase 1. Everything else can wait without slowing it.

## 7. Open questions for RK

1. Python version to install (and approval to install it).
2. Instruct creation of `D:\JARVIS\` and its two directories?
3. Add `.gitattributes`?
4. Should an MCA-002 be drafted for the narrow §23/§25 parallel-front-end wording in section 3?
5. Whether the voice adapter may front RK's own Claude Code sessions during P2 as a developer aid.

## 8. What this document does not do

It starts no phase, adds no phase, reorders none, changes no Master Context text and creates nothing under `D:\JARVIS\`. It records no decision. Merging it would not accept anything in it.

> **JARVIS:** The blueprint is ready, sir. The three decisions are small. I would, with respect, recommend making them before the next idea arrives.
