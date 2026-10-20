# JARVIS Decision Call: Idea Note v0.1

**Status:** IDEA NOTE. DRAFT, NON-AUTHORITATIVE. Not approved, not an ADR, not an MCA. It starts nothing, builds nothing and changes no phase.
**Date:** 2026-10-21
**Raised by:** RK, in chat on 2026-10-21.

## 1. The idea

RK saw a reel in which a man walking through a shopping mall gets a phone call from JARVIS. JARVIS says a decision is needed, explains the options it has found, says what it recommends, and asks him to choose. He answers. JARVIS says it will proceed, ends the call, and carries out the choice in the background.

RK wants this for our JARVIS.

> **JARVIS:** I shall try to call only when it matters, sir. And never during the good part of a film.

## 2. In plain words

JARVIS is designed as a capable assistant that is not allowed to make big decisions alone. The call is simply the moment JARVIS says: "This one is yours, sir."

It has four steps:

1. **JARVIS gets stuck on something important.** It stops and waits.
2. **It prepares a short summary:** the options, what it recommends and why.
3. **It reaches RK** and RK chooses.
4. **It carries out that choice, and nothing beyond it.**

## 3. How it fits what already exists

| Step | What already exists or is planned | Where |
|---|---|---|
| Stops and waits | A task that needs authority it does not have is held as `DEFERRED` with reason `APPROVAL_MECHANISM_ABSENT`. The Phase 1 evaluator on the `phase-1/control-plane` branch (not yet merged) already does this | ADR-0002 D2, ADR-0003 D8 and D12 |
| Short summary of options | The decision record with "respectful dissent" and the situation brief | Architecture draft sections 9.2 and 10 |
| RK's answer counts as a decision | The approval mechanism for high-impact (L4) actions is planned for Phase 3. A chat or spoken answer is only an input; the recorded act is what counts | ADR-0002 D4, ADR-0001 D6 |
| Speaking on the phone | The local-only voice chosen for the presence layer | Presence proposal (draft, not merged) |

## 4. Why it cannot be built yet

1. **Proving it is really RK.** If JARVIS acted on any voice that said "yes", someone holding RK's phone, or a copy of RK's voice, could make it do things. Before an answer can count, it needs a check that it came from RK, for example a PIN or a confirmation in an app. Designing that belongs with the approval mechanism (Phase 3).
2. **Phone calls are outside version one.** Master Context §33 lists phone calling and a mobile application as non-goals for v0.1. Changing that needs a deliberate amendment by RK.
3. **Talking to other people is the riskiest part.** JARVIS contacting real people on RK's behalf is external communication: `MAKE_CALL` is DENY in v0.1, and `SEND_MESSAGE` and `SEND_EMAIL` wait for approval (ADR-0003 D12).

## 5. Suggested order (no new phase)

1. **Phase 2 (manual worker bridge):** JARVIS writes a decision note on the computer; RK answers there.
2. **Phase 3 (approval mechanism):** a checked way for RK's answer to count, and a phone notification that a decision is waiting.
3. **After an amendment to §33:** the voice call itself, using the local-only voice.
4. **Last, by its own decision:** JARVIS contacting other people on RK's behalf.

## 6. Ground rules if it is ever built

- A spoken "yes" alone never approves anything.
- JARVIS does only what RK chose, and records it.
- No call or message to anyone else without its own decision by RK.
- The phone is a convenience, not a security boundary.

## 7. What this note does not do

It records the idea so it is not lost. It decides nothing, changes no phase, amends no ADR or Master Context text, and merging it accepts nothing in it.
