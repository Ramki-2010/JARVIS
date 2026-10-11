# ADR-0003 — Capability Evaluation Model

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0003 |
| Title | Capability Evaluation Model |
| Status | ACCEPTED |
| Drafted | 2026-10-09, by Cloud Claude |
| Authority class | USER AUTHORITY REQUIRED (G-03, G-05, G-16). Items E-2, E-3, E-8 are `ENGINEERING AFTER CP-0` once this ADR is accepted. |
| Inputs | Master Context §12, §13, §14, §26, §33, §40.8. CP-0 Review — Final (§4.1, F5, F6, §6.2). Local CP-0 Fact Report 2026-10-09. |
| Related | ADR-0001, ADR-0002, ADR-0004, ADR-0005, MCA-001 |

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
| Accepted text includes | The loader, canonicalizer and pure evaluator split (D1); the target class CONTROL_PLANE_RECORD (D2); the reason code TARGET_CLASS_NOT_ALLOWED and the allowed-target-class column (D12); the added capability names marked with a dagger (section 10) |

---

## 1. Context

1. `MASTER CONTEXT POLICY` §13: every tool action passes through a capability layer, and permissions are enforced technically, not by prompts. §12 defines L0–L5. §26: external input and tool output are untrusted.
2. `MASTER CONTEXT POLICY` §13 lists 12 initial and 11 restricted capabilities. It does not map capabilities to levels. §12 says L2 is "normally" automatic and L3 is automatic "within explicit boundaries" without defining either.
3. `MASTER CONTEXT POLICY` §14 prefers a worktree or sandbox. §40.8: "A permission prompt is not a security boundary." No isolation exists yet.
4. `VERIFIED (LF-9, 11)` NTFS; long paths enabled. `UNKNOWN (LF-10)` 8.3 short-name generation. `VERIFIED (LF-6)` Python 3.10.11 (`os.path.realpath(strict=True)` exists; `isjunction` and `isreserved` do not). `VERIFIED (LF-4)` `core.autocrlf=true`, so repository text files check out with CRLF on this machine.
5. `VERIFIED (LF-12)` A secret-looking variable name exists in the build session's environment. The evaluator must never read the environment.

## 2. Decision

### D1. The evaluation function and its three stages `PROPOSED`

Evaluation is split into three stages. Only the first two perform I/O. The evaluator performs none.

| Stage | Component | I/O | Produces |
|---|---|---|---|
| 1 | Loader | Yes. Reads the policy, contract and revocation files, the project registry and the audit store. Reads the clock. Computes SHA-256 hashes (D4) | `PolicySnapshot` or `PolicyFailure(reason)`; `RevocationSnapshot` or `RevocationFailure(reason)`; `EffectiveContract` or `ContractFailure(reason)`; `now_utc`; `last_recorded_utc` |
| 2 | Canonicalizer (D3) | Yes. Raw-input checks, strict path resolution, classification | `CanonicalTarget` or `TargetFailure(reason)` |
| 3 | Evaluator | **None** | `(risk_level, verdict, reason)` |

```
evaluate(capability,
         target,             # CanonicalTarget | TargetFailure
         contract,           # EffectiveContract | ContractFailure
         policy,             # PolicySnapshot | PolicyFailure
         revocations,        # RevocationSnapshot | RevocationFailure
         task_constraints,   # structured, supplied by RK (ADR-0002 D3)
         now_utc,
         last_recorded_utc)
    → (risk_level, verdict, reason)
```

- `risk_level` ∈ {L0, L1, L2, L3, L4, L5}, ordered L0 < … < L5.
- `verdict` ∈ {ALLOW, DENY, DEFER}.
- `reason` is one code from the closed list in D9 plus structured parameters. It is never free text.
- **Failure values.** A `*Failure(reason)` input carries a reason code from the closed list in D9. The evaluator does not retry or repair it. It returns DENY with that code at that input's position in the D9 order.
- **Snapshots.** `PolicySnapshot` carries the policy version, its SHA-256 and the capability matrix (D12). `RevocationSnapshot` carries the revoked capabilities, projects and contract hashes, read fresh by the loader for this evaluation. `EffectiveContract` carries `schema_version`, `project_id`, optional `valid_until` and its SHA-256, after narrowing (ADR-0001 R1.4). `task_constraints` has structured fields only: no free text.
- **Recording.** The caller records `policy_version`, `policy_sha256` and `contract_sha256` with the decision (D4). They come from the input snapshots.
- `now_utc` and `last_recorded_utc` are explicit arguments, injectable in tests. They are the only time inputs and are used only for expiry and the clock-skew check (D7). Both are part of the recorded inputs. Expiry and clock skew need time. Passing it explicitly keeps the function pure. See Open items.
- **The evaluator is a pure function.** It reads no environment variables, no files, no network and no clock, and performs no other I/O. Its type signature contains no free-text field.
- Same inputs give byte-identical output (golden-file test, X-03).

**Verdict meanings:**

- **ALLOW:** the action may proceed.
- **DENY:** the action must not happen. It is outside authority.
- **DEFER:** the capability is recognized, but the current system lacks the authority or isolation mechanism required to execute it safely. DEFER does **not** mean allowed later. A later ALLOW needs a policy change, which is G-03.

### D2. Target classes `PROPOSED`

| Class | Meaning | Rule |
|---|---|---|
| `PROJECT_ID` | A registered project by ID | Must exist in the registry |
| `PROJECT_PATH` | A path inside a registered project root | Subject to contract scope |
| `CONTROL_PLANE_RECORD` | A task, report, registry or configuration record, by type and ID. Never a path | The ID is chosen by the control plane. The four Phase 1 ALLOW capabilities take this class only (D12) |
| `ARTIFACT` | A patch, commit or file, bound by SHA-256 | Hash required (D4) |
| `COMMAND` | A command line | Hash required (D4). Deferred. |
| `URL` | A web resource | Deferred |
| `GOVERNANCE_ZONE` | Contracts, registry, revocation list, spend policy (ADR-0004) | **Always DENY** |
| `JARVIS_SELF` | The JARVIS repository working tree and runtime code | **Always DENY** |
| `DATA_ROOT` | The SQLite store, exports, anchors (ADR-0004, ADR-0005) | **Always DENY** |
| `USER_SECRET_LOCATION` | `.ssh`, browser profiles, credential stores, tool credential directories under the user profile, and anything on the policy's secret-location list | **Always DENY** |
| `UNCLASSIFIED` | Cannot be classified | **DENY** (`UNKNOWN_TARGET_CLASS`) |

The "always DENY" rows apply to every capability invoked as a task action, when the target the action names is classified into one of those classes. The control plane's own reads and writes of its store are internal operations, not capabilities (ADR-0002 D1).

**How the Phase 1 ALLOW set stays consistent with these rows.** The four Phase 1 ALLOW capabilities name a `CONTROL_PLANE_RECORD` by type and ID. No task, constraint or input supplies a path for them. The control plane maps the ID to its own stores (the database in the data root, configuration and registry in the governance zone, ADR-0004 D2) by internal operations. A report is therefore created by naming a report record, never the `DATA_ROOT` class. A configuration read names a configuration record, never the `GOVERNANCE_ZONE` class. Any action that does name a path into those locations is classified into the always-DENY class and denied.

**Allowed target classes per capability** are in D12. A target whose class is not allowed for the capability is DENY (`TARGET_CLASS_NOT_ALLOWED`, D9 step 10).

### D3. Canonicalizer and canonical target `PROPOSED` `ENGINEERING AFTER CP-0` (E-3)

The canonicalizer is stage 2 of D1. It performs I/O (strict path resolution) and returns `CanonicalTarget` or `TargetFailure(reason)`. It is separate from the evaluator, which never touches the filesystem. The canonicalizer receives the roots it classifies against (governance zone, data root, JARVIS repository tree, registered project roots, secret-location patterns) from the loader. It assigns the D2 class. The evaluator applies the class rules (D9 steps 6 and 7). Tests X-09 and X-16 (ADR-0002) cover the canonicalizer. Test X-03 covers the evaluator.

Form: `<class>:<canonical-string>` and, where required, `#sha256:<64 hex>`. A `CONTROL_PLANE_RECORD` is `CONTROL_PLANE_RECORD:<type>/<id>`. It involves no path, and the canonicalizer only validates the shape of the type and ID.

**Path rules** (CP-0 review F6):

1. **Raw-input checks first, before any normalising call.** DENY (`TARGET_RAW_INVALID`) if the raw string is empty or relative; contains NUL; has a trailing dot or space in any component; contains a reserved device name (CON, PRN, AUX, NUL, COM1–9, LPT1–9, with or without extension); contains an alternate data stream marker (`:` beyond the drive letter); uses a device prefix (`\\?\`, `\\.\`); or is a UNC path. Python's `abspath` strips trailing dots and spaces on Windows, so these must be rejected on the raw input.
2. **Strict resolution.** Resolve with `os.path.realpath(strict=True)`. Any error, including access denied, is DENY (`TARGET_UNRESOLVABLE`). Without `strict`, `realpath` stops at the first component that fails and appends the rest unchanged, so the result may still contain links. Python's `realpath` resolves 8.3 names, symlinks and junctions on Windows. `isjunction` (3.12) and `isreserved` (3.13) are not available on the installed 3.10.11 (LF-6), so the reserved-name check is hand-written unless ADR-0006 sets a higher version.
3. **Path targets that do not exist yet** (for example a file a later phase may create inside a project): resolve the parent strictly and validate the leaf name by the raw rules in step 1.
4. **Containment.** Use `commonpath` after `normcase`. A `ValueError` (different drives) is DENY (`TARGET_CROSS_DRIVE`).
5. **Case.** `normcase` lowercases by Python's rules, which differ from NTFS case folding for some non-ASCII letters. Non-ASCII characters in scope roots get explicit tests (X-16).
6. **Do not assume 8.3 behaviour.** (LF-10 is `UNKNOWN`.) Resolution handles short names whether or not they exist.

### D4. Hashes where required `PROPOSED`

- `ARTIFACT` and `COMMAND` targets carry a SHA-256 of the exact artifact (patch bytes) or canonical command line. A decision made without the hash is DENY (`INPUT_INVALID`).
- Every decision record stores `contract_sha256`, `policy_sha256` and `policy_version`, so a decision can be replayed (review §4.1).
- Policy and contract hashes are computed over canonical bytes: UTF-8; every CRLF converted to LF; a lone CR rejected (`POLICY_FORMAT_INVALID`). This is needed because `core.autocrlf=true` (LF-4) turns repository text files into CRLF on this machine. A `.gitattributes` rule for policy files is an engineering choice for ADR-0006.

### D5. Deterministic inputs `PROPOSED`

Inputs, exactly as in the D1 signature: capability name; `CanonicalTarget` or `TargetFailure`; `EffectiveContract` or `ContractFailure` (hashed); `PolicySnapshot` or `PolicyFailure` (hashed); `RevocationSnapshot` or `RevocationFailure` (read fresh by the loader); `task_constraints`; `now_utc`; `last_recorded_utc`. Nothing else.

- Never an input: task text, model output, task-supplied risk or level, environment variables, ambient time.
- Task-supplied `risk` or `level` values are ignored and overwritten. An audit event records that the field was ignored.

### D6. Policy version handling `PROPOSED`

- A policy has an integer `policy_version` and a `policy_sha256`.
- The same version with a different hash is DENY (`POLICY_HASH_MISMATCH`). A content change must raise the version.
- An unknown version is DENY (`POLICY_VERSION_UNKNOWN`). An unreadable policy is DENY (`POLICY_UNAVAILABLE`).
- Policy files live in the repository under a path that CODEOWNERS covers (ADR-0001 D9). Changing a policy file is G-03.
- Policy file format: `UNKNOWN`, decided in ADR-0006. `tomllib` is unavailable on the installed Python (LF-8). The format must be stdlib-parseable, schema-versioned, and UTF-8.

### D7. Expiry, revocation, clock `PROPOSED`

- **Expiry.** A contract may carry `valid_until` (UTC). Past it is DENY (`EXPIRED`). No expiry field is a Phase 1 requirement for grants, because none exist.
- **Clock.** The loader reads the UTC wall clock (injectable in tests) and passes `now_utc`. The loader reads the latest recorded decision time from the audit store and passes it as `last_recorded_utc`. If `now_utc` is earlier than `last_recorded_utc`, the evaluator returns DENY (`CLOCK_SKEW`). It fails closed.
- **Revocation.** The loader reads the revocation list in the governance zone for every evaluation and never caches it. The evaluator receives a `RevocationSnapshot`. A listed capability, project or contract hash is DENY (`REVOKED`). A `RevocationFailure` (unreadable list) is DENY (`REVOCATION_UNAVAILABLE`).
- A revocation takes effect at the next evaluation. A RUNNING task re-evaluates before each side-effecting step (ADR-0002 D2).

### D8. `requires_isolation`, default deny, unknowns `PROPOSED`

- Each capability carries `requires_isolation` (true/false) and a `phase_enabled` flag in the policy.
- If `requires_isolation` is true and no isolation attestation exists, the verdict is DEFER (`ISOLATION_REQUIRED`). No attestation can exist in Phase 1, because no isolation exists. Nothing in this ADR creates one.
- An L4 capability with no approval mechanism is DEFER (`APPROVAL_MECHANISM_ABSENT`). Phase 1 has none.
- A recognized capability not enabled in the current phase is DEFER (`PHASE_NOT_ENABLED`).
- **Default deny.** Anything not matched is DENY.
- **Unknown capability** → DENY `UNKNOWN_CAPABILITY`. **Unknown project** → DENY `UNKNOWN_PROJECT`. **Unknown or unresolvable path** → DENY (`UNKNOWN_TARGET_CLASS`, `TARGET_UNRESOLVABLE`).

### D9. Evaluation ordering and reason codes `PROPOSED` `ENGINEERING AFTER CP-0` (E-2, E-8)

Order. The first DENY wins. If there is no DENY, the first DEFER wins. If neither, ALLOW.

The evaluator (stage 3) applies every step. Where a step's input can fail, the loader (stage 1) or the canonicalizer (stage 2) has already turned the failure into a `*Failure(reason)` value. The evaluator reports that code at the step's position, so precedence is the same whichever stage detected the problem.

1. Input validation (evaluator): types, no extra fields, hashes present where required → `INPUT_INVALID`
2. Policy (`PolicyFailure` from the loader, or the snapshot's version and hash check) → `POLICY_UNAVAILABLE`, `POLICY_VERSION_UNKNOWN`, `POLICY_HASH_MISMATCH`, `POLICY_FORMAT_INVALID`
3. Clock (evaluator: `now_utc` against `last_recorded_utc`) → `CLOCK_SKEW`
4. Capability recognized (evaluator) → `UNKNOWN_CAPABILITY`
5. Revocation (`RevocationFailure` from the loader, or a match in the snapshot) → `REVOCATION_UNAVAILABLE`, `REVOKED`
6. Target raw checks and strict resolution (`TargetFailure` from the canonicalizer) → `TARGET_RAW_INVALID`, `TARGET_UNRESOLVABLE`, `TARGET_CROSS_DRIVE`
7. Target class, assigned by the canonicalizer; always-deny classes (evaluator) → `TARGET_GOVERNANCE_ZONE`, `TARGET_JARVIS_SELF`, `TARGET_DATA_ROOT`, `TARGET_USER_SECRET`, `UNKNOWN_TARGET_CLASS`
8. Project and contract resolution (`ContractFailure` from the loader) → `UNKNOWN_PROJECT`, `CONTRACT_MISSING`, `CONTRACT_SCHEMA_UNKNOWN`, `CONTRACT_INVALID`
9. Expiry (evaluator: `valid_until` against `now_utc`) → `EXPIRED`
10. Contract authorization and narrowing (evaluator): the capability's allowed target classes (D12), scope, forbidden operations, protected paths, `task_constraints` → `TARGET_CLASS_NOT_ALLOWED`, `TARGET_OUT_OF_SCOPE`, `FORBIDDEN_BY_CONTRACT`, `CONSTRAINT_WIDENS`
11. Non-goal and L5 rules → `FORBIDDEN_L5`, `NON_GOAL_V01`
12. Level derivation (D10)
13. DEFER conditions → `PHASE_NOT_ENABLED`, `ISOLATION_REQUIRED`, `APPROVAL_MECHANISM_ABSENT`, `MECHANISM_NOT_IMPLEMENTED`
14. ALLOW → `ALLOWED_BY_POLICY`

The reason-code list above is closed. An unlisted code is a bug and fails the test suite. Adding a code is an ADR amendment. Changing which verdict a code maps to is G-03.

### D10. Risk derivation `PROPOSED`

- `risk_level` = the policy's base level for the capability, raised (never lowered) by target class (protected path, governance-adjacent), contract protection flags, and the L5/non-goal rules.
- **Task risk = the maximum `risk_level` across every requested capability.**
- **Task verdict:** any DENY → task BLOCKED; else any DEFER → task DEFERRED; else the task may move to RUNNING.
- **The evaluator output is authoritative.** A risk or level from a task, a planner or a model is never trusted. It is ignored (D5).

### D11. Policy change during a task `PROPOSED`

- A task records the `policy_version` of its last evaluation.
- Leaving DEFERRED or BLOCKED always re-evaluates under the current policy (test C5).
- A RUNNING task re-evaluates before each side-effecting step if the current version differs.
- A contract hash change since the last evaluation also forces re-evaluation (ADR-0004).

### D12. Initial capability matrix `PROPOSED` `USER AUTHORITY REQUIRED` (G-03)

Levels follow §12. "P1" = Phase 1 verdict.

| Capability | Base level | requires_isolation | Allowed target classes | P1 verdict | Reason |
|---|---|---|---|---|---|
| `CREATE_TASK` | L2 | no | `CONTROL_PLANE_RECORD` only | ALLOW | `ALLOWED_BY_POLICY` |
| `CREATE_REPORT` | L2 | no | `CONTROL_PLANE_RECORD` only | ALLOW | `ALLOWED_BY_POLICY` |
| `READ_REGISTRY` † | L1 | no | `CONTROL_PLANE_RECORD` only | ALLOW | `ALLOWED_BY_POLICY` |
| `READ_CONTROL_PLANE_CONFIG` † | L1 | no | `CONTROL_PLANE_RECORD` only | ALLOW | `ALLOWED_BY_POLICY` |
| `READ_PROJECT` | L1 | no | ANY ‡ | DEFER | `PHASE_NOT_ENABLED` |
| `READ_FILE` | L1 | no | ANY ‡ | DEFER | `PHASE_NOT_ENABLED` |
| `SEARCH_WEB` | L3 | yes | ANY ‡ | DEFER | `ISOLATION_REQUIRED` |
| `WRITE_SANDBOX` | L3 | yes | ANY ‡ | DEFER | `ISOLATION_REQUIRED` |
| `RUN_TEST` | L3 | yes | ANY ‡ | DEFER | `ISOLATION_REQUIRED` |
| `RUN_EXPERIMENT` | L3 | yes | ANY ‡ | DEFER | `ISOLATION_REQUIRED` |
| `USE_CLAUDE_CODE` | L3 | yes | ANY ‡ | DEFER | `ISOLATION_REQUIRED` |
| `USE_CODEBASE_MEMORY` | L3 | yes | ANY ‡ | DEFER | `ISOLATION_REQUIRED` |
| `USE_VERIFICATION` | L3 | yes | ANY ‡ | DEFER | `ISOLATION_REQUIRED` |
| `SCHEDULE_TASK` | L3 | no | ANY ‡ | DEFER | `MECHANISM_NOT_IMPLEMENTED` |
| `GENERATE_WORKER_BRIEF` † | L2 | no | ANY ‡ | DEFER | `PHASE_NOT_ENABLED` (Phase 2; rules in review F5, pending RK) |
| `DELETE_PROTECTED` | L4 | — | ANY ‡ | DEFER | `APPROVAL_MECHANISM_ABSENT` |
| `PUSH` | L4 | — | ANY ‡ | DEFER | `APPROVAL_MECHANISM_ABSENT` |
| `MERGE` | L4 | — | ANY ‡ | DEFER | `APPROVAL_MECHANISM_ABSENT` |
| `DEPLOY` | L4 | — | ANY ‡ | DEFER | `APPROVAL_MECHANISM_ABSENT` |
| `SEND_EMAIL` | L4 | — | ANY ‡ | DEFER | `APPROVAL_MECHANISM_ABSENT` |
| `SEND_MESSAGE` | L4 | — | ANY ‡ | DEFER | `APPROVAL_MECHANISM_ABSENT` |
| `MAKE_CALL` | L4 | — | ANY ‡ | DENY | `NON_GOAL_V01` (§33: phone calling) |
| `FINANCIAL_TRANSACTION` | L4 | — | ANY ‡ | DENY | `NON_GOAL_V01` (§33: financial integrations; zero-spend policy) |
| `CHANGE_PERMISSION` | L5 for JARVIS | — | ANY ‡ | DENY | `FORBIDDEN_L5` |
| `CHANGE_GOVERNANCE` | L5 for JARVIS | — | ANY ‡ | DENY | `FORBIDDEN_L5` |
| `DISABLE_GUARDRAIL` | L5 | — | ANY ‡ | DENY | `FORBIDDEN_L5` |

† Not in the Master Context §13 list. See Open items.

‡ `ANY` means any class except the always-DENY classes and `UNCLASSIFIED`, which are denied at D9 step 7 for every capability. For these rows the Phase 1 verdict is decided by the capability-level rule in the Reason column. Their target classes are not yet specified. The ADR that enables the capability must specify them (G-03). They do not change any Phase 1 verdict.

**Consistency with D2.** The four Phase 1 ALLOW capabilities accept `CONTROL_PLANE_RECORD` only. That class is a record type and ID chosen by the control plane, never a path, so it cannot be classified into an always-DENY class. No Phase 1 ALLOW row can therefore be denied by the target rules of D2, and no always-DENY class can be reached through an ALLOW row. The golden-file test (X-03) and the capability table test (X-01) cover this.

- **Reading of CHANGE_PERMISSION / CHANGE_GOVERNANCE:** §12 lists "permission changes" under L4. In this design a change to permissions or governance is never a JARVIS action. It is made by RK outside JARVIS (editing the governance zone, merging a PR). Any attempt by JARVIS to invoke it is L5 and DENY. No `WRITE_CONTRACT` capability exists (CP-0 review §4.2). This narrows §12/§13. It needs RK's acceptance.
- **Phase 1 ALLOW set is exactly four capabilities.** The full matrix is the policy. Changing any row is G-03.

## 3. Alternatives considered

| Alternative | Rejected because |
|---|---|
| Risk as a task field set by the planner or model | The model would control the verdict. |
| Verdict set {ALLOW, DENY, REQUIRE_APPROVAL} | No approval mechanism exists in Phase 1. A verdict that cannot be honoured would be a hidden DENY. DEFER names the missing mechanism. |
| Treat DEFER as "allowed once isolation exists" | Later authority needs a policy change (G-03), not a state of the machine. |
| Lenient `realpath` | Errors are swallowed. Review F6. |
| Cache the revocation list | A revocation must take effect at the next evaluation. |
| An evaluator that loads its own files, resolves paths and reads the clock | I/O inside the evaluator defeats determinism. The golden-file test would depend on the machine's filesystem and clock. The loader, canonicalizer and evaluator split (D1) keeps the evaluator pure. |

## 4. Evidence

- Master Context §12, §13 (both lists), §14, §26, §33, §40.8.
- `VERIFIED (LF-4, 6, 8, 9, 11, 12)`. `UNKNOWN (LF-10)`.
- CP-0 review: §4.1 (missing elements), F5, F6, §6.2.
- Python documentation for `os.path` (cited in the CP-0 review §11).

## 5. Security impact

- Closes the paths where a model, planner or task could set its own risk or widen its scope.
- Makes every decision replayable (policy and contract hashes recorded).
- Pre-isolation limit: the policy and revocation files are read by a process running as RK. Any process running as RK can edit them. The evaluator is deterministic over its inputs. It does not make those inputs tamper-proof. Detection comes from recorded hashes and the audit chain (ADR-0005).

## 6. Complexity impact

Medium. One pure evaluator, one loader, one canonicalizer, one policy file, golden-file tests. No dependencies beyond the standard library.

## 7. Reversibility

High while nothing depends on it. Changing verdict semantics or the matrix after use is G-03 and invalidates recorded decisions' meaning, so do it by a superseding ADR.

## 8. Authority class

USER AUTHORITY REQUIRED. Triggers G-03, G-05, G-16.

## 9. Consequences

- A closed reason-code list, a golden-file test and a path test suite become part of Phase 1 exit (ADR-0002 X-01 to X-03, X-09, X-16).
- Execution-capable capabilities stay DEFER until an isolation ADR and an attestation mechanism exist. No such mechanism is defined here.
- Policy format and Python version depend on ADR-0006.
- The evaluator's tests (X-01 to X-03) need no filesystem and no clock. The canonicalizer's tests (X-09, X-16) and the loader's failure paths do.

## 10. Open items

| Item | Label |
|---|---|
| Policy file format and the Python version it requires | `UNKNOWN`, ADR-0006 |
| 8.3 short-name behaviour on the workspace volume | `UNKNOWN (LF-10)`, needs elevation |
| Initial list of user-secret location patterns (exact Windows paths) | `UNKNOWN`, `USER AUTHORITY REQUIRED` (G-07) |
| Whether the evaluator signature may include `now_utc` and `last_recorded_utc` | `USER AUTHORITY REQUIRED` (G-03) |
| The allowed-target-class column in D12 and the added reason code `TARGET_CLASS_NOT_ALLOWED` | `USER AUTHORITY REQUIRED` (G-03) |
| Whether MAKE_CALL and FINANCIAL_TRANSACTION are DENY, not DEFER, in v0.1 | `USER AUTHORITY REQUIRED` (G-03) |
| The three added capability names (†) | `USER AUTHORITY REQUIRED` (G-03) |
