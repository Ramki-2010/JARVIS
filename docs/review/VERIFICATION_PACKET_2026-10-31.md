# JARVIS — Verification Packet for an Independent Reviewer

**Date:** 2026-10-31. **Prepared by:** Local Claude (Sonnet 5.5), at RK's request.
**Status:** NON-AUTHORITATIVE review aid. Not an ADR, not an MCA, not for merge. It exists on a review branch only so an independent reviewer can read everything in one place.
**Repository:** `Ramki-2010/JARVIS` (public). **Review branch:** `review/chatgpt-verification-2026-10-31`. This branch contains `main` plus the five proposed governance documents below and this packet.

## 00. Review history

**Round 1 (ChatGPT):** architecture PASS; asked for three document corrections before acceptance. **Round 2 (applied, documents only; each stacked branch contains its required fixes):**
1. **MCA-002** now *replaces* the lines that contradicted the Beta sub-context, instead of only appending: §23 first and last lines, §24 heading plus an opening sentence ("The full Knowledge Galaxy belongs to later phases."), §25 heading and first line. The reviewer named §24; the same defect existed in §23 and §25 and is fixed too. The "blocked, deferred and cancelled work" wording is clarified as states, not necessarily separate views.
2. **ADR-0011 D2:** the child helper uses an absolute Python 3.14 interpreter path (not resolved via PATH), `-I -m jarvis`, absolute `--config`, `shell=False`, minimal fixed environment; shell invocation prohibited; static test fails on `shell=True` or a bare interpreter name.
3. **ADR-0011 D3:** `Host` and `Origin` accepted only as exactly `http://127.0.0.1:<port>` or `http://localhost:<port>` (Host without scheme); `Origin` required on every Stage B mutation; the token stays independently mandatory.
4. **ADR-0011 D3 (reviewer addition):** strict POST validation: fixed content type, maximum body size checked before parsing, exact field whitelist per route, unexpected, duplicate or missing fields rejected.
5. **Beta plan:** BU-1 aligned, BU-1b added for the interpreter rule.
ADR-0012, ADR-0013 and the voice-licence handling are unchanged. Reopening terminal tasks (D-12) stays unresolved. No code, policy, ruleset or test change; no tests rerun (documents only).

## 0. Instructions for the reviewer

You are asked to verify, not to take over. Treat section 2 as fixed constraints. Separate **verified** from **inferred** from **unknown**. Do not invent versions, licences or numbers. If you think a constraint should change, say so as a proposal for RK, the sole decision-maker. The committed repository documents are authoritative over this packet. Questions are in section 9.

## 1. What this is

JARVIS is a governed, local-first assistant and control plane. RK (founder, they/them) decides. Two Claude roles: Cloud proposes, Local implements and reports facts. Beta target **2026-11-29**. Acceptance criteria are never weakened; scope is cut instead.

State on `main` (verified live 2026-10-31): head `a5e7113`, 415 tests, all pass, 1 skipped (symlink test needs Developer Mode). `doctor` on the real install: healthy, one warning (no registry yet). Ruleset `protect-main` unchanged since 2026-10-11. Tag `phase-0-freeze` = `e919b7a`.

Beta gates (from RK's gate list): B-03, B-07, B-08 pass; B-01, B-04, B-05, B-09, B-12 pass with limitation; **B-02, B-06, B-10, B-11 open**; B-13 (release notes list every limitation, defined in the merged Beta plan, PR #27) finalised at Gate 7. B-06 is blocked because `E:\JARVIS-PROJECT` does not exist. B-10 needs a clean machine. B-11 is RK's first audit anchor.

## 2. Fixed constraints (accepted records on `main`)

- ADR-0006: control plane `jarvis/` is Python 3.14 standard library only; no network, no subprocess, no model calls (static scan + runtime guard, X-13).
- ADR-0007: operational state only under `D:\JARVIS\`.
- ADR-0010: manual worker bridge; relayed results are untrusted data and never influence planning, authorization or briefs; "Voice, UI or model access to any of this needs its own ADR".
- Policy v2: nine capabilities ALLOW; anything L4+ deferred.
- ADR-0001: only RK accepts, by merging; chat approval is an input, not the record. Master Context changes need an accepted MCA (ADR-0001 D3).
- Master Context (v0.1-r1) sections 23, 24, 25, 33 currently say: no cinematic 3D galaxy yet, voice not in v0.1, both listed as non-goals; Phase 7 is the functional dashboard.
- Standing project rule: Claude never fetches, extracts or clones film audio.

## 3. What RK decided in chat (2026-10-31) — inputs, not yet records

1. Amend the Master Context so a galaxy and voice are in v0.1 **as a Beta sub-context**; the finished functional dashboard still lands in Phase 7. Edit the Beta plan accordingly. RK approved both.
2. Phone calls and external communication stay excluded from the Beta.
3. UI write endpoints allowed if the risk is small.
4. Voice must be in the Beta, private/internal use only, using the character voice RK wants; RK states the speech tool's repository is MIT-licensed.
5. LAN access deferred; localhost only.
6. Local-model demo acceptable after governance approval, advisory only.
7. Principle adopted: **strict authority, flexible interaction, controlled exposure**.

## 4. The five proposed documents (all STATUS: PROPOSED, docs only)

| PR | File | Purpose |
|---|---|---|
| #41 | `docs/decisions/MCA-002-v0.1-beta-ui-galaxy-voice-subcontext.md` | Master Context amendment: Beta sub-context for dashboard minimum, ring, read-only galaxy, push-to-talk voice. Master Context text is **not** edited until acceptance. |
| #42 | `docs/plans/JARVIS_BETA_RELEASE_PLAN_2026-11-29.md` (Amendment 1, section 11) | New items BS-5..BS-10, acceptance rows BU-1..BU-6, schedule, cut order, RK decisions D-9..D-15. |
| #43 | `docs/decisions/ADR-0011-local-interaction-surfaces.md` | Localhost UI, process boundary, truthfulness invariants, galaxy rules, 25 intents, task semantics, persona. |
| #44 | `docs/decisions/ADR-0012-voice-surface.md` | Push-to-talk, separate runtime, privacy, voice profile record, voice asset slot, spike. |
| #45 | `docs/decisions/ADR-0013-local-model-advisory-surface.md` | Optional. Approved model list, advisory only, untrusted output. |

Changes outside these files: only the register in `docs/decisions/README.md`. No code, `policy/`, CODEOWNERS or ruleset change.

## 5. Recommendations made (with reasons)

### 5.1 Localhost server — recommended: yes, separate process, read-only first
- `ui/` outside `jarvis/`; stdlib `http.server`; `127.0.0.1` only; random port; per-launch token (not in a query string); Host check; Origin check on writes; no CORS; strict CSP; no CDN; no outbound calls; no direct filesystem or database access.
- (Round 2: interpreter is an absolute path, no shell; Host/Origin exact; Origin required on writes; strict POST validation. See section 00.)
- The UI reads and writes only by starting `python -m jarvis ...` as a child. **`jarvis/` itself never creates subprocesses or sockets.** Static guard extended to enforce this. Reasoning: ADR-0006 and X-13 stay true for the control plane; one controlled boundary; policy and audit apply to every UI action.
- Stage A read-only first. Stage B (only after A passes security tests and RK says so): three existing commands (task create, note add, cancel). Residual risk: low to moderate (DNS rebinding, other local pages, XSS; each has a stated mitigation). **Unverified:** that the stdlib server meets the CSP/token design without friction.
- Fallback if the ADR is not accepted: static read-only HTML file, no server.

### 5.2 Voice privacy — recommended design
Push-to-talk only, mic closed while speaking; local speech in/out; separate interpreter and environment (speech packages such as `kokoro-onnx` 0.6.1 declare `requires_python <3.14`, verified from package metadata); voice has no network (static check, runtime test, and an outbound firewall block that RK applies); no audio stored by default; models and assets under `D:\JARVIS`, hash-pinned; ring shows LISTENING only while the mic is open; **no external-communication adapter exists in the Beta, so the private voice has nowhere to route** (structural, not a label); voice identity grants no authority; install by RK from a pinned release with checksums, never `curl | sh`.

### 5.3 Voice asset and licence
A replaceable asset slot plus an auditable **voice profile record** (profile ID, scope private, destination local playback only, runtime, asset/model SHA-256, provenance as RK states it, licence status VERIFIED/UNVERIFIED). Claude does not obtain or clone film audio. The speech tool's licence is **UNVERIFIED**: a video frame showed AGPL-3.0; RK says MIT; must be read at the source. A software licence covers the software; what it says about a person's voice or film audio is a question for the licence and the asset's provenance, owned by RK. The architecture records and constrains scope; tests, not labels, show that private-only playback holds.

### 5.4 STOP / CANCEL / RESUME / CURRENT_TASK
Nothing runs in the background today, so:
- **CURRENT_TASK**: read-only, shows the open/last-touched task.
- **CANCEL_TASK**: terminates a not-finished task (CANCELLED), final, audited; the existing `cancel`.
- **STOP_TASK**: a request to interrupt, distinct from cancel. Beta answer: "Nothing is currently running." No state change; never cancels.
- **RESUME_TASK**: full re-evaluation (state → policy → task conditions → outcome: continue / remain blocked / defer / reopen / no-op), for every state; re-evaluation does not guarantee reopening. Checked against `jarvis/states.py`: PENDING, BLOCKED, DEFERRED have evaluated edges; RUNNING has no edge to BLOCKED/DEFERRED (ADR-0002 D2 extension still PROPOSED); COMPLETED_UNVERIFIED, FAILED, CANCELLED have **no outgoing edge**, so "reopen" does not exist today. A real reopen needs a state-machine amendment: **open RK decision D-12**.

### 5.5 Galaxy and ring
Ring states derive only from real records/signals. Galaxy is read-only, canvas with simple 3D projection, no third-party library (WebGL/vendored libraries need a separate decision). **Acceptance: every LIVE node and every displayed relationship maps to real data; PREVIEW/DEFERRED/BLOCKED nodes are labelled and never counted as records or activity. Node count need not equal record count.** Performance is measured in a spike; no number is assumed.

### 5.6 Intents and persona
25 intent families, deterministic lexicon, clarify on doubt, confirmation is not authorization, measurement harness first with no target invented. Example utterances are test inputs only. **No address-term configuration exists**; lines like "Daddy is here" are voice test utterances. Persona rendering never changes results; wit off for approvals, risk, credentials, records.

### 5.7 Local models
Optional ADR-0013: separate process outside `jarvis/`; RK-approved list is governed, switching among listed models is not; output untrusted, never read by planning, authorization, briefs or intent validation; a model may only offer an intent candidate in a later roadmap.

### 5.8 GitHub
Each capability (public read, private read, clone, commit, PR, merge, settings, credentials) is a separate governance item. Beta = manual human transfer only.

### 5.9 Schedule and cut rule
UI cut line 14 Nov; voice cut line 19 Nov; cut order: local-model demo, voice, Stage B writes, galaxy, ring; Beta dashboard Stage A last. **Cut scope, never acceptance criteria.** Realism is an estimate, not measured: a single implementer, four gates already open, RC freeze 26 Nov.

## 6. Contradictions found and how each was resolved (or left open)

| # | Contradiction | Resolution |
|---|---|---|
| 1 | Master Context §23/24/25/33 exclude galaxy and voice from v0.1 | MCA-002 (Beta sub-context); not in force until RK merges acceptance |
| 2 | Beta plan §3.3 and risk 8 put UI/voice post-Beta | Amendment 1 (PR #42) |
| 3 | UI server needs sockets; ADR-0006 forbids network in `jarvis/` | Server lives outside `jarvis/`; boundary written in ADR-0011 D2 |
| 4 | Speech stacks are third-party and not Python 3.14 compatible | Separate interpreter; ADR-0012 D2; spike decides the tool |
| 5 | Proposal said "no write endpoints" yet UI actions run commands | Stage A read-only, Stage B three whitelisted commands |
| 6 | Proposal deferred external communication yet included an external voice profile | External profile dropped from Beta |
| 7 | STOP vs CANCEL redundant | STOP distinct (request to interrupt), RK correction applied |
| 8 | RESUME limited to non-terminal states | Full re-evaluation; reopen unavailable until D-12 |
| 9 | "Daddy" as configurable persona data | Removed; test utterance only |
| 10 | Galaxy test "node count equals record count" too rigid | Replaced with LIVE-maps-to-real-data rule |
| 11 | B-13 appeared undefined | Verified: defined in the Beta plan merged as PR #27 (`6df67be`) |
| 12 | Film voice | Open and RK-owned: provenance recorded, status UNVERIFIED, Claude does not obtain the audio |
| 13 | Whether interaction records go in the audit chain | Left open (ADR-0011 D8, off by default) |
| 14 | Round 2: MCA-002 appended Beta wording but left "belongs to a later phase" / "Voice is not part of v0.1" / "— Later" headings in §23-§25 | Replaced; old and new text both listed in MCA-002 sections 1, 3 and 4 |
| 15 | Round 2: "fixed interpreter" and "Origin must match" were underspecified | Absolute interpreter path, no shell, exact Origin/Host rules, strict POST validation (ADR-0011 D2, D3) |

## 7. Claim ledger

| Claim | Status |
|---|---|
| `main` a5e7113, 415 tests pass, 1 skipped | Verified (run 2026-10-31) |
| Ruleset `protect-main` unchanged | Verified (`updated_at` 2026-10-11) |
| `kokoro-onnx` 0.6.1 `requires_python <3.14` | Verified earlier from package metadata |
| State machine edges as in 5.4 | Verified from `jarvis/states.py` |
| Static guard forbids `socket`, `http`, `subprocess` in `jarvis/` | Verified in `tests/test_static_guard.py` |
| Speech tool licence (AGPL-3.0 vs MIT) | UNVERIFIED |
| Speech tool Python 3.14/Windows compatibility, install method, telemetry | UNKNOWN |
| Canvas galaxy frame rate; STT/TTS latency; intent accuracy | UNKNOWN (measure in spikes) |
| Stdlib `http.server` can meet the CSP/token design | UNVERIFIED |
| Schedule is achievable | Judgment, not measured |

## 8. Decisions that remain RK's

D-9 accept MCA-002; D-10 merge the plan amendment; D-11 accept ADR-0011/0012 (0013 optional); D-12 whether RESUME may reopen terminal tasks; D-13 outbound firewall block for voice; D-14 pinned install of the speech tool; D-15 data-root layout for voice assets. Also the pre-existing items: first real registry/contract, B-06 project folder, B-10 machine, B-11 anchor, `gh` credential decision, ADR-0010 D7 event-name deviation, branch cleanup.

## 9. Questions for the reviewer (answer each briefly; mark confidence high/medium/low)

1. Is any statement in sections 5 and 6 contradicted by the committed documents or by ADR-0001/0006/0010? Cite the line.
2. Is the MCA-002 wording sufficient for an Amendment under ADR-0001 D3, or does it widen anything it should not (§26, §31, §33 remaining items)?
3. Is the UI process boundary (child CLI calls; `jarvis/` never spawns or listens) sound, and does it truly leave ADR-0006 and X-13 intact?
4. Is Stage B (task create, note add, cancel) safe enough with token + Origin + Host checks? What attack did we miss?
5. Does the voice design make private-only structurally true? What is the weakest point?
6. Is the RESUME model coherent, given that terminal states have no outgoing edge?
7. Are BU-1..BU-6 measurable, and are any weaker than B-01..B-13?
8. Is the schedule honest, and are the cut lines and order right?
9. Anything risky, contradictory or missing, including in how the film voice question is handled?
10. What would you change before RK merges #41–#45?

## 10. Limits

No code was written or run for this work. The speech tool, Ollama and the video's repositories were not inspected. The two earlier second-opinion reports are inputs only. The reviewer has not necessarily seen the repository; section 2 is a summary, not the source of truth.
