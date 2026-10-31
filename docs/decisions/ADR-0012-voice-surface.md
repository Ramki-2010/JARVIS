# ADR-0012 — Voice Surface: Push-to-Talk, Local Speech, Private Voice Profile

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0012 |
| Title | Voice Surface for the v0.1 Beta: push-to-talk, local speech in and out, private voice profile only |
| Status | ACCEPTED |
| Drafted | 2026-10-31, by Local Claude, from RK's chat instruction of the same day |
| Authority class | USER AUTHORITY REQUIRED (G-05, G-06, G-13, G-15) |
| Inputs | MCA-002 (PROPOSED). ADR-0011 (PROPOSED). ADR-0001 D3, D6. ADR-0006 sections 3.2, 6.1, 6.3. ADR-0007. ADR-0008. ADR-0010 section 6. Master Context sections 25, 26. Two uploaded second-opinion reports of 2026-10-31 (input only). Beta plan Amendment 1 |
| Depends on | MCA-002 accepted and ADR-0011 accepted. **Nothing here is in force before then** |
| Amends | Nothing. `jarvis/` and ADR-0006 are unchanged |

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED, effective only when RK merges the pull request that adds this change, and only after MCA-002 and ADR-0011 are in force |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-31 (the date of RK's instruction; the effective date is the merge date) |
| How the acceptance was given | RK's chat instructions to Local Claude on 2026-10-31: approval of the direction, and the later instruction to prepare the acceptance pull requests. An independent second-opinion review passed the text unchanged; that review is input, not authority. Under ADR-0001 D6 these are inputs. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this change. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6). The status line, the Status row and this record were the only edits |
| Not done | **No speech tool is chosen, downloaded or installed.** The D7 spike has not run. The speech tool's licence stays `UNVERIFIED`. No voice asset exists; no Claude session obtains film audio. The firewall block (D-13), the pinned install (D-14) and the data-root layout (D-15) are RK's acts and are not done. No code, no `voice/` package, no policy change |

**Labels:** `PROPOSED` · `USER AUTHORITY REQUIRED` · `ENGINEERING` · `UNKNOWN` · `RK ACT` (something only RK does).

## Governance-trigger classification (ADR-0001 D7)

- Matched: **G-05** (a new runtime with its own interpreter; outbound traffic blocked), **G-06** (microphone, transcripts, voice assets), **G-13** (installing a speech tool and model files), **G-15** (Beta scope via MCA-002).
- Not matched: G-03 (no capability change), G-10 (no external communication exists in the Beta), G-14 (no worker authority).
- Named engineering items: audio library choice among options that pass the spike, sample rates, push-to-talk key binding, test corpus contents.
- This block is a claim by the drafting session. RK's merge confirms or corrects it.

---

## 1. Context

1. MCA-002 allows push-to-talk voice in the v0.1 Beta. RK requires voice in the Beta and wants a private JARVIS voice.
2. The voice runtime is third-party and heavy (speech recognition, speech synthesis, model files). `kokoro-onnx` 0.6.1 declares `requires_python <3.14` (`VERIFIED` earlier from package metadata); other speech packages' Python 3.14 support is `UNKNOWN`. Core JARVIS stays on Python 3.14 and stdlib only. So voice cannot live in `jarvis/`.
3. The video RK referenced uses a voice-cloning app (`VoiceStudio`). Its licence was read from a single video frame as AGPL-3.0; RK states the repository is MIT. Both are `UNVERIFIED` until read at the source.

## 2. Decisions

### D1. Scope `PROPOSED`

Beta voice is: hold-to-talk microphone input, local speech-to-text, the same intent and command path as every other surface (ADR-0011 D1, D6), a persona-rendered reply, and local text-to-speech to the local audio device. Nothing else.

Excluded: wake word, always-listening, barge-in, interruption, external communication, phone calling, any external voice profile, cloud speech, browser speech recognition (treated as cloud), mobile, LAN.

### D2. Process boundary `PROPOSED` `USER AUTHORITY REQUIRED` (G-05)

- A new package `voice/` outside `jarvis/`. It may run in its **own Python interpreter and environment** (outside the repository, under `D:\JARVIS`), so Python-version limits of speech packages do not touch core JARVIS.
- `voice/` has **no network module and no outbound connection**. Enforced three ways: a static check on `voice/` source; a runtime guard in the voice test harness that fails on socket events; and an outbound-block firewall rule for the voice interpreter (**RK ACT**, G-05, RK decision D-13).
- `voice/` reaches the control plane only through the `interaction/` helper that starts `python -m jarvis` as a child (ADR-0011 D2). It never imports `jarvis/`.
- Installing the speech tool, its dependencies and model files is a **RK ACT** (G-13). No Claude session installs or downloads them.

### D3. Privacy rules `PROPOSED` `USER AUTHORITY REQUIRED` (G-06)

1. **Push-to-talk only.** The microphone is open only while the key is held. It is closed while JARVIS is speaking.
2. Speech recognition and synthesis are **local**. No cloud speech.
3. **No audio is stored by default.** Audio lives in memory for the duration of the request. Transcript text is handled by the optional interaction log (ADR-0011 D8), which is off until RK decides.
4. Model files and voice assets live under `D:\JARVIS` (ADR-0007), hash-pinned, never in the repository, never in the audit chain. A static check and `.gitignore`-style test keep audio and model files out of the repository. Location: RK decision D-15.
5. The ring shows LISTENING only while the microphone is actually open and SPEAKING only while audio actually plays (ADR-0011 D4). No microphone indicator is faked.
6. **Structural privacy.** No external-communication adapter exists in the Beta, so the private voice has nowhere external to route. The private profile may play only to the local audio device. That this holds is shown by tests (no outbound connection, no file written outside the data root), not by a label.
7. JARVIS must remain fully usable without a microphone.
8. Spoken secrets: the speaker is warned that speech is transcribed to text, and credentials must not be spoken. Transcript redaction is not claimed.

### D4. Authority `PROPOSED`

Voice is an input surface. **Voice identity grants no authority**; no speaker-verification claim is made. A voice command passes the same intent validation, command layer and policy as a typed one. Low confidence yields a clarification, never a guess. Authority-sensitive intents need an explicit confirmation turn; confirmation is not authorization and policy still decides. Ordinary conversation stays light.

### D5. Voice profile record `PROPOSED`

Each voice profile is described by a record kept in the data root, and a changed asset produces a changed hash:

| Field | Meaning |
|---|---|
| profile ID | name of the profile |
| scope | `private` (the only Beta value) |
| permitted destination | local playback device only |
| runtime | tool and version, interpreter, dependency list |
| asset / model SHA-256 | hash of every model and voice asset file in use |
| source provenance | where the asset came from, as RK states it |
| licence / provenance status | `VERIFIED` or `UNVERIFIED`, never assumed; with the licence names read at source |
| recorded by / when | RK, date |

JARVIS refuses to speak with an asset whose hash differs from the record. The record documents and constrains the scope. Whether the stated provenance is accurate is RK's responsibility, and the status field says so honestly.

### D6. The JARVIS character voice `PROPOSED` `USER AUTHORITY REQUIRED`

- The architecture provides a **replaceable voice asset slot**. RK installs the tool and supplies the voice sample or model locally.
- **No Claude session fetches, extracts, processes or clones film audio or any person's recorded voice.** This follows the project's standing constraint. JARVIS stores only the profile record (D5).
- RK has stated the private use is the character voice and that the tool's repository is MIT. Recorded as RK's statement, `UNVERIFIED`. A software licence covers the software; whether it says anything about a particular person's voice or about film audio is a question the licence and the asset's provenance must answer, and RK owns that answer. The status field in D5 holds it.
- Private, local, internal use only. The asset is never distributed, uploaded or used for external communication. A future external profile (a different, JARVIS-inspired voice) is a separate ADR and requires an external adapter, which does not exist in the Beta.

### D7. Technology selection by spike `PROPOSED`

No speech stack is chosen by this ADR. An isolated spike with no product code verifies, for each candidate, and records evidence: exact licences (application, model, dependencies, `VERIFIED` at source); Python and Windows compatibility; installer provenance and checksums; model-weight provenance and hashes; network behaviour and telemetry (observed); model downloads at runtime (must be none); data handling; latency measured on this machine. **`curl | sh` installers are not used.** Install from an official pinned release, verify checksums, record the install. No accuracy or latency number is quoted unless measured.

### D8. Test corpus `PROPOSED`

A corpus of utterances for the 25 intent families (at least five variants each, a held-out set, negatives, ambiguous and similar-intent examples, filler words, restructuring) is shared with ADR-0011 D6. Lines such as "Daddy is here" and "Good morning, Jarvis" are **test utterances only**. No address-term setting exists; no phrase is mandatory; nothing is hardcoded.

### D9. What does not change `PROPOSED`

`jarvis/`, policy, the evaluator, the audit model, ADR-0006, X-13, the governance zone, the ruleset.

## 3. Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Speech inside `jarvis/` | Breaks stdlib-only and Python 3.14; no |
| Browser speech recognition | Treated as cloud speech; privacy |
| Always-listening or wake word | Larger privacy and safety surface; excluded |
| Cloud speech | Violates local-first and privacy |
| One voice for private and external use | External use is out of the Beta; a separate profile and adapter later |
| Choose VoiceStudio now | Licence, compatibility and provenance unverified; spike decides |

## 4. Evidence

`VERIFIED`: ADR-0006 and X-13 as described; `kokoro-onnx` 0.6.1 `requires_python <3.14`. `UNVERIFIED`: VoiceStudio licence (AGPL-3.0 from a video frame vs MIT per RK), its Python and Windows compatibility, its install method, its network and telemetry behaviour, model hashes and provenance. `UNKNOWN`: STT and TTS latency and quality on this machine.

## 5. Security impact

New local input channel (microphone) and a heavy third-party runtime. Mitigations: separate interpreter, no network, firewall block, hash-pinned assets, push-to-talk, no audio storage, no authority. Residual: supply-chain trust in the speech tool and its models (spike and RK-run install), and a malicious audio asset is only audio (no code path executes it).

## 6. Complexity impact

High relative to the rest of the Beta; first to be cut (Beta plan 11.4).

## 7. Reversibility

High. Remove `voice/` and the environment; nothing in the control plane changes.

## 8. Authority class

`USER AUTHORITY REQUIRED`. Acceptance is RK's merge.

## 9. Consequences

Voice enters the Beta behind a cut line (19 Nov). B-13 lists its limits. A firewall rule, an install and a data-root layout are RK acts. If the spike fails (licence, compatibility, network), voice is cut and reported the same day; acceptance criteria are not weakened.

## 10. Open items

| # | Item |
|---|---|
| 1 | D-13 firewall rule; D-14 pinned install; D-15 data-root layout (RK acts) |
| 2 | Verify the speech tool's licence at source |
| 3 | Whether transcript logging is enabled (ADR-0011 D8) |
| 4 | External voice profile and adapter: later ADR |
