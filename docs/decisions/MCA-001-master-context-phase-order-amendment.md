# MCA-001 — Master Context Phase-Order Amendment

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| Amendment ID | MCA-001 |
| Title | Master Context Phase-Order Amendment |
| Status | ACCEPTED |
| Drafted | 2026-10-09, by Cloud Claude (change record) |
| Authority class | USER AUTHORITY REQUIRED (G-01, G-15) |
| Target document | `JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md`, version 0.1 (header: Status "Approved baseline", Date 2026-10-06) |
| Inputs | CP-0 Review — Final §5 and §5.1. Master Context text as committed on branch `docs/pre-phase-1-gate` (read 2026-10-09). |
| Related | ADR-0001 (D1, D4), ADR-0002 (D4, D6) |

**What MCA-001 is.** A change record. It is not a layer in the authority hierarchy. If RK accepts it, the result is a **new version of the Master Context** containing the amended text. The new version is the authority. This record stays as the history (ADR-0001 D1, D4).

**Until RK accepts MCA-001, the Master Context applies exactly as currently written.**

**Withdrawn items.** The three earlier proposed amendments (M1, M2, M3) are not revived. The CP-0 review finds each narrows authority the Master Context already allows. This is the only genuine contradiction identified.

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-11 |
| How the acceptance was given | A written instruction from the founder to Local Claude on 2026-10-11. Under ADR-0001 D6 that instruction is an input. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this document. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6: approval applies to the exact text accepted) |
| Resulting change | New Master Context version 0.1-r1 in docs/spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md, committed in the same pull request. Version 0.1 stays recoverable from Git history |
| Applied text | Section 4 of this record: the section 4 step order (4.1), the section 30 phases (4.2) and the header (4.3). The Master Context's Markdown list style is kept for the phase item lists. Item wording is unchanged |
| Not done | No Git tag was created for version 0.1. Section 9 of this record leaves the marking of the old version to RK |

---

## 1. Affected Master Context sections

| Section | Lines in committed file | Change |
|---|---|---|
| §4 Development Strategy: the progression block | 101–… | Reorder and add two steps |
| §30 Required Initial Phases: Phase 2 to Phase 7 | 1006–1114 | Renumber, insert two phases, regroup |
| Header: Version and Date | 1–12 | Version and date of the amended text |

Searched for other phase-number references. The only others are line 1334 ("5. Phase 1 change list", in §39) and line 2571 ("After Phase 0 and Phase 1, evaluate experimentally", in §40.12). Both refer to Phase 0 and Phase 1, whose meanings are unchanged. No other text refers to Phases 2–7 by number. (`VERIFIED` by search of the committed file.)

## 2. The contradiction

Master Context §30 ("Required Initial Phases") places the Research Engine (web research) as Phase 2 and Controlled Coding (command and test execution) as Phase 3. §4 places Research and Controlled Coding before Memory, Scheduling and Background Autonomy.

The control-plane-first sequence requires a deterministic control plane (Phase 1), then an interim manual worker bridge, then a local isolation boundary, **before** web research and code execution are automated.

Under the Master Context order, Phase 2 web research (untrusted content) and Phase 3 command execution would run before any isolation exists. The Master Context §14 prefers a controlled workspace, and §40.8 states that "a permission prompt is not a security boundary."

This amendment does not touch §39. §39 still requires inspection before implementation, and still requires the five outputs after inspection (architecture proposal, inventory, implementation plan, risk assessment, Phase 1 change list). CP-0 closure is the checkpoint that shows those are done. This is not a contradiction of §39.

## 3. Current / original text

### 3.1 §4 (committed text)

```text
Foundation
    ↓
Governance
    ↓
Project Registry
    ↓
Task Engine
    ↓
Research
    ↓
Controlled Coding
    ↓
Testing
    ↓
Verification
    ↓
Memory
    ↓
Scheduling
    ↓
Background Autonomy
    ↓
Advanced UI
```

### 3.2 §30 Phases 1–7 (committed text, condensed: each bullet list is shown on one line; the wording of every item is unchanged)

```text
### Phase 1 — Minimal Jarvis Core
Implement: Configuration. Project registry. Task model. Task persistence.
Basic planner. Capability registry. Audit logging. CLI.
No autonomous code modification yet.

### Phase 2 — Research Engine
Implement: Web research. Source recording. Research notes. Evidence handling.
Research task execution. Bounded retries.

### Phase 3 — Controlled Coding
Integrate Claude Code.
Implement: Sandbox/worktree creation. Task handoff. Command execution.
Test execution. Diff generation. Result collection.
Protected repository remains untouched.

### Phase 4 — Verification Integration
Integrate applicable: Universal Verification. Global Guardrail.
Project-specific guardrails. Codebase Memory MCP.
Use adapters. Do not merge implementations.

### Phase 5 — Autonomous R&D
Implement: Question → Research → Hypothesis → Experiment → Code → Test
→ Verify → Analyze → Report.
Add bounded background execution.

### Phase 6 — Scheduler
Add: Scheduled tasks. Recurring research. Background project work.
Pause/resume. Runtime limits.

### Phase 7 — Functional Dashboard
Add the basic UI. Do not build cinematic UI yet.
```

(Phase 0 is unchanged and is not reproduced.)

## 4. Proposed new text

### 4.1 §4 (proposed)

```text
Foundation
    ↓
Governance
    ↓
Project Registry
    ↓
Task Engine
    ↓
Manual Worker Bridge
    ↓
Local Isolation
    ↓
Controlled Coding
    ↓
Testing
    ↓
Verification
    ↓
Research
    ↓
Memory
    ↓
Scheduling
    ↓
Background Autonomy
    ↓
Advanced UI
```

The relative order of Testing, Verification, Research and Memory after Controlled Coding is my reading of the CP-0 review §5.1 ("research engine and autonomous R&D" in Phase 5; Memory unchanged relative to Verification). RK should confirm it. `USER AUTHORITY REQUIRED`.

### 4.2 §30 Phases 1–7 (proposed)

```text
### Phase 1 — Deterministic Control Plane
Implement: Configuration. Project registry. Task model. Task persistence.
Basic planner (deterministic). Capability registry and deterministic
evaluator. Audit logging. CLI.
No model call, no network, no subprocess, no worker execution.
No autonomous code modification.

### Phase 2 — Manual Worker Bridge
JARVIS produces a bounded task brief. RK runs an external worker manually
and relays results. JARVIS does not invoke the worker. Relayed results are
treated as untrusted input. Brief rules are defined by ADR.

### Phase 3 — Local Isolation
Establish and test an OS-level boundary between the governance zone,
protected projects and any worker. No automated worker execution until the
boundary is attested. Design is defined by ADR.

### Phase 4 — Controlled Coding and Verification Integration
(Master Context former Phase 3 and former Phase 4.)
Integrate Claude Code.
Implement: Sandbox/worktree creation. Task handoff. Command execution.
Test execution. Diff generation. Result collection.
Protected repository remains untouched.
Integrate applicable: Universal Verification. Global Guardrail.
Project-specific guardrails. Codebase Memory MCP.
Use adapters. Do not merge implementations.

### Phase 5 — Research Engine and Autonomous R&D
(Master Context former Phase 2 and former Phase 5, without background execution.)
Implement: Web research. Source recording. Research notes. Evidence handling.
Research task execution. Bounded retries.
Question → Research → Hypothesis → Experiment → Code → Test → Verify
→ Analyze → Report.

### Phase 6 — Scheduler and Background Autonomy
Add: Scheduled tasks. Recurring research. Background project work.
Bounded background execution. Pause/resume. Runtime limits.

### Phase 7 — Functional Dashboard
Add the basic UI. Do not build cinematic UI yet.
```

All bullets under former Phases 2–6 are preserved in the new phases. Only grouping and order change. The new Phase 2 and Phase 3 text is the only new content. It is descriptive. Details are defined by later ADRs, each under ADR-0001.

### 4.3 Header (proposed)

Version `0.1` → `0.1-r1` (proposed name, see §8). Date → the acceptance date. A line added to the header: `Amendments: MCA-001`.

## 5. Exact rationale

1. Web research (untrusted content) and command or test execution each need an isolation boundary before they are safe to automate. The Master Context §14 and §40.8 already say so. The §30 order puts both before any isolation phase.
2. The zero-spend constraint (CP-0 review §5.1) rules out paid workers now. A manual bridge gives usable worker output without JARVIS invoking a worker.
3. The deterministic control plane is the first deliverable because governance (§12, §13, §26) must exist before anything it governs.
4. No permission is created. Every phase still needs its own gate.

## 6. Security and architectural impact

- Positive: no web content and no code execution reaches JARVIS before an isolation boundary exists. Governance and audit exist first.
- Architectural: Research moves after Controlled Coding and Verification. Claude Code integration moves from Phase 3 to Phase 4. Until then, Claude Code (or any worker) is operated by RK, outside JARVIS. The Master Context §10's flow ("JARVIS → sandbox → Claude Code") is delayed, not changed.
- No change to L0–L5, to the forbidden actions, or to §26 security principles.

## 7. Compatibility impact

- **Unchanged:** §31 first acceptance test and its requirements; §32; §33 non-goals; §12 and §13; §37; §39; §40.12; every prohibited action.
- **Affected:** any document that uses Master Context phase numbers 2–7. The CP-0 review and Delivery Plan v2 already use the new order. The gate package `PRE_PHASE_1_GATE.md` maps stages to the old numbers and needs updating. ADR-0002 uses the new numbers (conditional on this MCA).
- **If rejected:** the Master Context order stands. Phase 2 (Research Engine, with web research) would have to run without an isolation boundary. The CP-0 review records that rejection therefore blocks Phase 2. Phase 1 is unaffected.
- **Not an amendment of §31:** v0.1 is still not complete until the first acceptance test passes. Phase 1's exit (CP-1) must never be called v0.1 complete.

## 8. User acceptance requirement

- `USER AUTHORITY REQUIRED`. Only RK can accept.
- Acceptance is effective only when recorded in the repository by RK (ADR-0001 D6): RK merges a pull request that sets this record's STATUS to ACCEPTED and commits the new Master Context version.
- Nothing from Phase 2 onward starts while this record is PROPOSED (CP-0 review R20).
- A Claude session cannot accept, merge or apply this record.

## 9. Resulting Master Context version change

| Item | Proposed |
|---|---|
| New version | `0.1-r1` (the name is a proposal; the CP-0 review says "for example v0.1-r1"). `UNKNOWN` whether RK prefers another scheme. `USER AUTHORITY REQUIRED`. |
| Path | Keep `docs/spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md` with the amended text. The previous version stays recoverable from Git history. `USER AUTHORITY REQUIRED`. |
| Marking the old version | A Git tag on the last commit of version `0.1` is the simplest way. A tag is a repository act and needs RK's decision. |
| Obsolete name | The obsolete `JARVIS_CORE_v0.1_MASTER_CONTEXT.md` must not be reused or referenced. |
| Unchanged text | Everything outside §4, §30 and the header. No other content is rewritten. |
| Record | This MCA stays as the change record. |
