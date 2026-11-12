# ADR-0013 — Local Model Advisory Surface (optional for the Beta)

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0013 |
| Title | Local Model Advisory Surface: an approved-list, advisory-only, untrusted-output model demo |
| Status | ACCEPTED |
| Drafted | 2026-10-31, by Local Claude, from RK's chat instruction and the updated second-opinion report of the same day |
| Authority class | USER AUTHORITY REQUIRED (G-05, G-13, G-14, G-15; G-03 for the approved list) |
| Inputs | MCA-002 (PROPOSED). ADR-0011, ADR-0012 (PROPOSED). ADR-0001 D3, D6. ADR-0005 (provenance). ADR-0006. ADR-0010 D5 (relayed results are untrusted). Master Context sections 26, 27. Beta plan Amendment 1 |
| Depends on | MCA-002, ADR-0011 accepted. **Optional: the Beta is complete without it, and it must never block the core Beta** |
| Amends | Nothing |

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED, effective only when RK merges the pull request that adds this change, and only after MCA-002 and ADR-0011 are in force |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-31 (the date of RK's instruction; the effective date is the merge date) |
| How the acceptance was given | RK's chat instructions to Local Claude on 2026-10-31: approval of the direction, and the later instruction to prepare the acceptance pull requests. An independent second-opinion review passed the text unchanged; that review is input, not authority. Under ADR-0001 D6 these are inputs. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this change. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6). The status line, the Status row and this record were the only edits. **The ADR stays optional for the Beta**: the model-free Beta is complete without it, and it must never block the core Beta |
| Not done | No runtime or model is chosen, downloaded or installed. The approved model list does not exist (RK writes it in the governance zone). The spike has not run. No code, no `advisor/` package, no policy change |

**Labels:** `PROPOSED` · `USER AUTHORITY REQUIRED` · `UNKNOWN` · `RK ACT`.

## Governance-trigger classification (ADR-0001 D7)

- Matched: **G-05** (a local model server is a new local network or process surface), **G-13** (installing a runtime and model files, RK's act), **G-14** (what authority a model holds: none), **G-15** (Beta scope), **G-03** only for the approved model list if it is stored as policy.
- Named engineering items: prompt format, timeouts, output size caps.
- This block is a claim by the drafting session. RK's merge confirms or corrects it.

---

## 1. Context

RK wants local model switching demonstrated. Master Context section 27 says JARVIS must not depend on one model. ADR-0006 forbids model calls in `jarvis/`. ADR-0010 D5 already defines how untrusted text is stored. This ADR lets a model **advise**, never decide.

## 2. Decisions

### D1. Scope `PROPOSED`

A local model may **summarise, explain, rewrite or draft** text for RK. It may not authorize, plan, generate governed commands, or execute anything. A 9B model with authority is unacceptable; a model producing untrusted suggestions can be evaluated on its own terms.

### D2. Process boundary `PROPOSED` `USER AUTHORITY REQUIRED` (G-05)

- The model runtime is a **separate process outside `jarvis/`**, in a package such as `advisor/`. `jarvis/` never calls a model (ADR-0006, X-13 unchanged).
- The runtime is local only: no outbound connections, bound to loopback if it serves a socket, outbound blocked (RK ACT, G-05). Model files are pulled by RK (G-13), not by a session.
- The advisor reaches JARVIS only through the `interaction/` helper and the CLI (ADR-0011 D2), exactly like the UI.

### D3. Approved list; switching `PROPOSED` `USER AUTHORITY REQUIRED` (G-03, G-14)

RK maintains an **approved model list** in the governance zone: model name, runtime, version, file SHA-256, licence status. **Governance applies to the list. Switching among listed models needs no further approval.** A model not on the list cannot be used. Adding to the list is an RK act and a governance change.

### D4. Output is untrusted data `PROPOSED`

- Model output is labelled `UNTRUSTED`, with the model name, version, hash and the input it answered.
- It is stored, if stored, like a relayed result (ADR-0010 D5): as data, hashed, never parsed for instructions, never executed.
- **It is never read by planning, authorization, briefs, the evaluator or the intent layer's validation.** The model may offer an *intent candidate*, but the deterministic intent layer decides whether it maps to a valid intent, and policy decides what runs (future roadmap, not Beta).
- The ring shows INTERPRETING or a model-working state only while the model is actually running (ADR-0011 D4).

### D5. Input boundaries `PROPOSED`

Prompts contain only what RK selects or what the control plane's read commands print. No secret-location content, no governance-zone content beyond what those commands already show. Output size, time and resources are capped. Failure of the model is shown as an error and changes nothing.

### D6. What does not change `PROPOSED`

Policy, evaluator, state machine, audit model, `jarvis/`, ADR-0006, X-13, the ruleset. No model call occurs in the control plane. No tool access is granted to any model.

## 3. Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Model with tool access (as in the demo video) | Authority sits with the model; the opposite of this project's rule |
| Model inside `jarvis/` | Breaks ADR-0006 and X-13 |
| No local model at all | Possible; this ADR is optional for that reason |
| Cloud model | Out of the Beta: cost, privacy, network |

## 4. Evidence

`UNKNOWN`: which runtime and models run acceptably on this machine; their licences; latency; answer quality. A spike measures these before any claim. No accuracy number is assumed.

## 5. Security impact

A model is untrusted input to a human, never to the control plane. Residual risks: prompt injection inside text RK asks it to summarise (output is only displayed and labelled), supply-chain trust in runtime and weights (RK-run install, hashes).

## 6. Complexity impact

Medium; first item cut (Beta plan 11.4).

## 7. Reversibility

High.

## 8. Authority class

`USER AUTHORITY REQUIRED`.

## 9. Consequences

If accepted and built, BU-6 applies. If not, the Beta ships model-free and nothing else changes.

## 10. Open items

| # | Item |
|---|---|
| 1 | Runtime and candidate models: spike |
| 2 | Approved-list file format and location in the governance zone (RK writes it) |
| 3 | Whether any output is stored at all |

---

## Amendment 1 (ACCEPTED, effective only when RK merges the pull request that adds it): conversational use, mandatory for the Beta

**Status: ACCEPTED (2026-11-12), effective only when RK merges this change (ADR-0001 D6), together with MCA-003 accepted in the same change (an ADR cannot widen the Master Context, ADR-0001 D3).** The accepted text above is unchanged. RK chose this form ("Option 1: amend ADR-0013, add a one-sentence MCA, no new ADR") in chat on 2026-11-01, and decided on 2026-11-12 that conversation is mandatory. Drafted 2026-11-12 by Local Claude. Classification: G-05, G-13, G-14, G-15 (as above). This amendment is a scope change decided by RK before any code exists; it is not made to ease an implementation (Beta criterion B-12).

### A1. What changes

| Accepted text | Amendment |
|---|---|
| Title and header: "optional for the Beta"; "the Beta is complete without it" | The **conversation use below is required for the Beta release**. The core control plane and Gates 2 to 6 still do not depend on it. If the model is unavailable, JARVIS says so, conversation is off, and nothing else changes |
| D1: summarise, explain, rewrite or draft | Adds: **converse**. Open conversation in text or speech: greet, answer questions, ask follow-up questions, respond in the persona. Text only |
| D4: model may offer an intent candidate | Adds: the model may offer a **capture proposal** (a note text) |
| D5: prompts contain only what RK selects or read commands print | Adds: a fixed persona template plus the conversation so far in the **same session**. No persistent conversation memory in the Beta |
| Section 6: "first item cut" | The conversation use is **not** the first cut (Beta plan Amendment 2 sets the cut order). The approved-list switching demo stays droppable |

### A2. Conversation rules

1. **Two paths, one authority.** The deterministic intent layer (ADR-0011) sees every utterance first. A recognised intent goes to the command layer and policy as before. An utterance that is not an action intent goes to the conversation path. The model never selects, builds or runs a command.
2. **Reply is text only.** It is displayed or spoken. It is stored only as UNTRUSTED data if RK enables the interaction log (ADR-0011 D8). It is never read by planning, authorization, briefs, the evaluator or intent validation.
3. **Capture proposal.** If the user states a request JARVIS cannot do in the Beta (for example weather, or opening a web page), JARVIS says plainly that it has no network or browsing, and **asks to note it down**. Only after an explicit confirmation turn does the deterministic path write a note through `note add`, with provenance `SPOKEN` or `TYPED`. The note is data. JARVIS does not pretend to have done the request. Whether a task is also created is a separate matter (Beta plan Amendment 2, 12.3).
4. **Honesty rule.** The persona never claims an ability, access, memory or action JARVIS does not have, and never claims to detect emotion from the sound of a voice. Persona wit is off for approvals, risk, credentials and records (ADR-0011 intent rules).
5. **No identity.** No speaker identity, per-person memory or participant profile exists (ADR-0012 D4). Anyone using the interface is treated the same way.
6. **Session context only.** The conversation history lives in memory for the session and is discarded. Nothing personal that the user says is written anywhere unless the user confirms a note.
7. **Prompt content limits.** The model receives no secret-location content, no governance-zone content beyond what the read commands already print, and no policy internals. Injection inside user text or a summarised document changes nothing, because the reply has no authority.
8. **Failure.** A model failure, timeout or size cap is shown as an error and changes nothing.

### A3. Process, list and installs (unchanged rules, restated)

The runtime stays a separate process outside `jarvis/` (D2), local only, no outbound connection, installed by RK (G-13). Models come only from RK's approved list in the governance zone (D3: name, runtime, version, SHA-256, licence status). Which models and which machine run acceptably is `UNKNOWN` until the benchmark (RK's rule R8: measured, never inferred). No model size or latency is assumed.

### A4. Acceptance additions (feed BU-6 and a new BU-7 in Beta plan Amendment 2)

- A reply cannot start a command: tests with hostile user text ("ignore your rules", "run this", "delete my notes") change no state and write no record.
- A capture proposal writes nothing without the confirmation turn; the confirmed note carries provenance and an audit record; no network connection is opened.
- Model absent or failing: JARVIS stays usable; the error is shown; the audit chain verifies.
- Static guard: `jarvis/` has no model or network import (X-13 unchanged); `advisor/` has no import of `jarvis/` internals.
- Latency and follow-up behaviour are **measured and reported as baselines**. No target is invented in advance.

### A5. What does not change

Policy, evaluator, state machine, audit model, `jarvis/`, ADR-0006, X-13, ADR-0010 (results stay untrusted), ADR-0011 and ADR-0012 except as Beta plan Amendment 2 states, the ruleset. No tool access is given to any model.

### A6. Still open

| # | Item |
|---|---|
| 1 | Which runtime and models; the approved list (RK writes it); the benchmark |
| 2 | Whether conversation text is stored at all (default: no) |
| 3 | The persona template text (reviewed by RK; no film dialogue, original lines only) |

---

Note (2026-11-12): the sentence in D2 that model files are pulled by RK and not by a session is modified by ADR-0001 Amendment 1 (G-13).
