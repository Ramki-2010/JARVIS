# ADR-0006 — Phase 1 Technical Stack and Local Implementation Baseline

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0006 |
| Date drafted | 2026-10-09 |
| Drafted by | Local Claude (environment-grounded engineering proposal) |
| Authority class | Stack choices: `ENGINEERING AFTER CP-0`. Installing or upgrading Python: `USER AUTHORITY REQUIRED` (U-11). Accepting this ADR: `USER AUTHORITY REQUIRED` (U-12). |
| Reversibility | High. Nothing is installed or implemented. Each choice can change before Phase 1 code exists. |
| Complexity impact | Low by design. No third-party packages, no framework, no packaging. |
| Depends on | ADR-0003 (capability evaluation and path canonicaliser), ADR-0004 (contracts), ADR-0005 (audit). Not drafted here. Where a section below depends on an undecided ADR, it says so. |
| Does not change | The Master Context. An ADR cannot amend it (Final CP-0 Review, F2). |

Labels used: `VERIFIED` (observed locally, command or source stated), `UNKNOWN`, `MASTER CONTEXT POLICY`, `PROPOSED`, `USER AUTHORITY REQUIRED`, `LOCAL FACT CHECK REQUIRED`, `ENGINEERING AFTER CP-0`.

Nothing in this document has been implemented. No software was installed and no repository file was changed to produce it.

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-11 |
| How the acceptance was given | A written instruction from the founder to Local Claude on 2026-10-11. Under ADR-0001 D6 that instruction is an input. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this document. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6: approval applies to the exact text accepted) |
| Accepted text includes | The stack baseline and the test-process structure references (sections 2 to 4, 6), with the exclusions recorded below |
| Python | No installation or upgrade is authorized by this acceptance |

### Acceptance conditions (section 10 of this ADR)

Section 10 lists seven conditions. Their state at acceptance, recorded without deciding anything new:

| # | Condition | State |
|---|---|---|
| 1 | The user has decided the Python option, or explicitly deferred it | **Not decided.** The founder's instruction of 2026-10-11 does not choose an option and does not authorize installing Python 3.11 or 3.13. Per this condition, acceptance **excludes the `tomllib` and minimum-version clauses** (section 2 item 2, the `tomllib` row of section 3.1, and section 5.2). The Python option stays a separate decision (U-11) |
| 2 | ADR-0005 has decided one store versus two | Met by the acceptance of ADR-0005 in the same pull request |
| 3 | The data root location is decided or explicitly deferred | **Not decided.** Treated as deferred, as in ADR-0004 section 10 |
| 4 | The Cloud review has checked this ADR against the Master Context citations and the Local facts | The Cloud cross-review and final review reports exist for the drafts |
| 5 | The unresolved items in section 11 are resolved or accepted as UNKNOWN | Accepted as UNKNOWN with the handling stated in section 11 |
| 6 | Tests mapped to this ADR exist in the Phase 1 plan | Mapped by ADR-0002 D5 (X-05, X-06, X-08, X-09, X-16) |
| 7 | No clause claims an audit hook, the import scan or any in-process check is an isolation boundary | Met by the text as accepted (sections 3.2 and 6.1) |

---

## 1. Context

Phase 1 is the deterministic control plane: task state, capability evaluation, contracts and audit. It runs no model, makes no network call, starts no subprocess and executes no worker. The Final CP-0 Review (Section 4.4 and finding F7) concluded that Phase 1 can be built on the Python standard library alone, using `unittest`, with zero installs, provided the installed Python is new enough.

The Local CP-0 fact inspection (2026-10-09) shows it is not new enough for one module the baseline names (`tomllib`). That gap is the main open decision in this ADR.

Related Master Context policy: section 3 (runs locally, one-person maintainability), section 26 (least privilege, external input untrusted), section 28 (no silent dependencies), section 34 (prefer simple, modular, observable, reversible, local). The Master Context does not specify a language. Python is a proposal, not a Master Context requirement.

## 2. Decision (proposed)

1. Phase 1 is implemented in Python using the **standard library only**. No third-party package is required, and none may be added without a separate decision.
2. The minimum Python version is **3.11**, because `tomllib` (TOML configuration) first ships in 3.11. Python 3.13 or later is preferred if the user chooses to install, because it adds Windows path helpers that remove hand-written checks (Section 5.3). `USER AUTHORITY REQUIRED`: which version, and whether to install at all (Section 7).
3. **SQLite** (`sqlite3`) is the transactional persistence store for task state and, if ADR-0005 accepts the one-store option (U-9), for the audit chain.
4. The control plane is a **deterministic, single-purpose process** run on demand as `python -m jarvis`. It has no daemon, no model, no network, no subprocess and no worker execution.
5. Text is **UTF-8** everywhere, set explicitly in code. Repository-controlled text uses **LF** line endings (Section 6.2).
6. Tests use **`unittest`** from the standard library.
7. No packaging or distribution requirement exists in Phase 1.

## 3. Technical baseline

### 3.1 Standard-library modules

| Module | Use in Phase 1 | Minimum Python | Notes |
|---|---|---|---|
| `argparse` | CLI (`task`, `status`, `report`, `cancel`, `audit verify`) | any in scope | |
| `dataclasses` | Frozen data types for tasks, decisions, contracts | any in scope | Use `frozen=True`. No free-text field may feed the evaluator (ADR-0003). |
| `pathlib` | Path handling | any in scope | Resolution rules in Section 5.3. |
| `os`, `os.path` | `realpath(strict=True)`, `commonpath` | `strict=` exists since 3.10 | VERIFIED locally: `strict` parameter present on 3.10.11. |
| `json` | Canonical JSON for audit records, JSON export | any in scope | Canonical rules belong to ADR-0005. |
| `hashlib` | SHA-256 for the audit chain and contract/policy hashes | any in scope | Unkeyed. Tamper-evident only within the stated trust boundary. |
| `sqlite3` | Task state and (conditionally) the audit store | any in scope | VERIFIED locally: bundled SQLite library 3.40.1. |
| `tomllib` | Read-only TOML configuration and contracts | **3.11** | Read-only parser. VERIFIED locally: not importable under 3.10.11. |
| `unittest` | Test suite | any in scope | VERIFIED locally: imports. |
| `msvcrt` | Windows file locking | Windows only | Needed only if ADR-0005 chooses two stores (option A). Not needed under the one-store option. VERIFIED locally: imports. |
| `datetime` / `time` | UTC clock, injectable in tests (ADR-0003 expiry) | any in scope | The evaluator reads no clock except for expiry. |

Other standard-library modules may be used if a need arises, if they are not on the forbidden list below.

### 3.2 Forbidden in Phase 1 product code

`PROPOSED`. A static test (a scan of the code's parsed syntax, run under `unittest`) fails if product code imports any of these, or calls the listed builtins. This catches mistakes. It is not a security boundary (Section 6.1).

- Network: `socket`, `ssl`, `http`, `urllib`, `ftplib`, `smtplib`, `xmlrpc`, `asyncio` networking.
- Process creation: `subprocess`, `multiprocessing`, `os.system`, the `os.spawn*`, `os.exec*` and `os.popen` families.
- Native code and dynamic loading: `ctypes`, `cffi`, `importlib` dynamic loading of arbitrary paths.
- Unsafe deserialization and code evaluation: `pickle`, `marshal`, `shelve`, `eval`, `exec`, `compile`.
- Any import outside the standard library.

Scope of the forbidden list: product code under `jarvis/`. The runtime restriction is not weakened. The static scan covers all of `jarvis/`, and a runtime audit hook (Section 6.1) covers every `python -m jarvis` process the tests start.

The test harness is outside the product-code guard. Two required tests (C1, C2) need child processes, so the harness starts them. It may start a child only by one helper that runs `python -m jarvis` with the given arguments, and a static check over `tests/` fails if any other process-creating call appears. Crash injection for C2 comes from a test hook inside the child. No test code is added to `jarvis/`. The structure is specified in ADR-0002 D5 ("Test process structure").

### 3.3 Process model

- One short-lived process per command. No background threads.
- Single writer to SQLite at a time (Section 4.1).
- Configuration comes from files only. The process reads no environment variable that influences behavior (Section 6.3).
- Exit codes are defined and tested. Any unhandled error fails closed.

### 3.4 Encoding and line endings

- VERIFIED locally: the installed Python's default text encoding is `cp1252` (`locale.getpreferredencoding(False)`), and UTF-8 mode is off (`sys.flags.utf8_mode` is 0). The filesystem encoding is `utf-8`.
- Therefore every `open()` call passes `encoding='utf-8'` explicitly, and writers pass `newline='\n'` explicitly. The code does not rely on UTF-8 mode, the locale, or an environment variable.
- A static test fails on any `open()` in text mode without an explicit encoding.

## 4. SQLite approach

### 4.1 Transactions, writer locking and concurrency

`PROPOSED`, subject to ADR-0005 (U-9):

- Open connections with `isolation_level=None` so Python does not start transactions implicitly. VERIFIED locally: the `sqlite3.Connection.autocommit` attribute does not exist on 3.10.11, so the code must not depend on it. `isolation_level=None` works on every version in scope.
- Every write is an explicit `BEGIN IMMEDIATE ... COMMIT`. `BEGIN IMMEDIATE` takes SQLite's write lock at the start, so two CLI processes serialize on it. This is the writer lock; no separate lock file is needed under the one-store option (F4).
- Set a bounded `busy_timeout`. After the timeout the command fails closed with a defined exit code and an audit event where possible. No unbounded retry loop.
- Read the audit chain tail inside the same `BEGIN IMMEDIATE` transaction that appends the next record, so two writers cannot fork the chain (test C1).
- `PRAGMA foreign_keys = ON` on every connection. Use strict typing where the SQLite version allows it (SQLite 3.37 and later per SQLite's documentation; not re-verified in this session; `UNKNOWN` for a new Python until its SQLite version is checked).
- If ADR-0005 instead chooses two stores (option A), a lock file opened exclusively (with `msvcrt` or equivalent) provides the writer lock, and ordering follows the intent/commit/commit-record rule of F3. That path is more complex and is not the proposed default.

### 4.2 Crash consistency

- Under the one-store option, task state and the audit record are written in a single SQLite transaction, so a crash leaves both or neither. This is the F3 option B rationale.
- Durability setting: `PRAGMA synchronous = FULL`. Journal mode: SQLite's default rollback journal. WAL is not required. `PROPOSED` default is the simplest mode that gives atomic commit on a local NTFS volume; `UNKNOWN` whether interference from antivirus or indexing software on this machine affects commit timing.
- At start, run a cheap integrity check (`PRAGMA quick_check`). Any failure stops the process. Recovery is never silent.
- A JSONL file, if used at all, is a verified export of the table. It is rebuilt from the table. It is never the source of truth.
- Test C2 proves recovery: crash at each point of a commit, recovery identical on every run, recovery logged.

### 4.3 Location

The SQLite file lives in the data root, outside any Git repository (R21, ADR-0005). The data root location is `UNKNOWN` (LF-14: not specified). Nothing here chooses it.

## 5. Compatibility considerations

### 5.1 Python 3.10 → 3.11+ gap

VERIFIED locally (CP-0 fact inspection and the probe for this ADR): Python 3.10.11, 64-bit, installed per user. `py -0p` lists only that version.

| Feature needed | Introduced | On 3.10.11 |
|---|---|---|
| `tomllib` | 3.11 | Absent (VERIFIED: `ModuleNotFoundError`) |
| `os.path.isjunction`, `Path.is_junction` | 3.12 | Absent (VERIFIED for `os.path.isjunction`) |
| `os.path.isreserved` | 3.13 (Windows reserved names) | Absent (VERIFIED) |
| `os.path.realpath(strict=True)` | 3.10 | Present (VERIFIED) |
| `sys.addaudithook` | 3.8 | Present (VERIFIED) |

The version introductions for 3.11, 3.12 and 3.13 come from the Final CP-0 Review (which cites the Python documentation). They were not re-checked against the documentation in this session; only the 3.10.11 column was observed.

Consequence: the "zero installs" outcome from F7 and Section 4.4 does not hold. The installed Python cannot run a TOML-based baseline.

### 5.2 Options for the gap (`USER AUTHORITY REQUIRED`, U-11)

| Option | What it means | Trade-offs |
|---|---|---|
| A. Install Python 3.13 (or newer) alongside 3.10 | New runtime, used via the `py` launcher | Removes hand-written reserved-name and junction checks. Adds an install and a PATH decision. |
| B. Install Python 3.11 alongside 3.10 | Smallest version that provides `tomllib` | Keeps the hand-written reserved-name and junction checks. |
| C. Stay on 3.10.11 | No install. Configuration and contracts use a format Python 3.10 can parse in the standard library (for example JSON or `configparser`) | Zero installs. Departs from the TOML baseline in the Final Review. 3.10's published end-of-life date (October 2026 per PEP 619) is `UNKNOWN` until re-verified; this ADR did not check it. |

This ADR does not choose among them and does not install anything. It proposes that the minimum requirement is 3.11 (option B or A). Option C requires revising the baseline.

Install-time facts to check later (`LOCAL FACT CHECK REQUIRED`): which interpreter `python` resolves to after installation (current `where.exe python` order: Python310 first, then the Microsoft Store alias stub), whether the installer needs elevation for a per-user install, the bundled SQLite version of the chosen Python, and whether that build honors long paths.

### 5.3 Path handling on Windows

Requirements the stack must support (the algorithm itself belongs to ADR-0003, E-3):

- `os.path.realpath(path, strict=True)`; any error is DENY. VERIFIED locally: `strict=` is supported on 3.10.11. By default `realpath` stops resolving at the first failing component, so non-strict resolution can leave links unresolved (F6, citing the Python documentation).
- Raw-input checks run before any normalising call. `os.path.abspath` strips trailing dots and spaces on Windows, so such input must be rejected before it is normalised (test C4).
- `os.path.commonpath` raises on paths on different drives. Treat as DENY.
- Reserved names: `isreserved` (3.13 and later) when available; otherwise a hand-written check on 3.11 or 3.12.
- Case rules: NTFS is case-insensitive by default, and `os.path.normcase` does not match NTFS folding for some non-ASCII letters (F6). Non-ASCII paths in scope roots get an explicit test.
- Also covered by tests: alternate data streams (`name:stream`), device-path prefixes, UNC paths and junctions.

### 5.4 Facts about this machine that shape the path and test design

- VERIFIED: the workspace path is `D:\J.A.R.V.I.S AI Assistant`, 27 characters, with 2 spaces and 5 dots. Tests must include paths containing spaces and multiple dots.
- VERIFIED: D: is NTFS. `LongPathsEnabled` is `1` in the registry. Whether the installed Python build honors long paths is `UNKNOWN` until tested.
- `UNKNOWN`: 8.3 short-name generation on D:. The query `fsutil 8dot3name query D:` was denied without elevation (LF-10). Tests that depend on 8.3 names must report UNKNOWN or skip with an explicit message, never pass silently.
- `UNKNOWN`: whether symlinks can be created without elevation or Developer Mode on this account. Junction and symlink tests depend on it.

## 6. Security considerations

### 6.1 Audit hooks and the guard

`sys.addaudithook` exists on the installed Python (VERIFIED). It is a **detection and observation mechanism, not a sandbox and not an isolation boundary**. It can observe events such as network and process creation. It does not stop native code, does not isolate the process from the user's account, and code running in the same process can attempt to subvert it. This ADR does not rely on it for security.

`PROPOSED` use (E-4): in the test suite only, a hook that exists only inside each child process the harness starts as `python -m jarvis`. It is installed by a startup module under `tests/`, not by product code. In that child it fails the test on audit events for sockets, process creation, native code (`ctypes`) and imports outside the standard library, so a regression is detected. The harness parent is outside the guard and starts only `python -m jarvis`. The hook supplements the static scan of `jarvis/` (Section 3.2). Neither is a boundary. Isolation is a Phase 3 matter (R3, R4, R5, R6 and the Master Context's sandbox policy).

For crash injection (test C2), the Python built-in audit events cover SQLite only at `connect` and `connect/handle`, not at statement execution (VERIFIED locally on 3.10.11). A child-side test hook that ends the process at a chosen SQLite statement boundary therefore has to wrap the connection that product code opens, for example through a test-only connection factory or trace callback installed before product code runs. Whether this works end to end is `UNKNOWN` until test C2 first runs. It is `ENGINEERING AFTER CP-0`.

### 6.2 Line endings and hashing

- VERIFIED: `core.autocrlf` is `true` (from the system Git configuration). VERIFIED earlier in this session: with that setting, working-tree copies of repository text files are checked out with CRLF, while the committed blobs are LF.
- The proposed policy is LF for repository-controlled text. The setting `core.autocrlf=true` conflicts with it. A repository-level `.gitattributes` entry would make LF deterministic. **No `.gitattributes` exists and none is created by this ADR** (`USER AUTHORITY REQUIRED` as a repository-governance change; see D-5 in Section 12).
- Consequence for ADR-0003 and ADR-0004: those ADRs record the SHA-256 of contract and policy files per decision. If such files live in a Git repository under `core.autocrlf=true`, their working-tree bytes can differ from the committed bytes, and hashes will differ between clones. Either the files live in the data root outside Git, or the hash is defined over a canonical form, or the files are exempted from conversion. `UNKNOWN` until ADR-0004 fixes their location.

### 6.3 Configuration and secrets

- Configuration is loaded from files only. The process reads no environment variable for behavior (test C3: loaded configuration is byte-identical with and without a secret-looking variable set).
- VERIFIED: one environment variable name matches the secret patterns in this session: `CLAUDE_CODE_MESSAGING_TOKEN`. Its value was never read or printed. Tests must not print environment values.
- Configuration secret rejection: the configuration loader rejects keys whose names match secret patterns (for example key, token, secret, password, credential) and rejects values that look like credentials. This is a mistake detector, not a guarantee, and it does not make storing secrets in configuration acceptable. Secrets do not belong in configuration or in the audit log.
- Error messages and audit records never include configuration values.

### 6.4 Other

- No third-party packages means no supply-chain exposure from package installs in Phase 1. It does not remove the trust placed in the Python installation itself or in the standard library.
- The control plane runs with the user's full Windows rights. Phase 1 has no isolation boundary, and this ADR does not claim one (R1, R3 to R6, R12, R13 in the CP-0 and gate risk analysis).
- The Claude Code permission mode in this session is `auto` (VERIFIED, LF-1). It is an environment fact about how Local Claude is run. It is not a control that JARVIS relies on.
- No non-sample Git hooks exist (VERIFIED, LF-5), and `core.hooksPath` is unset (VERIFIED, LF-4). No automation enforces line endings, tests or secret scanning at commit time. Nothing here adds any.

## 7. Installation implications

- No installation is performed or requested by this ADR.
- If the user chooses option A or B, a Python installation is needed, and that is a separate `USER AUTHORITY REQUIRED` decision (U-11), taken after CP-0 closes. Phase 1 implementation does not start before it.
- The proposed baseline needs nothing beyond that interpreter: no `pip install`, no virtual environment, no package. `unittest` ships with Python.
- If the user chooses option C (stay on 3.10.11), no install is needed, but the configuration format changes (Section 5.2) and this ADR should be revised before acceptance.
- Packaging: none. Run as `python -m jarvis` from the project directory. A virtual environment is not needed when no packages are installed, and is not part of this baseline.

## 8. Alternatives considered

| Alternative | Why not proposed |
|---|---|
| Third-party test runner (`pytest`) | Adds an install and a dependency for no Phase 1 need (F7). `unittest` is sufficient. |
| Third-party TOML or config libraries | Adds a dependency. `tomllib` covers read-only needs from 3.11. |
| JSON for all configuration | Possible. Viable if the user chooses option C. Loses comments and some readability. |
| Flat files (JSONL only) for task state | Two stores and no atomic commit across them (F3). SQLite gives atomicity, locking and crash safety. |
| WAL journal mode | More files (`-wal`, `-shm`) and more failure modes. Not needed for a single short-lived writer. Can be revisited. |
| Daemon or long-running service | Adds state, lifecycle and attack surface. Phase 1 needs none. |
| Packaging as a wheel or executable | No Phase 1 need. Packaging expands the install surface. |
| A different language | Not evaluated against Python in this ADR. The Master Context does not specify a language. Python is installed, familiar and sufficient. Revisit if the user prefers otherwise. |
| Rely on audit hooks for isolation | Rejected. They detect events. They are not a boundary. |

## 9. Consequences

- Phase 1 has no third-party dependency and a small, auditable import surface.
- A decision is needed before any Phase 1 code can run: install a newer Python, or change the configuration format.
- SQLite adds a single file and some operational care: location, backup, integrity check, locking behavior.
- Hash stability for governance files depends on resolving the `autocrlf` and file-location questions.
- Test coverage must include Windows-specific cases, some of which depend on UNKNOWN facts (8.3 names, symlink privilege, long-path behavior of the installed build). Those tests must report UNKNOWN visibly instead of silently passing.
- The forbidden-imports scan and audit-hook guard add test code but no runtime dependency.
- This ADR does not isolate anything. Isolation remains a later phase.

## 10. Acceptance requirements

This ADR may be accepted only when all of the following hold. Acceptance is `USER AUTHORITY REQUIRED` (U-12).

1. The user has decided the Python option (A, B or C) or explicitly deferred it. If deferred, acceptance excludes the `tomllib` and minimum-version clauses.
2. ADR-0005 has decided one store versus two stores (U-9), or this ADR's Section 4 is accepted as conditional on it.
3. The data root location is decided or explicitly deferred (LF-14, U-4).
4. The Cloud review has checked this ADR against the Master Context citations and the Local facts.
5. The unresolved items in Section 11 are either resolved by Local fact checks or accepted as UNKNOWN with their handling stated.
6. Tests mapped to this ADR exist in the Phase 1 plan: C1, C2, C3, C4, plus the Windows-specific tests in Section 5.3 and 5.4.
7. No clause claims that audit hooks, the import scan or any in-process check is an isolation boundary.

## 11. Unresolved UNKNOWNs

| # | UNKNOWN | How it can be resolved |
|---|---|---|
| 1 | Which Python version to install, or whether to stay on 3.10.11 | User decision (U-11) |
| 2 | Python 3.10's end-of-life date (October 2026 per PEP 619, recalled, not verified here) | Read the Python documentation |
| 3 | `python` resolution order after a new install (the Store alias stub is also on PATH) | Local check after install |
| 4 | Bundled SQLite version of the Python that would be installed, and whether STRICT tables (3.37+) are available | Local check after install |
| 5 | Whether the installed Python build honors long paths (registry value is 1) | Local test after install |
| 6 | 8.3 short-name generation on D: | Elevated read-only inspection (`fsutil 8dot3name query D:`), user decision to elevate |
| 7 | Whether symlinks or junctions can be created by this account without elevation | Local read-only check, then a test fixture decision |
| 8 | Data root location, and whether it lies inside a Git repository (LF-14) | User decision (U-4) |
| 9 | One-store versus two-store audit (ADR-0005, U-9) | User decision |
| 10 | Whether `.gitattributes` will be added, and where governance files live | User decision |
| 11 | Antivirus or indexer interference with SQLite commit behavior on this machine | Observed during Phase 1 testing |
| 12 | Whether per-user Python installation needs elevation | Observed at install time |
| 13 | Accuracy of Python version introductions for 3.11 to 3.13 features | Re-check against the Python documentation |
| 14 | Whether the child-side crash hook for test C2 can wrap the SQLite connection end to end | Observed when test C2 first runs |

## 12. Facts requiring user decision or future verification

**User decisions**
- D-1. Install a newer Python (3.11 or 3.13+), or stay on 3.10.11 with a non-TOML configuration format (U-11). No install happens until you decide, and not before CP-0 closes.
- D-2. Accept or reject ADR-0006 (U-12), after the Cloud review.
- D-3. One-store or two-store audit design (U-9, ADR-0005). Section 4 depends on it.
- D-4. Data root location (U-4) and whether it sits outside Git.
- D-5. Whether to add a repository `.gitattributes` to pin LF line endings, given `core.autocrlf=true`.

**Future Local verification (read-only unless noted)**
- V-1. After any install: `python`/`py` resolution, version, `tomllib` import, bundled SQLite version.
- V-2. 8.3 short-name generation on D: (needs elevation; your decision).
- V-3. Whether symlink or junction creation works without elevation.
- V-4. Long-path behavior of the chosen Python build.
- V-5. Whether the data root lies inside any Git repository, once it is chosen.
- V-6. Re-check the Python 3.10 end-of-life date and the version-introduction claims in Section 5.1.
