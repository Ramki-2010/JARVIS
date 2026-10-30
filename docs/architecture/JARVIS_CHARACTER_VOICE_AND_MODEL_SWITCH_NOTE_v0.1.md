# JARVIS Character, Voice, Model Switch and Phone Calls: Idea Note v0.1

**Status:** IDEA NOTE. DRAFT, NON-AUTHORITATIVE. Not approved, not an ADR, not an MCA. It starts nothing, builds nothing, adds no phase and changes no Master Context text.
**Date:** 2026-10-30
**Raised by:** RK, in chat on 2026-10-30, after watching short videos (section 2).
**Updated:** 2026-10-30, at RK's request: a third video added (sections 2, 3, 6, 7A and 8).
**Labels:** `VERIFIED`, `UNKNOWN`, `PROPOSED`, `USER AUTHORITY REQUIRED`, as in the architecture draft.

## 1. What RK asked for

RK found that a creator's "Jarvis" demo looks like the project and asked for these to be recorded as wishes for ours. They are stated preferences. They become binding only through RK's recorded act of merging (ADR-0001 D6).

1. **The voice of the film's J.A.R.V.I.S.** RK says the demo uses it and that nobody has filed a copyright claim. RK approved the voice overall, **not limited to private use**, and said it will not be used anywhere it is legally prohibited (section 4).
2. **The same dry wit, humour and small quirks** (section 3).
3. **Switching between a local and an online model** (section 5).
4. **Anything else worth taking from the videos** (sections 6, 7 and 7A). The second video shows JARVIS **making a phone call for RK**, and the third shows **looking things up, searching the web and describing a shared screen**. RK asked for both to be added.

Settled earlier and still in force (presence proposal, 2026-10-21): no new phase, nothing that complicates the existing process, and voice that runs locally.

> **JARVIS:** Four wishes, sir, and a fifth that arrived while the other four were still being filed. I shall treat it as enthusiasm.

## 2. What the videos showed, and what I could not check

- Video one (39 seconds, "Jarvis is now running 100% locally on my machine"): a voice assistant on a dark screen with a ring that shows when it is listening or speaking. A badge names a small local model. A cost counter reads zero, and three badges read cloud off, invoice none, listening no one. It reads the person's calendar and comments on it dryly. A graph of the person's notes sits behind it.
- Video two (73 seconds): the assistant phones a restaurant to book a table (section 7). The ring is there again, and the badge now names a cloud model.
- Video three (60 seconds, "I Built JARVIS with Claude Fable 5"): the assistant introduces itself in character, pulls up information from the creator's own notes and offers to read it aloud, searches the web for cheaper alternatives to a paid tool and shows its sources, and describes a browser tab the creator shares (section 7A). The badge names a different cloud model from video two.
- `VERIFIED` I read the captions of all three and about half the frames of each. `UNKNOWN` I did not listen to the audio, so I cannot say whose voice it is. `UNKNOWN` how either is built, how reliable it is, or what it costs.
- Lines from the videos are not copied here. Only the patterns are used, and every sample line below is written fresh. This is the same rule the architecture draft already applies to the films.

## 3. Character: what we have, and what to add

`VERIFIED` The architecture draft (section 3) already specifies "sir", dry understated wit, formal British diction, candour about limits, and a wit dial that switches humour off for approvals, risk, credentials and records. Nothing below overrides it.

Patterns from the videos worth adding, each as a **style example, never a script**:

| Pattern | Fresh sample line |
|---|---|
| A running gag about costing nothing (fits the zero-spend policy) | "Local mode, sir. The meter reads zero, and I find I rather like the number." |
| Narrating the search for a tool before using it | "One moment, sir, while I establish whether I own the right instrument." |
| Dry remarks about RK's own data | "Your calendar lists three meetings and a gap marked 'misc', sir. I admire the mystery." |
| Gentle jokes about its own status | "I have been promoted from tool to housemate, sir. The salary is unchanged." |
| A dry line after good news | "Booked for eight, sir. The venue offered no resistance; I shall file that under unexpected courtesy." |
| Refusing to guess | "I have no number for that place, sir, and I would rather ask than guess. A name and a city will do." |
| A self-introduction in character | "Good morning, sir. I am your second brain and, on request, your conscience. I keep the notes; you keep the credit." |
| A morning exchange that skips the pleasantries | "Present and fully operational, sir, which is more than I can say for the backlog. Where shall we begin?" |
| Offering the next step after an answer | "That is the comparison, sir. Shall I set the sources side by side, or would you rather argue with them first?" |

Rules that stay: the quip never carries or hides the information; no jokes in approvals, risk, credentials, money or any canonical record; wit is a style and grants nothing (architecture draft 3.3). Persona scope for Claude Code sessions is still open (decision D-7).

## 4. Voice: RK's decision, recorded

**RK's decision (2026-10-30, updated the same day):** the film voice is approved overall. It is **not limited to private use**. RK will not use it anywhere it is legally prohibited. This is RK's stated preference and RK takes the legal judgment on each use.

**What I am recording, and what I am not.**
- I cannot approve a voice or decide what is lawful. RK's merge of this note is the recorded act; the legal judgment stays RK's.
- This is **not legal advice**, and I cannot say how the law applies in RK's country. "Nobody has filed a claim" is not the same as having permission. A recording of an actor's voice can carry copyright, and the voice itself can carry personality rights. Terms of some cloning services forbid cloning a real person.
- `UNKNOWN` which uses are lawful. That is the point where a lawyer or the rights holder is the right source, not this note.
- **I will not obtain, download or process film audio.** That step needs a fresh instruction from RK. At that point I will ask where the audio comes from and what RK relies on for it being lawful to use.
- No voice engine is chosen and nothing is installed by this note.

**Guardrails proposed for how "not where it is prohibited" is applied (`PROPOSED`):**
1. **Legality is checked per use, by RK.** Private listening on RK's own machine is on. Every other use is **off by default** until RK has recorded that it is lawful for that use: sharing, posting, video or audio that others hear, anything commercial, a phone call to a third party, and any publication. JARVIS cannot check this and does not decide it.
2. **Nothing voice-related goes in the public repository** unless RK records a lawful basis for that. The repository is public, so committing a sample, a model or a recording is publication. I recommend never.
3. The voice engine sits behind an interface and a per-use setting, so a licensed voice can replace the film voice for any use without other changes.
4. Generation is local (the presence proposal: voice local only). No audio or sample leaves the machine.
5. Voice files live under `D:\JARVIS\data\`, never in the repository (ADR-0007).
6. Installing a speech engine is a software install (G-13) and needs RK's instruction at that step.
7. Voice is a later presence-layer item (Master Context section 25; a v0.1 non-goal). Phase 1 output stays in Record voice.

## 5. Switching between a local and an online model

`VERIFIED` Master Context section 27 asks for a model abstraction. Section 28 says to prefer local, give API-heavy work a budget, avoid uncontrolled API loops, and never introduce cloud dependencies silently. Ollama and llama.cpp are named as optional local runtimes (section 40.5). `VERIFIED` Phase 1 has no model call and no network (ADR-0002 D1).

**Rule RK agreed (2026-10-30), proposed in full:**
1. **Local is the default**, always.
2. **Switching to local is always allowed**, by anyone, at any time. It narrows exposure and cost.
3. **Switching to online needs RK's explicit confirmation, and not by voice.** A spoken "yes" is an input, not an approval (ADR-0001 D6). The confirmation is a button or command that is recorded.
4. **A budget first.** Online stays off until RK sets a spending limit. The counter shows the running cost in rupees (zero-spend policy, G-08).
5. **Logged.** Every switch and every online call is an audit entry.
6. **Some data never goes online:** anything in the user-secret locations, the governance zone, the data root, and anything RK marks private.
7. **The switch is a setting, not a permission.** It lives with the control-plane configuration in the governance zone. A model asking to go online is a request, not a switch.
8. **Always visible:** cloud on or off, running cost, and whether JARVIS is listening, as the first video does.

Triggers it touches when built: G-05 (network), G-06 (data leaving the machine), G-07 (keys and accounts), G-08 (money). `UNKNOWN` which later phase first calls any model (the presence proposal says the same). `UNKNOWN` which local model fits this laptop; nothing is chosen. Local runtimes stay optional.

## 6. Other things worth taking from the videos

| Seen | Where it fits | Note |
|---|---|---|
| Status ring: listening, speaking, "reaching for the tools" | Presence layer; the status snapshot planned for Phase 1 | Matches the orb-plus-HUD look RK already chose |
| Model name badge and a cost counter | Section 5 | Rupees, not dollars |
| Privacy badges: cloud, invoice, listening | Section 5 | A trust indicator, backed by the rule |
| Ring, cube and face views | Presence layer, later | Extra views are optional |
| A graph of notes by type | Memory draft; the 3D Galaxy is a v0.1 non-goal (section 24) | Later |
| Local web page on a loopback address | Matches the loopback-only guardrail | |
| Text box with example prompts and quick buttons | Dashboard phase | |
| Addressed by name, always listening | Wake word is a v0.1 non-goal (section 33) | Prefer push-to-talk for privacy |
| Reading a calendar | A connection to an account: credentials (G-07), network (G-05), and a new capability | Not planned |
| Toggles named EYES, HOLO, FOCUS, REFLEX | `UNKNOWN` what they do | EYES is probably the screen- or tab-sharing switch: video three shows a browser banner saying a tab is being shared, with a stop button. Not confirmed, and not a camera as far as I saw. HOLO, FOCUS and REFLEX stay `UNKNOWN` (section 7A) |
| Refusing to invent a phone number it had no record of | Already our rule: candid about limits, evidence over guessing | Keep |

## 7. Ability from the second video: JARVIS phones someone for RK

**What was shown (paraphrased).** RK asks JARVIS to book a table. A call card appears with the state (dialing, on the call, ended), the contact and number, a one-line status, a cancel button and a link to a recording. JARVIS, in a synthetic voice, talks to the restaurant, receives a counter-offer, says it will call back, and ends the call. It tells RK what happened and asks which option to take. RK says yes. JARVIS calls back, confirms, and reports the result with a dry remark. Asked earlier for a number it had no record of, it declined to guess and asked for a name and a city.

**Ideas worth keeping.**
- A **call card with a stop button**, so RK can end a call at any moment.
- The **pause-and-ask loop**: counter-offer, back to RK, explicit decision, then act. It is the approval mechanism planned for Phase 3 (ADR-0002 D4), with a phone call as the thing being approved.
- **Never invent data** such as a phone number.
- A short spoken outcome with one dry line.
- A **recording as audit evidence**, if RK enables it (see cautions).

**Why it cannot start now.**
- Phone calling is a v0.1 non-goal (Master Context section 33) and `MAKE_CALL` is DENY in the Phase 1 policy.
- It needs a phone-calling account and number, real-time speech in and out, an online model for quality, and money for each minute. That touches G-05, G-06, G-07 and G-08 and the zero-spend policy. `UNKNOWN` whether any free route exists.
- It shares its parts with the **decision-call idea note** (JARVIS phones RK). Both need telephony and the approval loop, so they should be built once.

**Cautions (`PROPOSED`).**
1. **Say it is automated.** In the demo the caller called itself an assistant and never said it is an AI. JARVIS should state at the start that it is an automated assistant. `UNKNOWN` what the rules on automated and recorded calls are in RK's country; check before any real call.
2. **Recording is off by default.** A recording holds a stranger's voice and RK's details, so consent law applies. Any recording stays under `D:\JARVIS\data\`, never in the repository (ADR-0007).
3. **Personal data leaves the machine** (RK's name, party size, a phone number) to a stranger and to the calling and model providers (G-06).
4. **A booking can commit RK** (a deposit, a cancellation fee). Committing needs RK's recorded approval, never a spoken yes (ADR-0001 D6). Information-only calls are low risk. Anything that commits money is financial.
5. **The person on the call is untrusted input.** What they say cannot change policy or approvals.
6. **Limits against call loops:** one number per task, an allow-list or confirmation per number, no emergency numbers, rate limits (Master Context section 28).
7. **The voice on a call is a third-party use.** Under section 4 the film voice is off by default for calls until RK has recorded a lawful basis for calls specifically. The default is a licensed, neutral voice.

**Where it fits.** No new phase. It needs the approval mechanism (ADR-0002 D4), isolation, and an accepted change to move `MAKE_CALL` out of DENY (G-03, G-15; likely an MCA because it is a v0.1 non-goal). The call card belongs to the dashboard phase.

## 7A. Abilities from the third video: notes, web search and a shared screen

**What was shown (paraphrased).**
- **In-character self-introduction** and a short morning exchange that skips the pleasantries.
- **Pulling up information from the creator's own notes** on request, with an offer to read it aloud if asked.
- **A web search** for cheaper alternatives to a paid tool. The answer gave prices, a recommendation, a remark about timing, an offer for a next step, and a list of the sources it used under the answer.
- **A shared browser tab.** The creator shares a tab and asks what the assistant sees. It describes the page. The browser's own banner, "sharing this tab" with a stop button, is visible.
- **The notes graph with hover cards:** pointing at a node shows a small card with its type, its number of connections and a one-line description.
- **A text box** with example prompts and a row of buttons, for typing instead of speaking.
- The badge names a different cloud model from the one in video two. Across the three videos the badge changes, which fits the visible model switch in section 5.

`UNKNOWN` whether the prices in the video are right. They are an example of the format, not a fact I checked.

| Ability | Where it fits | What it would need, and the trigger | Verdict |
|---|---|---|---|
| Self-introduction and morning banter | Character, section 3 | Nothing new. Briefing voice only | Adopt as style now (documentation) |
| Pull up RK's notes on request; read aloud on request | Memory draft; the presence layer; Obsidian as the viewer | Local only. The notes are RK's data and are not sent online unless the section 5 rule allows it. Reading aloud follows the voice rules in section 4 | Later, with memory and the presence layer |
| Web search that shows its sources | Capability `SEARCH_WEB`, which the Phase 1 policy marks DEFER because it needs isolation | Network (G-05), isolation (Phase 3), the research phase, and the online and cost rules in section 5. What it finds is `REPORTED`, not verified (ADR-0005 D8) | Later. The **habit of showing sources** under every answer is worth adopting now |
| Share a tab or screen and have JARVIS describe it | Probably the EYES toggle (section 6) | Screen content can hold secrets and other people's data, and "full computer vision" is a v0.1 non-goal (section 33). Proposed limits: RK starts it each time, a visible indicator with a stop button stays on, never continuous, a local model by default, and screen content never goes online unless the section 5 rule is met (G-06, G-07) | Needs RK's decision; not planned |
| Hover cards on the notes graph | Memory draft; the 3D Galaxy is a v0.1 non-goal (section 24) | None | Later |
| Typed prompt box and buttons | Dashboard phase | None | Later |
| A visible model badge that changes | Section 5 | None | Keep |

> **JARVIS:** I note, sir, that I am now expected to read the notes, search the web, watch the screen and remain polite throughout. I accept, with the usual conditions attached.

## 8. Decisions for RK

| # | Decision | Default if left open |
|---|---|---|
| 1 | Confirm the model-switch rule in section 5 as written | Not applied; nothing is built |
| 2 | A spending budget before any online use | No online use |
| 3 | The voice engine, and where the source audio comes from (later, with a fresh instruction) | No voice, no engine |
| 4 | For each use beyond private listening (sharing, posting, public, commercial, calls): record the lawful basis before it is switched on | Off |
| 5 | Whether a camera or screen-sharing feature (EYES) is wanted at all. If screen sharing: started by RK each time, a visible indicator and stop button, never continuous, a local model by default (section 7A) | Not wanted |
| 6 | Whether calendar-style account connections are wanted later | Not planned |
| 7 | Whether phone calling is wanted at all (a v0.1 non-goal), and if so: disclosure as an automated assistant (recommended yes), recording (recommended off), an allow-list of numbers | Not wanted |
| 8 | The voice on calls (recommended: a licensed neutral voice unless a lawful basis for calls is recorded) | Licensed neutral voice |
| 9 | Persona scope for Claude Code sessions (D-7) | Runtime only |
| 10 | Whether to add the new sample lines to the architecture draft's phrasebook (a separate, small follow-up PR) | Not added |
| 11 | Whether web search is wanted, and under what limits (sources always shown; results treated as unverified until checked; the section 5 online rules apply) | Not planned |
| 12 | Whether JARVIS should pull up RK's notes and read them aloud on request, later, with the memory and presence work | Not planned |

## 9. What this note does not do

It adds no phase, reorders none, changes no Master Context, ADR or policy text, builds no code, installs nothing, obtains no audio, chooses no voice engine or model, and creates nothing under `D:\JARVIS\`. It records no decision except RK's stated preferences. Merging it accepts nothing in it.

> **JARVIS:** The wishes are filed, sir, the voice is approved, and the question of where it may be heard is yours to answer one use at a time. I shall keep the list short.
