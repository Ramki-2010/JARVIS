# ADR-0011 — Local Interaction Surfaces: Dashboard, Status Ring, Galaxy, Intent Layer

**STATUS: PROPOSED**

| Field | Value |
|---|---|
| ID | ADR-0011 |
| Title | Local Interaction Surfaces for the v0.1 Beta: localhost dashboard, status ring, read-only galaxy, shared interaction and intent layers |
| Status | PROPOSED |
| Drafted | 2026-10-31, by Local Claude, from RK's chat instruction of the same day |
| Authority class | USER AUTHORITY REQUIRED (G-05, G-06, G-15; G-11 for the optional interaction log) |
| Inputs | MCA-002 (PROPOSED). ADR-0001 D3, D6, D9. ADR-0002 D2. ADR-0003. ADR-0005. ADR-0006 sections 3.2, 6.1. ADR-0007. ADR-0010 D1, section 6. Master Context sections 23, 24, 26. Two uploaded second-opinion reports of 2026-10-31 (input only). Beta plan Amendment 1 |
| Depends on | MCA-002 accepted. **No part of this ADR is in force before that** (an ADR cannot widen the Master Context, ADR-0001 D3) |
| Related | ADR-0012 (voice), ADR-0013 (local model, optional) |
| Amends | Nothing. ADR-0006 governs the control plane, which does not change. This ADR adds surfaces outside it |

## Acceptance record

Not accepted. Acceptance is RK's merge of a pull request that sets STATUS to ACCEPTED (ADR-0001 D6). RK's chat approval of the direction on 2026-10-31 is an input, not the record.

**Labels:** `PROPOSED` · `USER AUTHORITY REQUIRED` · `ENGINEERING` (an ordinary implementation choice inside this ADR) · `UNKNOWN`.

## Governance-trigger classification (ADR-0001 D7)

- Matched: **G-05** (a localhost server is a new network surface, even though bound to loopback), **G-06** (what the UI exposes; optional interaction log), **G-15** (Beta scope, via MCA-002). **G-11** only for the optional interaction log (D8).
- Not matched: G-03 (no capability or policy change; Stage B writes use existing capabilities), G-14 (no worker or session authority is created).
- Named engineering items: layout of the `ui/` and `interaction/` packages, ring colours and animation, galaxy layout algorithm, port selection method, lexicon contents.
- This block is a claim by the drafting session. RK's merge confirms or corrects it.

---

## 1. Context

1. MCA-002 lets the v0.1 Beta carry a Beta dashboard, a status ring and a read-only galaxy. ADR-0010 section 6 says UI access needs its own ADR. This is that ADR.
2. ADR-0006 forbids network and subprocess in product code under `jarvis/`, enforced by a static scan and a runtime guard (X-13). A browser dashboard needs a listening socket.
3. The principle for the Beta is **strict authority, flexible interaction, controlled exposure**. Interfaces are presentation. The control plane stays the only authority.

## 2. Decisions

### D1. Layers `PROPOSED`

```text
UI (browser)   CLI   VOICE (ADR-0012)
        \       |       /
         Interaction layer      normalises input from every surface
                |
         Intent layer           maps input to one of 25 intent families (D6)
                |
         Command layer          maps a validated intent to one fixed CLI command
                |
         python -m jarvis       the control plane: policy, audit, state
```

Each interface only translates what the user did. No interface holds authority, duplicates a command or touches state directly. Presentation (D7) comes after the result, never before.

### D2. Process boundary `PROPOSED` `USER AUTHORITY REQUIRED` (G-05)

- `jarvis/` is unchanged. It never creates a subprocess and never opens a socket. ADR-0006 and X-13 remain true for it.
- New packages `interaction/` and `ui/` sit outside `jarvis/`. Process creation and sockets belong **only** to them (and to `voice/` under ADR-0012), never to `jarvis/`.
- **The UI process may invoke the CLI (`python -m jarvis ...`) as a child process. `jarvis/` itself never creates subprocesses. UI child calls are the only read/write command boundary into the control plane. No UI code imports or directly accesses control-plane internals, the database, or the filesystem beyond what the CLI prints.**
- One helper in `interaction/` starts the child. Required form:
  - **Absolute interpreter path.** The Python 3.14 executable is given by absolute path (taken from the launching interpreter's own `sys.executable`, checked to be 3.14 at start and refused otherwise). A bare `python` or `py` resolved through `PATH` is forbidden, so a changed `PATH` cannot redirect execution.
  - Fixed arguments `-I -m jarvis` followed by an argument list built from validated parameters, and an absolute `--config` path.
  - **Shell invocation is prohibited**: `shell=False`, never a command string, never `os.system` or similar.
  - Fixed working directory, a minimal fixed environment (nothing inherited that changes behaviour), a timeout and a bounded output size.
- No other process-creating call is permitted in `ui/` or `interaction/`. A static test enforces this, as it does for `tests/` (ADR-0006 section 3.2): it fails on `shell=True`, on a bare interpreter name, and on any second process-creating call.
- The static guard is extended: `jarvis/` has no subprocess or network imports; `ui/` and `interaction/` import no network module other than the stdlib HTTP server in `ui/`; `voice/` has no network module at all.
- Every child call goes through the control plane, so policy evaluation and audit happen exactly as they do from the CLI.

### D3. Localhost server rules `PROPOSED` `USER AUTHORITY REQUIRED` (G-05)

1. Standard library `http.server` only. Bound to `127.0.0.1` only. A random free port chosen at launch. Never `0.0.0.0`, never a LAN address. **LAN access is excluded from the Beta.**
2. A per-launch random token (at least 128 bits). It is delivered to the page without putting it in a query string (for example a URL fragment read by the page script) and sent as a request header. Requests without it are refused.
3. **Exact Host and Origin.** `Host` must be exactly `127.0.0.1:<port>` or `localhost:<port>` (this launch's port); anything else is refused (DNS rebinding). `Origin`, where present or required, must be exactly `http://127.0.0.1:<port>` or `http://localhost:<port>`; every other value is rejected. **`Origin` is required on every Stage B mutation; a missing `Origin` is refused.** The per-launch token (item 2) stays independently mandatory: a correct `Origin` never substitutes for it.
4. No CORS headers. A strict Content-Security-Policy: same-origin only, no inline script except one hashed or nonced block, no remote fonts, images or scripts, no CDN.
5. No outbound calls of any kind from the server. No arbitrary URL fetching. No filesystem browsing. No endpoint returns a path outside what the CLI prints. No secret is ever read.
6. All output is HTML-escaped; control characters are neutralised, as the CLI display module does.
7. Request size and rate are bounded. The server holds no state of its own beyond the token.
8. **Stage A (first):** read-only routes only, each mapped to a read-only CLI command (`status`, `doctor`, `project list/show`, `task list/show`, `note list/show`, `result` metadata, `audit verify`, `resume`, `report`).
9. **Stage B (only after Stage A passes its security tests and RK says so):** POST routes for a whitelist of three existing commands: task create, note add, cancel. Each maps to an existing CLI command, is evaluated by policy and audited. No other write route exists. **Strict POST validation:** a fixed content type; a strict maximum body size, checked before parsing; an exact field whitelist per route, where unexpected, duplicate or missing fields are rejected (no lenient parsing, no default filling); values pass the same validation as CLI arguments. Tests: oversize body, unknown field, duplicate field, missing field, wrong content type, wrong or absent Origin, wrong Host, and missing token with an otherwise correct Origin must each be refused.
10. If this ADR is not accepted in time, the fallback is a static, read-only HTML file generated from CLI output and opened from disk, with no server (Beta plan BS-3).

### D4. Truthfulness invariants (ring and every display) `PROPOSED`

1. **Actual state versus presentation.** Animation may enhance a real state. It must never fabricate one.
2. Ring states are derived only from records and real signals:

| Ring state | Source of truth |
|---|---|
| IDLE | no task RUNNING; nothing in progress |
| RUNNING | a task in state RUNNING in the store |
| WAITING | a task BLOCKED or DEFERRED awaiting RK |
| COMPLETED | latest task COMPLETED_UNVERIFIED (never shown as verified) |
| BLOCKED / DEFERRED / CANCELLED | task state or policy verdict |
| ERROR | a command returned an error |
| AUDIT_FAULT | `audit verify` failed |
| LISTENING / SPEAKING | only from ADR-0012: the microphone is actually open, or audio is actually playing |
| INTERPRETING | only while the intent layer is actually working on a request |

3. Forbidden: fake network activity, fake model processing, fake task execution, fake connectivity, fake metrics, fake audit activity, a "thinking" state with nothing running.
4. The UI states LOADING, EMPTY, READY, RUNNING, SUCCESS, WARNING, BLOCKED, DEFERRED, CANCELLED, ERROR, AUDIT_FAULT come from real command results. Long commands must not freeze the page (the server returns while the child runs; the page observes state).
5. Anything shown for a future capability is labelled **PREVIEW**, **DEFERRED** or **BLOCKED** (the last two are real policy verdicts). A PREVIEW item is never counted as a record, task or activity.

### D5. Galaxy rules `PROPOSED`

1. Read-only. It displays records; selecting a node opens the same detail view as the list. Every action available in the galaxy is available through keyboard-reachable lists. The galaxy is never the only way to reach anything.
2. **Every LIVE node maps to real source data. Every displayed relationship maps to real data. PREVIEW, DEFERRED and BLOCKED nodes are labelled and never represent records.** Node count need not equal record count; one record may produce several visual elements and several records may form a cluster.
3. Presentation rules (active near the centre, completed receding, recent activity linking) are presentation only and change no state. Layout is deterministic given a seed so it can be tested.
4. Technology: HTML, CSS, JavaScript and 2D canvas with simple 3D projection. No third-party library. WebGL, Three.js or any vendored library needs a separate decision (supply chain, hash pinning). Performance is measured in a spike before a limit is stated; no number is assumed.
5. Accessibility: keyboard navigation, text status, labels. The page remains usable with the galaxy disabled.

### D6. Intent layer `PROPOSED`

1. 25 intent families (families, not phrases):
   Presence: `WAKE`, `PRESENCE`, `START_WORK`, `SESSION_END`. System: `SYSTEM_STATUS`, `SYSTEM_HEALTH`, `RUN_DOCTOR`, `EXPLAIN_STATUS`. Projects: `PROJECT_LIST`, `PROJECT_DETAILS`, `CURRENT_TASK`, `RECENT_ACTIVITY`. Tasks: `CREATE_TASK`, `TASK_DETAILS`, `STOP_TASK`, `CANCEL_TASK`, `RESUME_TASK`. Knowledge: `SHOW_NOTES`, `ADD_NOTE`, `READ_FILE`, `GENERATE_BRIEF`, `SHOW_RESULT`. Governance and utility: `AUDIT_STATUS`, `BACKUP_STATUS`, `HELP`.
2. Deterministic: a lexicon and rules, no model. Tolerates vocabulary variation, filler words and sentence restructuring within what the lexicon covers. Example utterances are **test inputs, not scripts**; no phrase is required.
3. **Doubt becomes a question, never a guess.** Low confidence or two close candidates produces a clarification ("Which task do you mean?"). Dangerous or irreversible intents need an explicit confirmation turn. Confirmation is not authorization: policy still decides.
4. The intent layer returns an intent and parameters, nothing else. Parameters pass the same validation as CLI arguments. It never builds a shell string.
5. Presence intents (`WAKE`, `PRESENCE`, `START_WORK`, `SESSION_END`) have a defined, harmless meaning: `WAKE`/`PRESENCE` greet and run the `resume` summary; `START_WORK` shows open tasks and asks which to work on; `SESSION_END` shows what is open and records nothing new unless asked. None changes state or grants anything.
6. **Task semantics** (corrected by RK's review):
   - `CURRENT_TASK`: read-only; the open or last-touched task.
   - `CANCEL_TASK`: terminates a not-finished task (state CANCELLED), final and audited. It is the existing `cancel` command.
   - `STOP_TASK`: a **request to interrupt**, distinct from cancel. The Beta has no background execution, so the answer is "Nothing is currently running." and **no state changes**. It never cancels automatically.
   - `RESUME_TASK`: a **full re-evaluation**, never a blind restart: current state, then policy, then task conditions, then the valid outcome (continue / remain blocked / defer / reopen / no-op). It applies to every state. Re-evaluation does not guarantee reopening. Today (`jarvis/states.py`, verified): PENDING, BLOCKED and DEFERRED have evaluated edges, so continue / remain blocked / defer work. RUNNING has no edge to BLOCKED or DEFERRED (ADR-0002 D2 extension is PROPOSED), so resume reports only. COMPLETED_UNVERIFIED, FAILED and CANCELLED have no outgoing edge, so **reopen does not exist**; for them resume reports the re-evaluation and does nothing. A real reopen needs a state-machine amendment: `UNKNOWN`, **RK decision D-12**.
7. **No address-term configuration exists.** Lines like "Daddy is here" are voice test utterances only, kept in the test corpus. They carry no authority, no identity and no persona setting.
8. Acceptance: a measurement harness first (development set, held-out set, negative, ambiguous and similar-intent examples, filler words, restructuring; at least five variants per family). Report intent accuracy, false-intent rate, clarification rate, latency and governance violations as measured. No target is set in advance.
9. Cross-surface equivalence: the same request via CLI, UI and voice resolves to the same intent and command.

### D7. Persona rendering `PROPOSED`

A separate module turns a result into wording ("The task is complete, sir."). It cannot change the result, authorization, task state or capabilities. Wit is off for approvals, risk, credentials and records. It reads only the result object it is handed. Original lines only.

### D8. Interaction record (optional) `PROPOSED` `USER AUTHORITY REQUIRED` (G-06, G-11)

If enabled, a plain log under `D:\JARVIS\data\interaction\` (ADR-0007) records surface, time, normalised text, resolved intent, confidence, clarification, confirmation and the command run. It is not part of the hash chain, not authoritative and never fed to planning. Commands it triggers are audited by the control plane as usual. Default: off until RK decides. No audio is stored here.

### D9. What does not change `PROPOSED`

The evaluator, canonicalizer, policy version 2, state machine, audit model, ADR-0006 stdlib-only rule for `jarvis/`, X-13, the ruleset, CODEOWNERS and the governance zone. No UI or intent code writes to the governance zone or modifies a project.

## 3. Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Put the HTTP server inside `jarvis/` | Breaks ADR-0006 and X-13 for the control plane |
| UI imports `jarvis` modules in-process | Gives a network process direct access to state; the CLI child keeps one controlled boundary |
| Static HTML only | Safe, but no live state and no Stage B; kept as the fallback |
| Third-party UI framework or Three.js | Supply chain and a separate decision; not needed for a first galaxy |
| LAN access | New exposure, own decision later |
| An ML intent model | Adds a model dependency; deterministic first, a model may only propose later (ADR-0013) |

## 4. Evidence

`VERIFIED`: ADR-0006 forbids `socket`, `http`, `subprocess` in `jarvis/` (`tests/test_static_guard.py`). `jarvis/states.py` transitions as in D6.6. 415 tests pass on `main` a5e7113. `UNKNOWN`: galaxy frame rate at a few hundred or thousand nodes; lexicon accuracy; whether the stdlib server meets the CSP and token design without friction. Each is measured in a spike before it is claimed.

## 5. Security impact

New loopback-only network surface. Risks and answers: DNS rebinding (Host check), other local pages calling the server (token, Origin, no CORS), XSS (escape, CSP), port clash (random port), local malware reading the token (out of scope; same trust as the user account), accidental LAN exposure (bound to loopback, tested). No new authority.

## 6. Complexity impact

Medium. Three small packages (`interaction/`, `ui/`, the pure intent code) and one page. No dependency.

## 7. Reversibility

High. Delete the packages; the control plane is untouched.

## 8. Authority class

`USER AUTHORITY REQUIRED`. Acceptance is RK's merge.

## 9. Consequences

The Beta gains a dashboard, a ring and a galaxy behind a cut line. B-13 must list the limits. The static guard gets new rules. ADR-0006 stays true for `jarvis/` and is not amended.

## 10. Open items

| # | Item |
|---|---|
| 1 | D-12: may `RESUME_TASK` reopen a terminal task (needs a new state edge). |
| 2 | D8: enable the interaction log or not. |
| 3 | Stage B go-ahead after Stage A passes. |
| 4 | Whether WebGL or a vendored library is ever allowed (separate decision). |
| 5 | LAN client access: later, own ADR. |
