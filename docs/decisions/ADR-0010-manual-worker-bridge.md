# ADR-0010 — Phase 2 Manual Worker Bridge

**STATUS: PROPOSED**

| Field | Value |
|---|---|
| ID | ADR-0010 |
| Title | Phase 2 Manual Worker Bridge: project reading, task briefs, relayed results, minimal memory |
| Status | PROPOSED. Not effective until RK merges the pull request that sets it ACCEPTED (ADR-0001 D6) |
| Drafted | 2026-10-30, by Local Claude, from RK's Beta instruction of the same day and the Beta release plan |
| Authority class | USER AUTHORITY REQUIRED (G-03, G-14, G-15, G-06, G-11) |
| Inputs | Master Context section 17, 18, 30 (Phase 2), 33. MCA-001. ADR-0001 D6, D9, G-03, G-14. ADR-0002 D4. ADR-0003 D2, D12. ADR-0004. ADR-0005 D8, D9, D11. ADR-0007 D5. `docs/plans/JARVIS_BETA_RELEASE_PLAN_2026-11-29.md`. `jarvis/` at the merge of PR #25 |
| Related | ADR-0002, ADR-0003, ADR-0005, ADR-0007 |
| Supplements | ADR-0002 D4 ("Manual worker brief", "Reading or parsing project content"), ADR-0003 D12 (the DEFER rows for `READ_PROJECT`, `READ_FILE`, `GENERATE_WORKER_BRIEF`), ADR-0007 D5 (the `memory/` layout, left `UNKNOWN`). No accepted ADR is amended |

**Labels:** `VERIFIED` · `UNKNOWN` · `PROPOSED` · `USER AUTHORITY REQUIRED` · `ENGINEERING` (an ordinary implementation choice inside this ADR).

## Governance-trigger classification (ADR-0001 D7)

- Matched triggers: **G-03** (capabilities enabled and added), **G-14** (worker-brief rules), **G-15** (Phase 2 scope), **G-06** (project content is read and written to the data root; nothing leaves the machine), **G-11** (new audit event names; the schema and chain are unchanged).
- Named engineering item: size caps and file layout inside D3 to D6.
- This block is a claim by the drafting session. RK's merge confirms or corrects it.

---

## 1. Context

1. Master Context section 30 (Phase 2, after MCA-001): "JARVIS produces a bounded task brief. RK runs an external worker manually and relays results. JARVIS does not invoke the worker. Relayed results are treated as untrusted input. Brief rules are defined by ADR." This is that ADR.
2. ADR-0002 D4 defers "reading or parsing project content" to Phase 2 onward, by ADR. ADR-0003 D12 holds `READ_PROJECT`, `READ_FILE` and `GENERATE_WORKER_BRIEF` at DEFER (`PHASE_NOT_ENABLED`).
3. ADR-0005 D9 already says a later phase may record project-file reads that the control plane mediates, as MEDIATED or REPORTED, never OBSERVED. ADR-0005 D8 already defines the provenance classes this ADR needs.
4. ADR-0007 D5 left the physical layout of `memory/` `UNKNOWN`.
5. Everything here stays inside the Phase 1 runtime limits: no network, no subprocess, no model, no worker invocation (X-13). Phase 3 isolation is not required because nothing here executes or fetches anything.

## 2. Decisions

### D1. Scope `PROPOSED`

Phase 2 is: bounded reading of project files, deterministic task briefs, intake of relayed results, and plain notes with a cold-start `resume`. It adds no execution surface. JARVIS never starts a worker, a command, a model or a connection. X-13 (static and runtime guard) continues to apply to every new module, and every new command is tested as a guarded child.

### D2. Capability changes (policy version 2) `PROPOSED` `USER AUTHORITY REQUIRED` (G-03)

| Capability | Change | Level | Allowed target classes | Verdict after |
|---|---|---|---|---|
| `READ_PROJECT` | enabled | L1 | `PROJECT_ID`, `PROJECT_PATH` | ALLOW inside contract scope, else per ADR-0003 |
| `READ_FILE` | enabled | L1 | `PROJECT_PATH` | ALLOW inside contract scope, else per ADR-0003 |
| `GENERATE_WORKER_BRIEF` | enabled | L2 | `PROJECT_ID` | ALLOW |
| `RECORD_RESULT` | **new** | L2 | `CONTROL_PLANE_RECORD` | ALLOW |
| `RECORD_NOTE` | **new** | L2 | `CONTROL_PLANE_RECORD` | ALLOW |

- The three enabled rows are narrowed from `ANY` to the classes listed. No other row, level, verdict or reason code changes. The always-DENY classes (governance zone, JARVIS self, data root, user-secret locations, unclassified) stay DENY for every capability (ADR-0003 D2, D9 step 7).
- No new target class and no new provenance class. G-11 is not asked to change classes.
- This ADR does not edit `policy/policy.toml`. The policy change is a separate pull request that RK merges (G-03), after this ADR is accepted. It raises `policy_version` to 2 (ADR-0003 D6).

### D3. Reading rules `PROPOSED` `ENGINEERING` for the numbers

1. Every read is a task action. It reaches the evaluator, which canonicalizes the path (X-09, X-16) and applies policy, contract scope, protected paths and the user-secret list. No command reads a project file by another route. A one-shot `file read` command, if built, creates an ordinary task.
2. A read returns at most **64 KiB** of one file. Longer files are truncated at a byte boundary that does not split a UTF-8 character, and the output states the original size and that it was truncated.
3. A file that is not valid UTF-8 text, or that contains a NUL byte, is refused with a named reason. Binary files are never returned.
4. A directory read lists at most **200** entries, names only, sorted, without following junctions or symlinks.
5. The audit record carries the canonical path, the byte count read and the SHA-256 of the bytes returned, in `files_read`, with provenance **MEDIATED** (ADR-0005 D9). Content is not copied into the audit chain.
6. Content that is returned to RK is printed. Content that goes into a brief is limited by D4.

### D4. Brief rules `PROPOSED` `USER AUTHORITY REQUIRED` (G-14)

1. **A brief grants no authority.** It is a request document. Its first lines say so. A worker, session or model that receives it holds no permission from it (G-14).
2. **Deterministic.** The same task record, contract and selected files produce a byte-identical brief. Generation reads no clock, no environment and no model.
3. **Contents, and only these:** brief ID; task ID and project ID; the objective text RK wrote; the contract scope roots, protected paths and forbidden operations; the list of files the task selected, each with its SHA-256 and size; excerpts of those files only if the task asked for them and the D3 cap holds; the standing rules for the worker (stay inside scope, do not touch protected paths, report every file modified, report what was not done); and the expected result format.
4. **Never in a brief:** anything from the governance zone other than the contract fields in item 3; data-root paths; user-secret locations; credentials; relayed results; notes; any text that came from a model or a worker. A brief is built from RK-authored task fields and control-plane records only. This keeps untrusted text from being carried forward into a new instruction.
5. **Bounded.** At most **192 KiB**. Over the cap: generation fails with a named reason; nothing is truncated silently.
6. **Stored and immutable.** Written to `<data_root>\briefs\<task_id>-<n>.txt`, temp-file-then-replace as reports are. A regenerated brief is a new file with a new number. The audit record carries the path, size and SHA-256.
7. **Generation is a plan step** of a task whose evaluation was ALLOW for `GENERATE_WORKER_BRIEF`. `task run` performs it.

### D5. Relayed results `PROPOSED` `USER AUTHORITY REQUIRED` (G-14)

1. RK supplies a result file to `result add <task_id> --file <path>`. The file is read as data by the control plane's own code.
2. **Untrusted.** The result is stored as received (UTF-8 text only, at most **256 KiB**; larger or non-text is refused), written to `<data_root>\results\<task_id>-<n>.txt`, with its SHA-256 and size in the audit record. Provenance: the fact that RK relayed it is MEDIATED; its claims are REPORTED (ADR-0005 D8). Neither is ever OBSERVED.
3. **Data only.** A result is never parsed for commands, task requests, paths or constraints. It is never an input to the planner, the evaluator, a constraint field, a brief or a note. A result cannot change task state, policy, contract, registry or revocations. Text inside it that reads as an instruction has no effect (X-03: no free text reaches the evaluator).
4. Recording a result does not change task state. A task whose plan finished stays `COMPLETED_UNVERIFIED`. `VERIFIED` stays unreachable (ADR-0002 D2, X-11). Reports show results under the label **UNTRUSTED, NOT VERIFIED**.
5. A result can be added to a task in any state except `CANCELLED`.

### D6. Minimal memory (the `memory/` layout) `PROPOSED` `USER AUTHORITY REQUIRED` (G-06)

1. **Files in the data root, not new store tables.** Layout, under `<data_root>\memory\`:
   - `projects\<project_id>\` and `tasks\<task_id>\` hold notes. `decisions\` holds notes RK marks as decisions. These are three of the four folders named in Master Context section 17; `research\` is created when research exists.
   - One note per file, named `<seq>.txt`, append-only. A note is never edited; a correction is a new note that names the earlier one.
2. **Each write is audited.** `RECORD_NOTE` writes the file (temp-then-replace) and appends a `NOTE_RECORDED` event carrying the path, size and SHA-256. `doctor` re-hashes the notes against the audit chain and reports any file that was changed, removed or added outside the chain. This extends tamper evidence to notes without changing the store.
3. **Provenance.** A note is RK's typed input: the control plane observed the input, not the event it describes, so the class is **MEDIATED** (ADR-0005 D8). The note header records the author kind `RK_TYPED` and the UTC time.
4. **Notes are data.** Never an input to the evaluator, planner, constraints, briefs or policy. Showing a note labels it as a note.
5. **`resume`** prints, read-only: open tasks by state, the latest notes per project, the audit tail and `audit verify` outcome, and any `doctor` failure. It reads only control-plane records and `memory\`. It never reads project files.
6. **Limit, stated.** Notes are plain text in the data root, outside git and cloud-synced folders (ADR-0005 D11). The audit chain holds only their hash and size, never their text. RK should not type credentials into a note. Whether to refuse note text that looks like a secret is `UNKNOWN` and is left to a later decision.

### D7. Audit events `PROPOSED` `USER AUTHORITY REQUIRED` (G-11)

- New event names: `FILE_READ`, `BRIEF_GENERATED`, `RESULT_RECORDED`, `NOTE_RECORDED`. They use the existing record fields (`files_read`, `detail`, provenance). **No schema change, no hash-chain change, no change to ADR-0005 D1 to D10.**
- G-11 asks about new event semantics; RK's acceptance of this ADR is that confirmation. If RK reads event names as part of the audit model, that is the question being put.

### D8. What does not change `PROPOSED`

The evaluator, the canonicalizer, the contract narrowing rule, the state machine and its transitions, the four Phase 1 ALLOW capabilities, the DEFER rows other than the three above, the DENY rows, the ruleset, CODEOWNERS, the governance zone and `revocations.toml`. No JARVIS command writes to the governance zone or modifies a project. Phase 3 isolation, worker execution, network, model calls and approval records remain deferred.

## 3. Alternatives considered

| Option | Why not |
|---|---|
| Memory as new SQLite tables | Needs a store schema version and migration, touches the audit model (G-11), and is the riskiest change on the schedule. Files plus audited hashes give the same tamper evidence with no store change. |
| Let a relayed result carry structured fields the planner can use | Opens the instruction path from untrusted text to action. Rejected until Phase 3 and a verifier exist. |
| Allow briefs to quote results and notes | Launders untrusted text into a new instruction. Rejected (D4 item 4). |
| Read project files outside the task flow for convenience | Creates a side door around the evaluator. Rejected (D3 item 1). |
| Wait for Phase 3 isolation first | Reading and briefing execute nothing and fetch nothing, so isolation is not needed for them (D1). Waiting would block the Beta for no safety gain. |

## 4. Consequences

- The Beta can read a project inside its contract scope, write a bounded brief, take relayed results back, and keep notes across sessions, with every step audited and none of it executing anything.
- Audit `files_read` becomes non-empty for project files, as ADR-0005 D9 anticipated, with MEDIATED provenance and the stated limit that a worker's own reads are not captured.
- A hash recorded for a note, brief or result detects later change of that file; it does not prevent it (same limit as ADR-0005 D10).
- Policy version 2 is a separate RK-gated pull request. Until it merges, the three capabilities stay DEFER and no code in this phase can be exercised end to end.

## 5. Tests required (acceptance of the implementation, not of this ADR)

Table-driven capability tests for the five rows; read denial for `..`, junction, protected path, user-secret location, other project's scope, over-size, binary, non-UTF-8; brief determinism and bounds; a result full of instruction-like text changes nothing; notes round trip across a restart; `doctor` detects an edited note; X-13 static and runtime guards pass for every new module and command; `VERIFIED` still unreachable.

## 6. Open items

| Item | Status |
|---|---|
| Size caps (64 KiB, 200 entries, 192 KiB, 256 KiB) | `ENGINEERING`, chosen for a single-user laptop. Raising them is a later ADR amendment. |
| Behaviour when a file is being written by a worker while it is read | `UNKNOWN`. Windows sharing rules to be observed in the tests. |
| Refusing secret-looking note text | `UNKNOWN`. |
| Backup of `memory\`, `briefs\`, `results\` | Part of the open backup item in ADR-0009. |
| Voice, UI or model access to any of this | Out of scope. Needs its own ADR. |
