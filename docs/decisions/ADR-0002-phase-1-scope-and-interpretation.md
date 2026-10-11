# ADR-0002 — Phase 1 Scope and Interpretation

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0002 |
| Title | Phase 1 Scope and Interpretation |
| Status | ACCEPTED |
| Drafted | 2026-10-09, by Cloud Claude |
| Authority class | USER AUTHORITY REQUIRED (G-03, G-15, G-16) |
| Inputs | Master Context §4, §7, §12, §13, §18, §19, §22, §30, §31, §32, §37, §39. CP-0 Review — Final (F1, F5, F6, F7, F10, §3.9, §6, §10.3). Local CP-0 Fact Report 2026-10-09. |
| Related | ADR-0001, ADR-0003, ADR-0004, ADR-0005, MCA-001 (all ACCEPTED) |

**Labels:** `VERIFIED` · `UNKNOWN` · `MASTER CONTEXT POLICY` · `PROPOSED` · `USER AUTHORITY REQUIRED` · `LOCAL FACT CHECK REQUIRED` · `ENGINEERING AFTER CP-0`. `VERIFIED (LF-n)` = Local CP-0 Fact Report.

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-11 |
| How the acceptance was given | A written instruction from the founder to Local Claude on 2026-10-11. Under ADR-0001 D6 that instruction is an input. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this document. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6: approval applies to the exact text accepted) |
| Accepted text includes | The test process structure and the X-13 guard (D5); the CONSTRAINT_WIDENS behavior (D3): a task constraint that adds a capability or widens authority is rejected, the evaluator returns DENY with reason CONSTRAINT_WIDENS, the task becomes BLOCKED, and evaluation never widens authority |
| Depends on | MCA-001 for the phase numbers (D6) |

---

## 1. Context

1. `MASTER CONTEXT POLICY` §30 Phase 1 is "Minimal Jarvis Core": configuration, project registry, task model, task persistence, basic planner, capability registry, audit logging, CLI. "No autonomous code modification yet."
2. `MASTER CONTEXT POLICY` §7: a task survives restart. §18: audit fields. §19: missing verification is never invented. §37: definition of done.
3. `VERIFIED (LF-1)` The build session's permission mode is `auto`. `VERIFIED (LF-12)` An environment variable named `CLAUDE_CODE_MESSAGING_TOKEN` exists in the build session (name only; value not read).
4. `VERIFIED (LF-6)` Installed Python is 3.10.11. `VERIFIED (LF-8)` `tomllib` does not import. `VERIFIED (LF-7)` Bundled SQLite is 3.40.1. `UNKNOWN` The Python version that ADR-0006 will require.
5. `VERIFIED (LF-2)` The workspace path is `D:\J.A.R.V.I.S AI Assistant` (27 characters, two spaces, five dots). `VERIFIED (LF-9)` NTFS. `VERIFIED (LF-11)` Long paths enabled. `UNKNOWN (LF-10)` 8.3 short-name generation.
6. The CP-0 review withdraws three earlier "amendments" (M1–M3). The only genuine Master Context contradiction is phase order (MCA-001). An ADR cannot change the Master Context (ADR-0001 D3).

## 2. Decision

### D1. Phase 1 is a deterministic control plane `PROPOSED`

Phase 1 delivers the Master Context §30 Phase 1 list, narrowed as below. It makes no model call, no network call, no subprocess call and executes no worker. It reads no project file content. It parses no project-resident file.

**In scope:**

| # | Component | Minimal content |
|---|---|---|
| 1 | Configuration | Typed, loaded from configuration files in the governance zone (ADR-0004 D2) by the loader (ADR-0003 D1). Rejects secret-like keys. Never reads environment variable values (test C3). |
| 2 | Project registry | Records carrying the §6.2 fields. Locations may be unresolved. Registry ID plus canonical root path (ADR-0004). |
| 3 | Contract schema and loader | Validation only. Contracts are JARVIS-side (ADR-0004). |
| 4 | Task model and persistence | The §7 fields. Single SQLite store shared with the audit chain (ADR-0005). Survives restart. |
| 5 | Planner stub | Deterministic. Produces plan structure with no model call. |
| 6 | Capability registry, loader, canonicalizer and pure evaluator | ADR-0003 D1. Default deny. The evaluator performs no I/O. |
| 7 | Audit | Every §18 field is in the schema from the start, empty where unused (CP-0 review §5 row 6). ADR-0005. |
| 8 | Verification field | A field in the task and audit schemas. Defaults to NOT_VERIFIED. Carries provenance. No verifier integration. |
| 9 | CLI | `task`, `status`, `report`, `cancel`, `audit verify`. |
| 10 | Tests | D5 below. |

**Phase 1 ALLOW set** (exactly; ADR-0003 holds the full matrix): `CREATE_TASK`, `CREATE_REPORT`, `READ_REGISTRY`, `READ_CONTROL_PLANE_CONFIG`.

**Control-plane operations are not capabilities.** Task state transitions, audit appends, `cancel`, `audit verify` and reads of the control plane's own store are internal operations governed by the state machine (D2) and ADR-0005. The evaluator governs task actions on targets. This is stated so nothing is read as an unlisted capability.

### D2. Task states `PROPOSED`

| State | Meaning in Phase 1 |
|---|---|
| `PENDING` | Created. Not yet evaluated. |
| `RUNNING` | In-process, deterministic actions only, such as writing a report. No worker, subprocess, network or model. |
| `BLOCKED` | Evaluation produced at least one DENY. |
| `DEFERRED` | No DENY. At least one DEFER. The capability is recognized, but the system lacks the authority or isolation mechanism needed (ADR-0003). It does not mean allowed later. |
| `COMPLETED_UNVERIFIED` | Actions finished. No independent verification occurred. |
| `FAILED` | An internal or execution error. A policy decision is never recorded as FAILED. |
| `CANCELLED` | RK cancelled through `jarvis cancel`. |
| `VERIFIED` | **Reserved. Unreachable in Phase 1.** |

Transitions:

| From | To | Condition |
|---|---|---|
| (new) | `PENDING` | Task created |
| `PENDING` | `RUNNING` | Evaluation: every requested capability ALLOW |
| `PENDING` | `BLOCKED` | Any DENY |
| `PENDING` | `DEFERRED` | No DENY, any DEFER |
| `DEFERRED`, `BLOCKED` | `RUNNING`, `BLOCKED`, `DEFERRED` | Always re-evaluated on leaving. The policy version may have changed (test C5). |
| `RUNNING` | `COMPLETED_UNVERIFIED` | Actions finished |
| `RUNNING` | `FAILED` | Error |
| `PENDING`, `RUNNING`, `DEFERRED`, `BLOCKED` | `CANCELLED` | `jarvis cancel` |

- Every other transition is rejected, leaves state unchanged, and writes an audit event.
- Any attempt to reach `VERIFIED` is rejected the same way (test C6).
- Evaluation happens on the PENDING → RUNNING transition, for every requested capability.
- While RUNNING, before each side-effecting step the control plane compares the current policy version with the version used for the last evaluation. If they differ, it re-evaluates and may move the task to BLOCKED or DEFERRED. `PROPOSED` (extension of C5, to be confirmed by RK).
- **Cancel is not stop.** `CANCELLED` is a state change. Terminating execution ("stop") stays deferred because nothing executes (CP-0 review F10).
- Terminal states: `COMPLETED_UNVERIFIED`, `FAILED`, `CANCELLED`.

### D3. Task constraints narrow, never widen `PROPOSED`

- Constraints are supplied by RK in the task text or CLI arguments. They are never taken from model output. Only structured constraint fields reach the evaluator as `task_constraints` (ADR-0003 D1). The evaluator never reads free text.
- Effective authority = policy ∩ contract ∩ constraints.
- A constraint that adds a capability or widens a scope is rejected: the evaluator returns DENY with reason `CONSTRAINT_WIDENS` (ADR-0003 D9 step 10), and the task is BLOCKED (ADR-0003 D10). It never widens the evaluation result (test C7).
- Any `risk` or `level` value supplied with a task is ignored and overwritten by the evaluator's derived value (ADR-0003).

### D4. Deferrals `PROPOSED`

Deferred stays deferred until its own ADR and gate. DEFER is not a promise of later permission.

| Deferred | Target (per MCA-001 numbering) |
|---|---|
| Any model call | Phase 5 research / Phase 2 bridge, by ADR |
| Network access, web research | Phase 5, after Phase 3 isolation |
| Subprocess, test or experiment execution | Phase 4, after Phase 3 isolation |
| Worker execution; sandbox or clone creation | Phase 4 |
| Manual worker brief (RK relays to a worker) | Phase 2 (rule in CP-0 review F5, pending RK) |
| Approval mechanism for L4 actions | Phase 3 |
| Verification integrations (UV, Global Guardrail, Swarag Guardrail, Codebase Memory MCP) | Phase 4 |
| `pause`, `resume`, `stop` | Phase 6 |
| Scheduler and background execution | Phase 6 |
| Dashboard | Phase 7 |
| Reading or parsing project content | Phase 2 onward, by ADR |

### D5. Measurable Phase 1 exit criteria `PROPOSED`

Phase 1 is done only when every row passes and the evidence is reviewed at CP-1. A row that is not run is NOT VERIFIED, not passed.

| ID | Criterion | Pass rule |
|---|---|---|
| X-01 | Capability table | A table-driven test covers every capability in Master Context §13 (12 initial, 11 restricted) plus the Phase 1 additions in ADR-0003. Verdict and risk match the ADR-0003 matrix. |
| X-02 | Default deny | An unknown capability, unknown project, unknown target class or unresolvable path returns DENY with the named reason code. |
| X-03 | No free text | The evaluator's input type contains no free-text field. A golden-file determinism test: same inputs, same output, byte-identical. Covers the evaluator (ADR-0003 D1). |
| X-04 | Audit chain | `audit verify` detects an altered, deleted, reordered or truncated record. |
| X-05 (C1) | Two processes write at once | The harness starts two `python -m jarvis` children at the same time, each under the runtime guard (X-13b). The chain stays linear. No two records share a predecessor. |
| X-06 (C2) | Crash at either side of a state-and-audit commit | A child-side test hook ends the child at a chosen SQLite statement boundary (see "Test process structure" below). A later `python -m jarvis` run recovers. Recovery is identical on every run and is logged. |
| X-07 | Restart | A task survives process restart with the same state. |
| X-08 (C3) | A secret-looking environment variable is set | Loaded configuration is byte-identical with and without it. |
| X-09 (C4) | Raw input with a trailing dot or space, a different drive, a reserved device name, an alternate data stream, a UNC path, or a relative path | DENY before any normalising call. Covers the canonicalizer (ADR-0003 D3). |
| X-10 (C5) | Policy version changes while a task is DEFERRED | Leaving DEFERRED re-evaluates under the new version. |
| X-11 (C6) | Any attempt to set VERIFIED | Rejected, state unchanged, audit event written. |
| X-12 (C7) | Constraints try to add a capability or widen a scope | Evaluator output is identical or narrower, never wider. |
| X-13 | No network, no subprocess, no model in product code | (a) Static guard: a scan of every module under `jarvis/` finds no import or call from the ADR-0006 §3.2 forbidden list and no import outside the standard library. (b) Runtime guard: every `python -m jarvis` child process in the suite runs under a test-only audit hook that fails the test on a socket, process-creation, native-code or non-standard-library import event. The harness parent is outside the guard and starts only `python -m jarvis` (see "Test process structure" below). |
| X-14 | Zero third-party installs | The dependency manifest is empty. Standard library only. Tests use `unittest`. (Needs Python adequate for ADR-0006; see Open items.) |
| X-15 | Schema completeness | Every §18 audit field exists in the schema. |
| X-16 | Path canonicalisation | Paths with `..`, junctions, symlinks, 8.3 names, case differences, and non-ASCII characters in scope roots resolve or DENY exactly as ADR-0003 states. Covers the canonicalizer (ADR-0003 D3). |

**Test process structure.** `PROPOSED` `ENGINEERING AFTER CP-0`. X-05 and X-06 need child processes. X-13 forbids process creation in product code. Both hold under this structure:

- **Two separate trees.** Product code is under `jarvis/`. Test code is under `tests/`. No test code, test hook or test-only branch is added to `jarvis/`.
- **Static guard (X-13a).** A scan of the parsed syntax of every module under `jarvis/` against the ADR-0006 §3.2 forbidden list. It runs in-process under `unittest` and needs no hook.
- **Runtime guard (X-13b).** A test-only audit hook that exists only inside each child process the harness starts as `python -m jarvis`. It is installed by a startup module under `tests/`, put on that child's module search path by the harness. In the child it fails on audit events for sockets, process creation (`subprocess`, `os.system`, `os.exec*`, `os.spawn*`, `os.popen`), native code (`ctypes`) and imports outside the standard library. The hook is a detection mechanism, not an isolation boundary (ADR-0006 §6.1).
- **Harness.** The parent test process starts children through one helper that runs `python -m jarvis` with the given arguments. It starts nothing else. A static check over `tests/` fails if any other process-creating call appears there. The harness is outside the product-code guard.
- **Crash injection (X-06).** A child-side test hook ends the child immediately (no cleanup) at a chosen SQLite statement boundary, for example before or after the `COMMIT` of a state-and-audit transaction. Product code contains no crash code. VERIFIED locally on Python 3.10.11: the built-in audit events cover SQLite only at `connect` and `connect/handle`, not at statement execution. The hook therefore has to wrap the connection that product code opens, for example through a test-only connection factory or trace callback installed before product code runs. Whether that works end to end is `UNKNOWN` until X-06 first runs.
- **What this does not weaken.** Product code may still not import or call network, process, native-code or model facilities (X-13a). Every `python -m jarvis` run in the suite, including every CLI subcommand that X-05 to X-08 exercise, runs under the runtime guard (X-13b). Residual: product code exercised only by in-process unit tests, with no CLI run, is covered by the static guard and not by the runtime guard.

**Verification statement.** `MASTER CONTEXT POLICY` §19 requires independent verification. None is available in Phase 1: Universal Verification and the guardrails are not integrated and are `UNKNOWN` (not found, Phase 0 snapshot). Phase 1 results are therefore recorded NOT VERIFIED by any independent verifier. The independent checks are RK's review at CP-1 and the Cloud review of the evidence. No Phase 1 task can reach VERIFIED.

### D6. Phase-order interpretation requires MCA-001 `PROPOSED` `USER AUTHORITY REQUIRED`

- The phase numbers in D4 follow MCA-001. This ADR does not change the Master Context phase order and cannot (ADR-0001 D3).
- Phase 1's content here is Master Context §30 Phase 1 narrowed. It is valid whether or not MCA-001 is accepted.
- If MCA-001 is rejected: the Master Context order stands. Phase 2 (Research Engine, with web research) would have to run without an isolation boundary. CP-0 review §5.1 records that rejection therefore blocks Phase 2. Phase 1 is unaffected.
- Nothing from Phase 2 onward starts while MCA-001 is PROPOSED (risk R20).

## 3. Alternatives considered

| Alternative | Rejected because |
|---|---|
| Keep §30 order, run research next | Needs isolation first. Master Context §14 and §40.8 say a permission prompt is not a sandbox. |
| Add a standalone verification model in Phase 1 | Premature (Phase 4). A field with provenance is enough. |
| Include an approval engine in Phase 1 | Approval records are forgeable by any process running as RK before isolation. Nothing in Phase 1 needs approval. |
| Use `pytest` | Adds an install. `unittest` suffices (review F7). |

## 4. Evidence

- Master Context §30 lines 1006–1114 and §39 (quoted in MCA-001).
- `VERIFIED (LF-1, 2, 6, 7, 8, 9, 11, 12)`. `UNKNOWN (LF-10)`.
- CP-0 Review — Final: F1, F10, §3.9, §6.2, §10.3.

## 5. Security impact

- Positive: no code path in Phase 1 reaches a model, the network or a subprocess, and test X-13 checks it: a static scan of `jarvis/`, plus a runtime guard in every `python -m jarvis` test child. Code exercised only by in-process unit tests is covered by the static scan alone.
- Residual: Phase 1 code is written by a session running as RK with mode `auto`. Nothing in Phase 1 isolates the control plane from that session. Phase 1 makes no OS-level security claim.
- The CLI cannot tell RK from a builder session running under the same account. The recorded actor is the OS user, not a verified human (ADR-0005 provenance).

## 6. Complexity impact

Low to medium. One SQLite store, one evaluator, one CLI. No dependencies if the Python version allows.

## 7. Reversibility

High. Phase 1 adds no execution. Scope changes need a superseding ADR (G-15).

## 8. Authority class

USER AUTHORITY REQUIRED. Triggers G-03, G-15, G-16.

## 9. Consequences

- Delivery Plan v2.1 and `PRE_PHASE_1_GATE` need updating to match (they are evidence documents).
- X-01 to X-16 become the measurable CP-1 evidence list.
- A Python version decision (ADR-0006, G-13) gates X-14.

## 10. Open items

| Item | Label |
|---|---|
| Python version needed. Installed 3.10.11 lacks `tomllib` (3.11+). `os.path.isjunction` needs 3.12. `os.path.isreserved` needs 3.13. Policy format and checks must not assume them unless ADR-0006 sets a version. | `UNKNOWN` (ADR-0006), `USER AUTHORITY REQUIRED` for any install (G-13) |
| Whether `permissionMode: "auto"` is acceptable while Phase 1 is built | `USER AUTHORITY REQUIRED` (G-07) |
| Whether unlocated ecosystem projects (Phase 0 snapshot) satisfy Master Context §39 ("repositories are understood") for starting Phase 1. Phase 1 reads none of them. | `USER AUTHORITY REQUIRED` at CP-0 closure |
| RUNNING-state policy re-check (D2) | `PROPOSED`, RK to confirm |
| The Phase 1 additions to the §13 capability names (ADR-0003) | `USER AUTHORITY REQUIRED` (G-03) |
