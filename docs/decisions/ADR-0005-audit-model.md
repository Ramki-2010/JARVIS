# ADR-0005 — Audit Model

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0005 |
| Title | Audit Model |
| Status | ACCEPTED |
| Drafted | 2026-10-09, by Cloud Claude |
| Authority class | USER AUTHORITY REQUIRED (G-06, G-11, G-12). Items E-1, E-5, E-6 are `ENGINEERING AFTER CP-0` once this ADR is accepted. |
| Inputs | Master Context §7, §17, §18, §19, §26, §28, §32. CP-0 Review — Final (F3, F4, F8, F9, §4.3, R14, R15, R21, R22). Local CP-0 Fact Report 2026-10-09. |
| Related | ADR-0001, ADR-0002, ADR-0003, ADR-0004 |

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
| Accepted text includes | The single-store design, option B (D1), and its reading of Master Context section 17 as a logical separation (D1) |
| Still open | The anchor ref and path (D7), the narrowed files-read scope's follow-ups, and the other open items in section 10 |

---

## 1. Context

1. `MASTER CONTEXT POLICY` §18: every autonomous task produces an audit record with the listed minimum fields. "Audit records must not be editable by ordinary agent operations." §17: audit data is separate from memory. §7: tasks persist and survive restart.
2. Two stores (task state in SQLite, audit in JSONL) can disagree after a crash. Two CLI processes can each read the same last hash and fork the chain (CP-0 review F3, F4).
3. `VERIFIED (LF-7)` Bundled SQLite is 3.40.1. `VERIFIED (LF-6)` Python 3.10.11. `VERIFIED (LF-9)` NTFS.
4. `VERIFIED (LF-4)` `credential.helper` is `manager`. `core.autocrlf` is `true`, so text files written by git checkout become CRLF. `VERIFIED` (Local diff table) `gh` 2.102.0 is installed. `UNKNOWN` `gh` authentication state.
5. `VERIFIED (LF-1)` The build session runs as RK with `permissionMode: "auto"`. A process running as RK can rewrite any file RK can write, including the audit store, and recompute a whole chain.
6. `UNKNOWN (LF-14)` No data root path has been specified.
7. `VERIFIED` The repository is public (RK-stated). The ruleset, force-push protection and bypass list are `UNKNOWN` (ADR-0001 D9).

## 2. Decision

### D1. Single-store transactional model (option B) `PROPOSED` `USER AUTHORITY REQUIRED` (G-11; CP-0 review U-9)

- Task state **and** the audit chain live in **one SQLite database** in the data root (ADR-0004).
- A state change and its audit record are written in **one transaction**. Either both are committed or neither is. Crash consistency follows from SQLite's own atomic commit (review R14).
- The audit chain is a table. The table is the **system of record**. Nothing else is authoritative.
- The audit table is append-only by design: the control plane issues only INSERTs to it. This is a design rule, not an enforcement. A process with file access can still alter the database (D10).
- Journal mode and `synchronous` level are `ENGINEERING AFTER CP-0` (E-5). The requirement is durability at commit and recovery identical on every run (test C2). `synchronous=FULL` is the starting point.

### D2. Writer concurrency and locking `PROPOSED` `ENGINEERING AFTER CP-0` (E-5)

- Every write transaction begins with `BEGIN IMMEDIATE`. It reads the last sequence number and hash inside the transaction, appends exactly one successor, and commits.
- A second process waits on SQLite's lock up to a configured busy timeout. If it cannot acquire the lock, it fails closed: it writes nothing and exits with an error. It never appends without the lock.
- Result: the chain stays linear. No two records share a predecessor (test C1; review R15).

### D3. JSONL or equivalent representation `PROPOSED`

- If retained, JSONL is a **verified export**, not a store. It is regenerated from the table, never edited, and never read back as authoritative.
- Exports are segmented (D9). They stay in the data root. They are not committed anywhere.
- `jarvis audit verify` checks the SQLite chain. It may also check that an export matches it.

### D4. Canonical serialization `PROPOSED` `ENGINEERING AFTER CP-0` (E-1)

- A record is serialized once, to **UTF-8 bytes**, with **sorted keys** and **no insignificant whitespace**. **No Unicode normalisation** is applied.
- The stored bytes are what is hashed. Verification re-hashes the stored bytes. It never re-serializes.
- No floating-point numbers in records. Integers and strings only. Timestamps are UTC strings in one fixed format (`YYYY-MM-DDTHH:MM:SS.ffffffZ`).
- Duplicate keys on parse are an error. A string that cannot be encoded as UTF-8 is an error.
- When an export file is written, open it with `newline='\n'` (CP-0 review §4.4). `core.autocrlf=true` (LF-4) must not alter exports.

### D5. Genesis record and SHA-256 chain `PROPOSED` `ENGINEERING AFTER CP-0` (E-6)

- Record 0 (genesis): `seq = 0`, `prev_hash` = 64 zeros. It lists the policy versions and hashes in force, the evaluator version and the schema versions.
- Every later record contains `seq` and `prev_hash` inside its canonical bytes. `record_hash = SHA-256(record_bytes)`. The next record's `prev_hash` equals this record's `record_hash`.
- `audit verify` walks the chain from genesis. It fails on a missing sequence number, a hash mismatch, a wrong predecessor, or a reordering.
- Every record carries the §18 fields (task_id, timestamp, project, objective, risk_level, tools_used, files_read, files_modified, commands_run, research_sources, models_used, tests_run, verification_results, retries, errors, final_status, approval_events), empty where unused (CP-0 review §5 row 6).

### D6. HEAD anchor `PROPOSED`

- `HEAD` is a small file containing only the **sequence number and the record hash** of the latest committed record. It contains no task text, no timestamp beyond what the chain already implies, and no personal data.
- The control plane writes `HEAD` into the data root after each commit. It is derived. If it lags after a crash, `audit verify` regenerates it.
- On start and on `audit verify`: if `HEAD`'s sequence number is greater than the store's tail, the control plane records `AUDIT_TRUNCATION_SUSPECTED` and stops accepting new work until RK reviews it.

### D7. Off-machine HEAD anchoring `PROPOSED` `USER AUTHORITY REQUIRED` (CP-0 review U-10, U-5, U-6)

- RK copies `HEAD` into a checkout of the public repository and commits and pushes it by hand, **weekly**, from Phase 1 (review F8).
- **JARVIS performs no network access to maintain the anchor.** The push is RK's act with RK's git tooling. No JARVIS code path opens a socket (test X-13 in ADR-0002). This is not a capability.
- The anchor counts as off-machine only once RK has verified a ruleset that blocks force pushes and deletion on the ref that carries the anchor, with an empty bypass list. Until RK records that check (`docs/phase0/inventory.md`, review §8.3), the repository is "already public (RK-stated)", not a verified anchor. This is risk R22.
- **Which ref carries the anchor** (main via PR, or a dedicated branch or tag) is `UNKNOWN` and `USER AUTHORITY REQUIRED` (G-12). A dedicated branch must be covered by force-push and deletion protection. A ruleset that targets only `main` does not protect it. Direct pushes to `main` are blocked if the ruleset requires pull requests.
- What it proves: a record at or before the anchored sequence number cannot be rewritten without the mismatch showing against the public copy.

### D8. Provenance classes `PROPOSED` `ENGINEERING AFTER CP-0`-adjacent; the classes themselves are `USER AUTHORITY REQUIRED` (G-11)

Every field in every record carries a class. Strength order: **OBSERVED > MEDIATED > REPORTED**.

| Class | Meaning |
|---|---|
| `OBSERVED` | The control plane directly observed or computed the event. Example: a policy hash it computed, an evaluation it ran. |
| `MEDIATED` | A fact RK relays from a tool, such as pasted test output. JARVIS observed RK's input, not the event itself. |
| `REPORTED` | Asserted by a worker, model, session or third party. Not observed by JARVIS. |
| `DERIVED` | Computed from other fields. It takes the weakest class among its inputs. |

- The **actor** field (who invoked the CLI) records the OS user. [Likely] The control plane cannot tell RK from a build session running under the same account. The field is therefore recorded as OBSERVED OS-user identity, with an explicit note that it does not establish a human. This limit remains until isolation and credential separation exist.
- A VERIFIED verification result is impossible in Phase 1 (ADR-0002 D2). Verification fields default to NOT_VERIFIED and carry provenance.

### D9. Files-read scope and rotation `PROPOSED`

- **Files-read scope.** In Phase 1, `files_read` covers only the control plane's own configuration, contracts and policy. Never project files. A later phase that reads worker-touched files can record only what the control plane mediates. The worker's own file reads cannot be captured without OS file-access auditing, which does not exist. This narrows the completeness the Master Context §18 and §32 imply. It needs RK's acceptance (G-11). Mediated reads are recorded as MEDIATED or REPORTED, never OBSERVED.
- **Rotation (exports).** Exports are split into segment files. Each new segment starts with a `SEGMENT_START` record that carries the previous segment's final hash and the sequence range. The SQLite chain itself is never rotated or truncated in Phase 1. Size thresholds are an engineering choice.

### D10. Tamper-evident, not tamper-proof `PROPOSED`

This ADR claims **tamper-evident within this trust boundary**. It does **not** claim tamper-proof.

- Anyone who can rewrite the SQLite file as RK, including the build session, can also rewrite every record after any chosen point and recompute the chain and `HEAD`.
- The chain is checkable against the off-machine anchor only up to the last anchored sequence number. Records after the last anchor, up to one week of activity, can be rewritten without detection.
- Against a worker running under another account, tamper-resistance depends on an ACL boundary that does not exist yet. No such claim is made here.
- The claim holds against anyone who cannot also rewrite the public anchor, and only after the force-push check (D7).

### D11. Sensitive-content handling `PROPOSED`

- Task text may hold personal data. The audit store and exports stay in the data root: outside git, outside cloud-synced folders (ADR-0004 D2).
- Records never contain environment variable values, credentials, tokens or key material. The config loader rejects secret-like keys (test C3).
- Only `HEAD` (sequence number and hash) leaves the machine, by RK's hand.
- RK scans a commit for personal data before pushing `HEAD` (risk R21). The tool for that is `UNKNOWN`; no new software is proposed.

### D12. Crash consistency and recovery `PROPOSED`

- A crash before commit: neither state nor audit record exists. A crash after commit: both exist. There is no intermediate state to reconcile (test C2).
- On start, the control plane verifies the chain tail (sequence is continuous and the last hash matches), runs SQLite's integrity check, and compares with `HEAD` (D6).
- A recovery that finds an anomaly appends a `RECOVERY` record (OBSERVED) stating what it found. Recovery is identical on every run.

## 3. Alternatives considered

| Alternative | Rejected because |
|---|---|
| Option A: two stores, intent and commit records | Recovery depends on reconciling two files. Needs an explicit lock file for the writer. More failure modes. |
| JSONL as the store | A crash can leave a partial line and state out of step. |
| Anchor only on the same machine | Anyone who can rewrite the log as RK can rewrite HEAD. Detects accidental truncation only. |
| JARVIS pushes the anchor itself | Gives JARVIS network access for its own bookkeeping. Violates the zero-network Phase 1 boundary. |
| Claim tamper-proof | False before isolation. |

## 4. Evidence

- Master Context §7, §17, §18, §19, §26, §32.
- `VERIFIED (LF-1, 4, 6, 7, 9)`. `UNKNOWN (LF-14)`.
- CP-0 review: F3, F4, F8, F9, §4.3, R14, R15, R21, R22, §8.3.
- Python and SQLite documentation as cited in the CP-0 review §11.

## 5. Security impact

- Positive: removes state/audit divergence and chain forking. Gives a verifiable chain with an off-machine check point.
- Residual: tamper-evident only (D10). The actor field does not identify a human (D8). `files_read` is incomplete for any worker (D9). `gh` and credential state can undermine the anchor ref (ADR-0001).

## 6. Complexity impact

Medium. One database, one writer rule, one canonicaliser, one verifier. Standard library only.

## 7. Reversibility

Moderate. The record format and hash rule, once data exists, cannot be changed without a migration or a new chain segment. Decide before Phase 1 writes records.

## 8. Authority class

USER AUTHORITY REQUIRED. Triggers G-06, G-11, G-12.

## 9. Consequences

- ADR-0006 must set the Python version and pragmas.
- Tests X-04, X-05, X-06, X-08 in ADR-0002 are acceptance evidence for this ADR.
- RK takes on a recurring manual task (weekly anchor) and the GitHub check before the first anchor push.
- The Master Context §18 `files_read` completeness is narrowed (D9). That is a reading RK must accept.

## 10. Open items

| Item | Label |
|---|---|
| Data root path | `UNKNOWN`, `USER AUTHORITY REQUIRED` |
| Ruleset, force-push protection, bypass list, CODEOWNERS | `UNKNOWN`, RK's GitHub check |
| Which ref carries the anchor | `UNKNOWN`, `USER AUTHORITY REQUIRED` |
| Option B (one store) acceptance | `USER AUTHORITY REQUIRED` (U-9) |
| Weekly manual anchor push | `USER AUTHORITY REQUIRED` (U-10) |
| Files-read scope narrowing | `USER AUTHORITY REQUIRED` (G-11) |
| SQLite journal mode, busy timeout, rotation size | `ENGINEERING AFTER CP-0` |
| Tool for scanning a commit for personal data before pushing HEAD | `UNKNOWN` |
