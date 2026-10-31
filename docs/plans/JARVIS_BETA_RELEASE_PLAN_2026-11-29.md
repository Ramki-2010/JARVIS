# JARVIS Beta Release Plan — target 2026-11-29

**Status:** PROPOSED. NON-AUTHORITATIVE until RK merges it (ADR-0001 D6). Not an ADR. Documentation only.
**Drafted:** 2026-10-30, by Local Claude, from RK's instruction of the same day.
**Baseline:** `main` at the merge of PR #25 (CP-1 evidence). CP-1: PASS WITH LIMITATION (`docs/environment/CP-1-phase-1-evidence-2026-10-30.md`).
**Classification (ADR-0001 D7):** matched triggers **G-15** (it fixes what ships and in what order) and **G-17** (it states that the Beta does not meet the Master Context section 31 acceptance test). No accepted ADR is amended. This block is a claim by the drafting session; RK's merge confirms or corrects it.

**Amendment 1 (PROPOSED, 2026-10-31).** RK instructed in chat that the Beta also include a functional dashboard minimum, a live status ring, a read-only galaxy, push-to-talk voice, 25 intent families and, if time allows, a local-model advisory demo (see section 11). This edits sections 3.3 and 7 and adds section 11. Matched triggers: **G-15**. It does not take effect until RK merges it. It depends on MCA-002 (Master Context), ADR-0011, ADR-0012 and ADR-0013 (optional), none of which is in force until RK merges its acceptance. Core criteria B-01 to B-13 and the dates of Gates 1 to 8 are unchanged. **Cut rule: scope is cut, never acceptance criteria.**

**Labels:** `IMPLEMENTED` (in `main`, with tests) · `OBSERVED` (seen locally, with the source named) · `INFERRED` (follows from documents, not run) · `PLANNED` · `UNKNOWN` · `RK DECISION`.

---

## 1. The honest starting point

| Fact | Label | Source |
|---|---|---|
| JARVIS today is a deterministic control plane: configuration, registry and contract loaders, evaluator, hash-chained audit store, task lifecycle, reports, a stub planner, a CLI of 10 commands. | `IMPLEMENTED` | `jarvis/` (2588 lines), CP-1 evidence |
| 252 tests pass, 1 is skipped (symlink case, needs Developer Mode). | `OBSERVED` 2026-10-30 | full suite on `c2d48a7` |
| Only four capabilities are ALLOWED: `CREATE_TASK`, `CREATE_REPORT`, `READ_REGISTRY`, `READ_CONTROL_PLANE_CONFIG`. All record-keeping. | `IMPLEMENTED` | `policy/policy.toml`, ADR-0003 |
| `READ_PROJECT`, `READ_FILE`, `GENERATE_WORKER_BRIEF` exist and DEFER with `PHASE_NOT_ENABLED`. | `IMPLEMENTED` | `policy/policy.toml` |
| Network, subprocess, worker execution and any model call are DEFERRED until Phase 3 isolation. Approval records are forgeable before isolation. | `IMPLEMENTED` as policy | ADR-0002 D4, MCA-001 |
| No real registry file and no real contract file exist. RK writes them. | `OBSERVED` | `D:\JARVIS\governance\` |
| The real store is initialized; audit tail seq 0; no audit anchor yet. | `OBSERVED` | CP-1 evidence |

**What this means.** JARVIS can record, evaluate and report on tasks. It cannot yet read a project, produce a brief, remember anything beyond task records, or help with real work. The Beta has to close exactly that gap, and nothing wider.

## 2. The scope conflict, stated now

The Master Context (section 30, as amended by MCA-001) puts these behind **Phase 3 Local Isolation**: any network access, research, subprocess, test or experiment run, worker execution, and any model call. Phase 3 is an OS-level boundary that must be designed (its own ADR), built and attested. That alone would consume the 30 days, with a real chance of not finishing.

Therefore the requested gates "useful capability set" (19 Nov) and "end-to-end usable path" (23 Nov) **cannot be met with autonomous capabilities** without either breaking accepted ADRs or skipping isolation. This plan does neither. It recommends **scope reduction**:

> **Beta = JARVIS as a governed project assistant that works with RK, not for RK.** It knows the projects, holds context across sessions, reads project files inside a contract scope, writes bounded task briefs, takes the relayed results back as untrusted input, and reports honestly. RK runs the worker. This is Master Context Phase 2 (Manual Worker Bridge) plus the memory v0.1 slice needed to make it useful.

Consequence stated plainly: **the Beta does not meet the Master Context section 31 first acceptance test** (it does no research, sandboxing or experiments). It is a Beta of the control plane and bridge, not "v0.1 complete". Master Context section 37 (Definition of Done) is untouched.

`RK DECISION` D-1: accept this reduction, or choose the alternative in section 9.

## 3. Beta scope

### 3.1 Beta-required (release does not ship without these)

| ID | Capability | Notes |
|---|---|---|
| BR-1 | **Project context.** `project list/show`: the registered projects, their roots and contract scope, read-only. | Uses `READ_REGISTRY`, already allowed. |
| BR-2 | **Bounded project reading.** `file read` / `project read`: read a file or list a directory inside a contract scope, with a size cap and truncation marking; refused in the governance zone, data root, JARVIS tree and user-secret locations (ADR-0008), and for secret-looking file names (ADR-0010 D3). | Needs `READ_FILE`/`READ_PROJECT` enabled: ADR-0010 and a policy change by RK (G-03). Reuses the canonicalizer (X-09, X-16). |
| BR-3 | **Task briefs.** `brief generate <task>`: a deterministic, size-bounded brief written to the data root, hashed, audited. | `GENERATE_WORKER_BRIEF`. Brief rules are decided by ADR-0010 (G-14). |
| BR-4 | **Relayed results.** `result add <task> --file`: store a result RK relays from a worker, labelled UNTRUSTED, hashed, never parsed for instructions, never executed. Task stays `COMPLETED_UNVERIFIED`; `VERIFIED` stays unreachable. | ADR-0010. |
| BR-5 | **Persistent context.** `note add/list/show` per project and task, with provenance class (who wrote it, from what). `resume`: a plain summary of open tasks, latest notes and audit state, to start a session cold. | Layout of `memory/` is `UNKNOWN` today (ADR-0007); ADR-0010 decides the minimal layout. Written through the audit chain. |
| BR-6 | **Reliability.** A killed `task run` leaves a verifiable chain and a task that can be re-run or failed explicitly. Clear exit codes and messages for every failure. | Closes the "crash recovery of `task run` untested" CP-1 limitation to the extent Beta needs. |
| BR-7 | **`doctor`.** One read-only command: Python version, config, policy, governance files, registry and contracts load, store and audit chain verify, free disk. | Plain-language pass/fail. |
| BR-8 | **Install, run, back up.** A pinned launcher (`py -3.14`), a written bootstrap, and a tested backup and restore procedure for `D:\JARVIS\`. | Backup is an open item in ADR-0009. |
| BR-9 | **Guards stay.** X-13 (no network, subprocess, model in product code) still passes with every new module; new commands run under the child guard. | The Beta adds no execution surface. |
| BR-10 | **Beta documentation and acceptance suite.** README quickstart, limits and security notes, release notes; one scripted end-to-end acceptance test that follows the real path. | |
| BR-11 | **First audit anchor** made by RK under ADR-0009. | RK act. |

### 3.2 Beta-supporting (ship if on time; dropping one never blocks the release)

| ID | Item |
|---|---|
| BS-1 | Persona phrasing layer for CLI output: dry, British, "sir", with the wit dial off for approvals, risk, credentials and records. Presentation only, in its own module, never reading governance state beyond what the CLI already prints. Phrasebook from the architecture draft, original lines only. |
| BS-2 | `status --json` / `doctor --json` for scripting. |
| BS-3 | Static, read-only HTML rendering of a report (no server, no script). |
| BS-4 | A `planner` improvement limited to mapping a few more plain verbs to capabilities (deterministic). |

### 3.3 Post-Beta (with rationale)

| Item | Why it is not in the Beta |
|---|---|
| Phase 3 Local Isolation | Needs its own ADR, an OS boundary, attestation. Cannot be done in the window alongside the rest. Unblocks everything below. |
| Controlled coding, tests, experiments (Phase 4) | Subprocess. Behind isolation. |
| Web research and R&D (Phase 5) | Network. Behind isolation. |
| Any model call, local or online; the local/online switch | No accepted ADR; needs a local server or network (a socket) and, online, G-05, G-06, G-07, G-08. See the character, voice and model-switch note. |
| Wake word, always-listening, barge-in, mobile, finished dashboard (Phase 7) | Later phases. **Amendment 1:** push-to-talk voice, the status ring, the galaxy and the Beta dashboard minimum are now Beta-supporting items (section 11), not post-Beta. |
| Phone calling, decision-call idea | v0.1 non-goal; `MAKE_CALL` is DENY. |
| Scheduler and background autonomy (Phase 6) | `pause`/`resume`/`stop` semantics and isolation. |
| Approval engine for L4 | Forgeable before isolation (ADR-0002). |
| Independent verifier; `VERIFIED` state | Needs a trust boundary that does not exist. Everything stays `NOT_VERIFIED`. |
| RUNNING-task re-evaluation (no RUNNING to BLOCKED/DEFERRED edge) | State-machine redesign. Beta has no long-running step, so the window for a policy change mid-run is empty. |
| Symlink test limitation | Environment (Developer Mode). Junction and other path cases pass. Revisit if the Beta host changes. |
| Registry/config editing UX | RK writes TOML by hand in the governance zone. Deliberate. |
| Full Knowledge Galaxy (typed relationships, memory graph), rich memory | Later. **Amendment 1:** a read-only galaxy over real records is Beta-supporting (section 11). Beta memory stays plain notes. |
| Advanced planner, broad capability expansion, refactors | No Beta requirement. |

### 3.4 Release-blocking unknowns

| ID | Unknown | Resolve by | Owner |
|---|---|---|---|
| U-1 | RK accepts the reduced scope (D-1). Without it the whole schedule is conditional. | 1 Nov | RK |
| U-2 | RK accepts ADR-0010 (bridge, reading, memory layout). Blocks BR-2 to BR-5. | 3 Nov | RK |
| U-3 | RK merges the policy change enabling the DEFERRED capabilities (G-03). | 5 Nov | RK |
| U-4 | RK writes the first real registry and contract files (G-04, G-09). The end-to-end path needs a real project. | 8 Nov | RK |
| U-5 | Memory storage choice: new tables in the existing store vs. files. A store schema change touches ADR-0005; the ADR must show it needs no audit-model change. | with ADR-0010 | Local Claude proposes, RK decides |
| U-6 | `gh` credential-access decision (ADR-0001 section 10; G-07, G-12). Not needed to ship, but the anchor's independence claim is weaker until RK decides or knowingly defers. | 20 Nov | RK |
| U-7 | Where backups of `D:\JARVIS\` are kept (a second drive or cloud is a G-06/G-08 question). | 20 Nov | RK |
| U-8 | Is a model-free Beta useful enough for RK's own daily use? Only RK can judge. | 19 Nov (demo) | RK |
| U-9 | The Python on `PATH` is 3.10.11; JARVIS needs 3.14 via `py -3.14`. A clean-machine install is `UNKNOWN`. | 26 Nov | Local Claude |

## 4. Beta acceptance criteria

The Beta ships when all hold, each with evidence recorded in a Beta evidence note (same style as CP-1). A criterion not run is NOT VERIFIED, not passed.

| ID | Criterion |
|---|---|
| B-01 | CP-1 criteria X-01 to X-16 still pass (X-16 symlink case stays an environment limitation). |
| B-02 | The full suite passes on a fresh clone of the release candidate. |
| B-03 | Every new command runs as a real child under the runtime guard (X-13b) and records no violation. |
| B-04 | The new reading capability denies: `..` escape, junction escape, the governance zone, a user-secret location, a secret-looking file name, an over-size file (truncated and marked), a path in another project's scope. |
| B-05 | A relayed result containing text that looks like instructions, a command or a task is stored as data and changes nothing. |
| B-06 | The scripted end-to-end path passes: register project, create task, evaluate, read file, generate brief, add relayed result, add note, report, resume, `audit verify`. |
| B-07 | Killing `task run` at each commit boundary leaves a chain that verifies and a task in a defined state. |
| B-08 | `doctor` reports healthy on the real machine and reports a seeded fault (missing revocations file; broken contract) as a failure. |
| B-09 | Backup then restore of a copy of `D:\JARVIS\` yields a store whose `audit verify` passes and whose HEAD matches. |
| B-10 | A clean install from the written bootstrap runs `doctor` successfully. |
| B-11 | First audit anchor exists on `main` through the ADR-0009 path. |
| B-12 | Ruleset `protect-main` unchanged; no ADR amended to ease implementation; no governance file modified by a JARVIS command. |
| B-13 | Release notes list every known limitation in this plan, including that the Beta does not meet section 31. |

## 5. The 30-day roadmap

Owners: **LC** = Local Claude (implements, tests, opens PRs). **CC** = Cloud Claude (optional architectural review). **RK** = decides and merges. "RK-gated" means the PR changes governance and only RK's merge makes it effective; it is never merged by a session.

| Window | Workstream | Deliverable | Depends on | Acceptance | Release risk | Owner | PR boundary |
|---|---|---|---|---|---|---|---|
| 30 Oct–1 Nov | Release control | This plan; scope frozen on merge | CP-1 merged (done) | RK merges; sections 3 and 4 are the frozen scope | Medium: RK latency | LC drafts, RK merges | **PR-1** docs only, RK-gated |
| 30 Oct–3 Nov | Release control / architecture | **ADR-0010**: Phase 2 bridge. Brief rules; reading rules; relayed-result rules; minimal `memory/` layout; new capabilities if any | PR-1 direction | ADR PROPOSED with options and an `UNKNOWN` list; RK accepts by merge | **High**: RK decision on the critical path | LC drafts, CC reviews if asked, RK decides | **PR-2** docs only, RK-gated (G-03, G-14, G-15, G-06) |
| 1–3 Nov | Core reliability | `doctor` (BR-7) | none | B-08 seeded-fault cases pass; read-only | Low | LC | **PR-3** code + tests |
| 3–6 Nov | Core reliability | Crash behaviour of `task run` (BR-6): tests at each commit boundary; defined recovery; error messages reviewed | PR-3 helps | B-07 | Medium: touches the store path | LC | **PR-4** tests + small fix |
| 3–5 Nov | Governance | Policy version 2: enable `READ_PROJECT`, `READ_FILE`, `GENERATE_WORKER_BRIEF`, and any capability ADR-0010 adds | PR-2 merged | Table-driven tests (X-01 style) updated; policy hash recorded; RK merges | **High**: RK latency | LC drafts, RK merges | **PR-5** policy + tests, RK-gated (G-03) |
| 4–7 Nov | Core reliability | `project list/show` (BR-1) | none | Read-only, uses `READ_REGISTRY`; child-guard test | Low | LC | **PR-6** |
| **7 Nov** | **Gate 2** | Core runtime reliability baseline | PR-3, PR-4, PR-6 | doctor + crash tests + guard tests green | | | |
| 6–10 Nov | Persistent context | Memory layout and `note add/list/show` with provenance class (BR-5, part 1) | PR-2 (layout), U-5 | Notes are audited; round trip survives restart; no note content goes into the audit chain beyond its hash and length | **High**: possible store-schema change | LC | **PR-7** |
| 10–13 Nov | Persistent context | `resume` (BR-5, part 2); session continuity | PR-7 | Cold start prints open tasks, latest notes, audit tail; contains no secret | Medium | LC | **PR-8** |
| 8 Nov | RK action | First real registry and contract files for one project | RK | Files load; `doctor` healthy | Medium: RK | RK | none (operational) |
| **13 Nov** | **Gate 3** | Persistent context baseline | PR-7, PR-8 | B-05-style data-only tests for notes; restart test | | | |
| 12–16 Nov | Capability | Bounded reading (BR-2) | PR-5 merged | B-04 | **High**: path handling is the product's sharpest edge; reuse the canonicalizer only | LC | **PR-9** |
| 15–18 Nov | Capability | `brief generate` (BR-3) | PR-5, PR-9 | Deterministic: same inputs, byte-identical brief; size bounded; hashed; audited | Medium | LC | **PR-10** |
| 17–19 Nov | Capability | `result add` (BR-4) | PR-10 | B-05 | Medium | LC | **PR-11** |
| **19 Nov** | **Gate 4** | Initial useful capability set; demo to RK (U-8) | PR-9, PR-10, PR-11 | RK can read, brief, relay and note on the real project | | | |
| 19–22 Nov | Interaction (supporting) | Persona phrasing layer (BS-1), `--json` (BS-2) | none | Wit dial off for risk and records; no governance logic in the module; golden-file tests | Low: droppable | LC | **PR-12** |
| 20–23 Nov | End to end | Scripted acceptance test of the whole path (B-06); fix what it finds | Gate 4 | B-06 green from a clean data root | Medium: integration defects | LC | **PR-13** |
| **23 Nov** | **Gate 5** | End-to-end usable JARVIS path | PR-13 | RK runs the path by hand once | | | |
| 22–25 Nov | Release engineering | Launcher, bootstrap, backup and restore procedure and drill, release procedure | U-7 | B-09, B-10 | Medium: clean-machine unknown (U-9) | LC | **PR-14** |
| 23–26 Nov | Security validation | Focused review: new reading and intake code, injection tests, guard coverage of every new module, secret-location tests; a code-review pass | Gate 5 | B-03, B-04, B-05, B-12; findings fixed or listed | **High**: late finding | LC (review by a fresh session), CC if asked | **PR-15** fixes |
| 24–26 Nov | RK action | First audit anchor (BR-11); decide or defer U-6 | ADR-0009 | B-11 | Medium: RK | RK | anchor PR by RK |
| **26 Nov** | **Gate 6** | Security, integration and release validation | PR-14, PR-15 | B-01 to B-12 evidence drafted | | | |
| 26–28 Nov | Release | Beta evidence note; documentation; release notes (B-13); release candidate branch; final full-suite run on a fresh clone | Gate 6 | B-02, B-13 | Medium | LC | **PR-16** docs |
| **28 Nov** | **Gate 7** | Release candidate frozen | PR-16 | Only blocker fixes after this point; each is a PR | | | |
| **29 Nov** | **Gate 8** | **Beta release**: tag, release notes | Gate 7, RK's explicit instruction | RK merges and tags; `main` equals the candidate | | RK | release PR, RK-gated |

**Slack.** Gate dates are fixed. Slack comes only from dropping BS items and from RK responding quickly. The two items with no slack are **PR-2 acceptance (3 Nov)** and **PR-9 (bounded reading)**. If PR-2 is not accepted by 5 Nov, BR-2 to BR-5 are re-planned that day and the Beta is cut to BR-1, BR-6 to BR-10: a hardened control plane with project context and `doctor`. That is the fallback, not the plan.

## 6. Release gates

| Gate | Date | Pass condition |
|---|---|---|
| 1 | 1 Nov | CP-1 merged (done 30 Oct). This plan merged by RK, which freezes sections 3 and 4. |
| 2 | 7 Nov | `doctor`, crash tests and `project show` merged; suite green; X-13 guard green. |
| 3 | 13 Nov | ADR-0010 and policy v2 accepted; notes and `resume` merged; restart test green. |
| 4 | 19 Nov | Reading, briefs and relayed results merged; RK has used them on one real project. |
| 5 | 23 Nov | B-06 end-to-end test green; RK ran the path by hand. |
| 6 | 26 Nov | Security review done; B-01 to B-12 have recorded evidence; anchor made. |
| 7 | 28 Nov | Release candidate frozen; fresh-clone run passes. |
| 8 | 29 Nov | Beta tagged on RK's instruction. |

A missed gate is reported the same day with the cut proposed. The date is not extended silently.

## 7. Current release risks

| # | Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|---|
| 1 | RK review latency on RK-gated PRs (PR-1, PR-2, PR-5) | High | Moves every later gate | Small PRs; the decision asked is stated in the first lines; fallback scope in section 5 |
| 2 | Bounded reading opens a path-escape or secret-leak | Medium | A security defect in the only new read surface | Reuse the canonicalizer; deny-first tests (B-04); fresh-session review (PR-15) |
| 3 | Memory needs a store schema change | Medium | Touches the audit model (ADR-0005, G-11) | ADR-0010 must show no audit semantics change, or choose files |
| 4 | A model-free Beta is judged not useful | Medium | Release feels thin | Demo at Gate 4 (U-8); the value is context, briefs and honest records, stated in the release notes |
| 5 | Clean-machine install behaves differently (Python 3.14, paths) | Medium | B-10 fails late | Bootstrap and a clean-clone run in PR-14, not at the end |
| 6 | One Local Claude session carries all code PRs | Medium | Serial bottleneck | PRs are small and independent where possible (PR-3, PR-6, PR-12 can run in any order) |
| 7 | Audit independence is procedural only (ADR-0009) until U-6 | Known | A claim in the release notes must be precise | Say so in B-13; do not claim tamper-proof |
| 8 | Scope pressure to add a model, voice or UI | High | Eats the schedule | **Amendment 1 is that RK-accepted edit** (section 11). It adds scope behind a cut line; core gates keep priority, and voice and the local-model demo are the first cut |

## 8. Highest-priority next work item

**ADR-0010, the Phase 2 Manual Worker Bridge decision (PR-2).** It is on the critical path of BR-2 to BR-5, which are most of what makes the Beta useful, and it needs the longest human lead time (RK's decision). `doctor` (PR-3) proceeds in parallel because it needs no decision.

## 9. Decisions that need RK

| ID | Decision | By | Recommended |
|---|---|---|---|
| D-1 | Accept the reduced Beta scope (section 2), or the alternative: spend the month on Phase 3 isolation and ship a Beta with a sandboxed run capability but without project reading, briefs or memory | 1 Nov | Reduced scope. Isolation cannot be built, attested and then used in 30 days. |
| D-2 | Accept ADR-0010 | 3 Nov | After review. |
| D-3 | Merge the policy change (PR-5) | 5 Nov | After review. |
| D-4 | Write the first real registry and contract (RK writes; sessions do not) | 8 Nov | Choose a low-risk project first. |
| D-5 | Backup location | 20 Nov | A second local drive. Cloud would be a G-06/G-08 decision. |
| D-6 | `gh` credential-access: decide or knowingly defer | 20 Nov | Decide before the anchor. |
| D-7 | Make the first audit anchor | 26 Nov | |
| D-8 | Final release instruction | 29 Nov | |

## 10. What this plan does not do

It creates no operational file, changes no policy, ADR, ruleset or governance file, starts no phase, and builds nothing. It does not claim the Beta is v0.1. Dates after Gate 1 are targets, not facts, and are re-planned at each gate.

## 11. Amendment 1 (PROPOSED): interaction surfaces in the Beta

**Principle: strict authority, flexible interaction, controlled exposure.** No interface, voice command or model grants authority; policy decides. The interface itself is not artificially limited.

### 11.1 New Beta-supporting items (droppable in the order given in 11.4)

| ID | Item | Governing record |
|---|---|---|
| BS-5 | **Beta dashboard** (functional minimum): status, health, projects, tasks, notes, results, recent activity, audit and backup status, errors, blocked, deferred and cancelled work. Read-only first (Stage A), then a short whitelist of writes (Stage B: task create, note add, cancel), each an existing CLI command | MCA-002, ADR-0011 |
| BS-6 | **Status ring** driven by real state only | ADR-0011 |
| BS-7 | **Galaxy**, read-only, canvas, real records; future capabilities only as labelled PREVIEW, DEFERRED or BLOCKED nodes | MCA-002, ADR-0011 |
| BS-8 | **Intent layer**, 25 intent families, deterministic, clarify-on-doubt, persona wording that never changes meaning | ADR-0011 |
| BS-9 | **Push-to-talk voice**, local speech in and out, private profile only | MCA-002, ADR-0012 |
| BS-10 | **Local-model advisory demo** (optional): approved list, advisory and untrusted output, separate process | ADR-0013 |

### 11.2 Acceptance for the new items (they do not replace B-01 to B-13)

An item that is cut has no acceptance duty. An item that ships must meet its rows.

| ID | Criterion |
|---|---|
| BU-1 | UI server tests pass: only `127.0.0.1`, random port, token required (and never replaced by Origin), `Host` and `Origin` accepted only as exactly `http://127.0.0.1:<port>` or `http://localhost:<port>`, `Origin` required on every Stage B mutation, wrong or absent Origin or wrong Host rejected, no CORS, strict CSP, no outbound connection, Stage A has no write route. POST bodies have a strict size limit and an exact field whitelist per route; unexpected, duplicate or missing fields are rejected. |
| BU-1b | The child-process helper uses an absolute Python 3.14 interpreter path (not resolved through `PATH`), `-I -m jarvis`, an argument list, never a shell; a static test fails on `shell=True` or a bare interpreter name. |
| BU-2 | The static guard shows `jarvis/` has no subprocess or network import; `ui/` starts only `python -m jarvis`; `voice/` has no network. |
| BU-3 | Every LIVE galaxy node and relationship traces to real source data; PREVIEW, DEFERRED and BLOCKED nodes are labelled and never counted as records or activity; the ring state equals the record state. |
| BU-4 | Cross-surface equivalence: the same request through CLI, UI and voice resolves to the same intent and command. Intent harness results are reported as measured, with no target invented in advance. |
| BU-5 | Voice: push-to-talk only, mic closed during speech, no audio written by default, no outbound connection, no external-communication adapter exists, voice profile record present with hash and provenance status. |
| BU-6 | Local model (if shipped): output stored as untrusted data and never read by planning, authorization or briefs. |
| B-13 (extended) | Release notes also list the limitations of these items and state that the Beta dashboard is the minimum and Phase 7 completes it. |

### 11.3 Schedule (targets; Gates 1 to 8 are unchanged)

| Window | Deliverable | Cut line |
|---|---|---|
| 1-3 Nov | MCA-002, this amendment, ADR-0011, ADR-0012, ADR-0013 drafted; RK decides | RK latency is the risk |
| 3-7 Nov | Spikes with no product code: speech tool licence, network behaviour, Python 3.14 compatibility; canvas frame-rate measurement | |
| 4-10 Nov | Dashboard views and status data (Stage A), then the ring | |
| 8-15 Nov | Intent layer and measurement harness | |
| 12-18 Nov | Galaxy | **14 Nov: UI cut line** |
| 14-19 Nov | Stage B writes; local-model demo if ADR-0013 accepted | |
| 10-19 Nov | Voice in, then voice out | **19 Nov: voice cut line** |
| 19-24 Nov | Cross-surface equivalence, security review of `ui/` and `voice/` | |

The core path (Gates 2 to 8) keeps priority. A missed cut line is reported the same day, with the cut proposed. The date is not extended silently.

### 11.4 Cut order if time runs short

1. Local-model demo (BS-10). 2. Voice output, then voice input (BS-9). 3. Stage B writes. 4. Galaxy (BS-7). 5. Ring (BS-6). The Beta dashboard minimum (BS-5, Stage A) is the last to go. The static, read-only HTML report (BS-3) is the fallback if the UI server ADR is not accepted.

### 11.5 Still excluded from the Beta

Wake word, always-listening, barge-in, phone calling, external communication, cloud speech, LAN access, direct GitHub access (manual human transfer only), unrestricted computer control, autonomous execution, any model holding authority, mobile UI.

### 11.6 Decisions that need RK

| ID | Decision |
|---|---|
| D-9 | Merge MCA-002 (accept) |
| D-10 | Merge this amendment |
| D-11 | Accept ADR-0011 and ADR-0012; ADR-0013 optional |
| D-12 | Whether RESUME may reopen a terminal task. It needs a new state edge (ADR-0002 amendment); without it RESUME re-evaluates and reports only |
| D-13 | Firewall rule to block outbound traffic for the voice runtime (G-05, RK's act) |
| D-14 | Install the speech tool from a pinned release with checked hashes (G-13, RK's act) |
| D-15 | Where the voice asset and model files live under `D:\JARVIS` (ADR-0007) |
