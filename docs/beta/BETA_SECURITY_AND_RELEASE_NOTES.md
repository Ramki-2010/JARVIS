# JARVIS Beta: security notes and release notes

**Status:** release documentation, drafted 2026-10-30 for the 2026-11-29 Beta. Non-authoritative: the accepted ADRs and the Master Context govern. It records facts and open items so they can be decided at Gate 6 (26 Nov).
**Labels:** `IMPLEMENTED`, `TESTED`, `OBSERVED` (on the real install, dated), `PLANNED`, `RK DECISION`.

## 1. Scope

The Beta is JARVIS as a governed, human-in-the-loop project assistant (Beta plan, accepted by RK 2026-10-30). It implements Master Context Phase 2 (manual worker bridge) with the memory slice it needs. **It does not meet the Master Context section 31 first acceptance test** (it does no research, sandboxing or experiments) and is not "v0.1 complete".

## 2. What the Beta enforces

| Boundary | How | Evidence |
|---|---|---|
| Only nine capabilities can be allowed: `CREATE_TASK`, `CREATE_REPORT`, `READ_REGISTRY`, `READ_CONTROL_PLANE_CONFIG`, `READ_PROJECT`, `READ_FILE`, `GENERATE_WORKER_BRIEF`, `RECORD_RESULT`, `RECORD_NOTE` | policy version 2; a test derives the implemented set from the code and requires it to equal the policy's allowable set | `TESTED` |
| No network, subprocess, model, worker execution, scheduler, isolation-gated work or L4/L5 action | every other row keeps its version 1 verdict; unknown capabilities are denied; static guard (X-13a) and runtime guard in every child test (X-13b) | `TESTED` |
| A missing or invalid policy denies everything | evaluator, and the read step re-checks the policy when it runs | `TESTED` |
| Reads stay inside the contract | strict canonicalization, scope roots, always-deny classes (governance zone, data root, JARVIS tree, user-secret locations), re-evaluation at run time, 64 KiB cap, regular text files only, secret-looking names refused, path re-resolved before and after the read | `TESTED` (B-04) |
| A relayed result is inert | stored verbatim, labelled untrusted, hash only in the chain, never imported by planner, evaluator, authorizer or brief builder, never changes a task, display escaped | `TESTED` (B-05) including a hostile result |
| Briefs grant no authority and are deterministic | built only from the task record, the contract and the bytes read in the same run; every excerpt line is prefixed so file text cannot forge structure | `TESTED` |
| Notes, briefs and results are tamper-evident | SHA-256 in the audit record, rechecked by `show` and `doctor`; unrecorded files reported | `TESTED` |
| Crash behaviour of `task run` | a kill on either side of the completing commit leaves a defined state; the report file is repaired from the committed state | `TESTED` (B-07) |
| Governance is untouched by any command | no JARVIS command writes to the governance zone, a project, or a ruleset | `TESTED` (end-to-end test compares the files) |

## 3. Known limitations (stated, not hidden)

- **Audit integrity is tamper-evident, not tamper-proof** (ADR-0005 D10). The actor field is the OS user and does not establish a human. Anchor independence is procedural (ADR-0009) and the `gh` credential-access decision is open. The first anchor does not exist yet. `RK DECISION`.
- **Worker reads are not captured.** `files_read` records only what JARVIS itself mediated (ADR-0005 D9).
- **Nothing is verified.** There is no independent verifier; `VERIFIED` is unreachable.
- **RUNNING tasks are not re-evaluated** by the state machine. The read step re-checks authority itself and, if it is gone, reads nothing and leaves the task RUNNING (it can be cancelled).
- **Symlink path case** is untested on this machine (needs Developer Mode or elevation). Junctions, 8.3 names, dot-dot, case and non-ASCII roots are tested. Environment limitation.
- **Secret-looking file names** is a heuristic list, not a secret scanner. A secret inside an ordinary-named file in scope can be read and quoted into a brief.
- **Notes are plain text** in the data root. Do not type credentials into them. Refusing secret-looking note text is undecided.
- **A local actor who can replace files inside the project during a read** is a residual race; the double re-resolve and identity check narrow it.
- **A crash between writing a note, brief or result file and committing its record** leaves an unrecorded file that `doctor` reports, and a gap in brief numbering. Harmless, visible.
- **Single user, single machine.** No multi-user model.
- **Planner is minimal**: fixed action per capability, reads before writes.

## 4. Implementation deviations for Gate 6 decision

These are recorded as facts. The accepted ADR and the implementation are unchanged; RK decides at Gate 6 whether to amend the ADR text or the code.

1. **ADR-0010 D7 event names.** D7 lists the new audit event names `FILE_READ`, `BRIEF_GENERATED`, `RESULT_RECORDED`, `NOTE_RECORDED`. The implementation uses `RESULT_RECORDED` and `NOTE_RECORDED` as separate events. It records file reads (`files_read`, provenance MEDIATED) and the brief (`detail.brief`: path, size, SHA-256) **inside the atomic task-completion transition** (`TASK_TRANSITION`), not as separate `FILE_READ` and `BRIEF_GENERATED` events. The wording is "new event names", which permits but does not require them. Effect: the read, the brief and the task state commit together, with the same hashes and provenance; nothing is lost. Security impact: none identified. Options at Gate 6: (a) amend ADR-0010 D7 to match; (b) add separate events later.
2. **Relative paths in records (added 2026-10-30, release-engineering PR).** Records for notes, briefs and results also carry `rel`, the path under the data root, so a restore to another location verifies. ADR-0010 says the record carries "the path, size and SHA-256"; `rel` is an addition, and the absolute `path` is still recorded. Found by the restore test before any such record existed on the real install.
3. **Excerpts.** ADR-0010 D4 says excerpts are included "only if the task asked for them". The implementation includes the content (within the cap) of every file the task requested with `READ_FILE`; a task that wants only names uses `READ_PROJECT`.
4. **Reads are task steps; no one-shot read command exists.** ADR-0010 D3 allowed a one-shot command that creates an ordinary task; none was built.

## 5. Acceptance status (Beta plan B-01 to B-13)

| ID | Status 2026-10-30 |
|---|---|
| B-01 X-01 to X-16 | automated suite passes (X-16 symlink case is the environment limitation) |
| B-02 fresh-clone full suite | `PLANNED` (Gate 7) |
| B-03 every command runs guarded | `TESTED` |
| B-04 read denial cases | `TESTED` |
| B-05 hostile result inert | `TESTED` |
| B-06 end-to-end workflow | `TESTED` in a temporary install; a real-project run is `PLANNED` before Gate 4 and needs RK's registry and contract |
| B-07 kill at each commit boundary | `TESTED` |
| B-08 doctor healthy / seeded faults | `OBSERVED` healthy on the real install 2026-10-30 (one warning: no registry); seeded faults `TESTED` |
| B-09 backup then restore | `TESTED`; drill on the real install `PLANNED` |
| B-10 clean install runs doctor | `PLANNED` (needs a clean machine or fresh clone) |
| B-11 first audit anchor | `RK DECISION`, scheduled 26 Nov |
| B-12 ruleset unchanged; no ADR amended to ease implementation | `OBSERVED` (ruleset `updated_at` unchanged) |
| B-13 release notes list every limitation | this document, to be finalised at Gate 7 |

## 6. Real-install activation (2026-10-30)

Policy version 2 became the repository's default policy when PR #37 merged. On the real install `doctor` loaded policy version 2, `audit verify` was OK at tail seq 0, and `jarvis.db`, `HEAD`, `jarvis.toml` and `revocations.toml` were byte-identical before and after. The version 2 hash is recorded in the store at the first evaluation. No registry or contract exists yet (RK writes them).
