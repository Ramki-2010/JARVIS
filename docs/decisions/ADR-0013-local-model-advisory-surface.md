# ADR-0013 — Local Model Advisory Surface (optional for the Beta)

**STATUS: PROPOSED**

| Field | Value |
|---|---|
| ID | ADR-0013 |
| Title | Local Model Advisory Surface: an approved-list, advisory-only, untrusted-output model demo |
| Status | PROPOSED |
| Drafted | 2026-10-31, by Local Claude, from RK's chat instruction and the updated second-opinion report of the same day |
| Authority class | USER AUTHORITY REQUIRED (G-05, G-13, G-14, G-15; G-03 for the approved list) |
| Inputs | MCA-002 (PROPOSED). ADR-0011, ADR-0012 (PROPOSED). ADR-0001 D3, D6. ADR-0005 (provenance). ADR-0006. ADR-0010 D5 (relayed results are untrusted). Master Context sections 26, 27. Beta plan Amendment 1 |
| Depends on | MCA-002, ADR-0011 accepted. **Optional: the Beta is complete without it, and it must never block the core Beta** |
| Amends | Nothing |

## Acceptance record

Not accepted. Acceptance is RK's merge of a pull request that sets STATUS to ACCEPTED (ADR-0001 D6).

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
