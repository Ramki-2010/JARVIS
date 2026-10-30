# CP-1 evidence — Phase 1 control plane — 2026-10-30

**Status: NON-AUTHORITATIVE EVIDENCE. NOT A CP-1 DECISION.** This note records what Local Claude checked. It is not independent verification (ADR-0002 D5, verification statement: none is available in Phase 1). CP-1 is decided by RK's review.

**Reviewed:** `main` at `c2d48a7ec11eadf86384e84e984ca348f7b128c4` (merge of PR #26), 2026-10-30, Windows, Python 3.14.7 (`py -3.14`).

**Basis:** ADR-0002 D1, D2, D5 (exit criteria X-01 to X-16 and the test process structure), ADR-0003 D12, ADR-0004, ADR-0005, ADR-0009, and the tests merged on `main`.

## Result

**CP-1: PASS WITH LIMITATION.** No criterion is OPEN. Fifteen criteria are PASS and one (X-16) is PASS WITH ENVIRONMENT LIMITATION. Two limitations are recorded below. The classification is Local Claude's reading of the evidence; RK decides CP-1.

| Class | Count | Criteria |
|---|---|---|
| PASS | 15 | X-01 to X-15 |
| PASS WITH ENVIRONMENT LIMITATION | 1 | X-16 |
| OPEN | 0 | |
| NOT APPLICABLE | 0 | |

## History of this note

An earlier version of this note, written against `main` at `606e711` (merge of PR #24), classified X-13 as OPEN and CP-1 as NOT READY. Its cause was the runtime guard (X-13b) not covering every child in the suite. That version named only the `audit verify` child at `tests/test_child_processes.py:231` as unguarded. **That was incomplete:** the four race children started in the same test (`test_the_chain_verifies_after_the_race`) were also unguarded. PR #26 (tests only) guarded all of them and added guarded runs of the later commands. This version replaces the earlier one in the same file and is based on the merged result. The one-off pre-merge guarded run of 13 commands mentioned in the earlier version was not relied on and is not part of the result below.

## Test run on the merged tip

- Command: `py -3.14 -B -m unittest discover -s tests -t . -v`, run on `main` at the commit above after PR #26 merged (merge commit `c2d48a7ec11eadf86384e84e984ca348f7b128c4`; PR head was `beba2a138011d689b9684fa1644fe0087d55b126`).
- **Ran 252 tests, OK, skipped=1.** 251 passed.
- **Skipped:** `tests.test_canonicalizer.PathTrickTests.test_symlink_into_governance`. Reason given by the test: "cannot create a symlink without elevation or Developer Mode: UNKNOWN". Developer Mode or elevation is not available on this machine, so the test was not run.
- The only change between the earlier reviewed commit and this one is `tests/test_child_processes.py` (+84/−5, PR #26). No production file changed.
- Product code imports only the standard library (`argparse dataclasses datetime enum hashlib json ntpath os re sqlite3 sys tomllib typing`).

## X-01 to X-16

Directly verified means the suite ran the test on the commit above.

| ID | Class | Evidence |
|---|---|---|
| X-01 Capability table | PASS | `test_evaluator.CapabilityTableTests`. The ADR-0003 D12 table text was parsed: 26 rows, and capability, level, verdict and reason match the test table (`tests/policy_d12.py`) with no mismatch. `test_policy.test_rules_equal_adr_0003_d12_table` shows the real `policy/policy.toml` equals that table. The ALLOW set is exactly four. |
| X-02 Default deny | PASS | `test_evaluator.DefaultDenyTests`; `test_tasks_cli` (unknown capability, unclassified target; project with no registry or contract is denied). |
| X-03 No free text | PASS | Golden-file byte-identical test over a fixed grid (`test_evaluator`), repeated with the real policy file (`test_policy`); `test_tasks_cli` shows the objective text never reaches the evaluator. |
| X-04 Audit chain | PASS | `test_store.TamperTests`: altered record, altered with recomputed hash, altered tail, deleted, reordered, truncated tail, and a stable truncation diagnosis across restarts. |
| X-05 Two processes at once | PASS | `test_child_processes`: real `python -m jarvis` children behind a start-line barrier, for the audit-only write and for task creation. Chain linear, no shared predecessor, `audit verify` OK. |
| X-06 Crash at either side of the commit | PASS | `test_child_processes`: child ended before and after `COMMIT`, for the audit-only recovery write and for `task create`. The next run recovers identically. |
| X-07 Restart | PASS | `test_store.test_restart_keeps_state` (reopen) and the child tests, where a later process reads a task written by an earlier one. |
| X-08 Secret-looking environment variable | PASS | `test_config_cli`: configuration equal with and without it. The child harness also passes an allow-listed environment only (`ChildEnvironmentTests`). |
| X-09 Raw path shapes | PASS | `test_canonicalizer.RawInputTests`: 24 shapes (trailing dot or space, reserved names, alternate data stream, UNC, device prefix, relative, drive-relative, others) rejected on the raw string. |
| X-10 Policy change while DEFERRED | PASS | `test_tasks_cli`: policy version bumped while DEFERRED; the next evaluation records the new version and hash. |
| X-11 VERIFIED rejected | PASS | `test_store`: rejected, state unchanged, `TRANSITION_REJECTED` audited. |
| X-12 Constraints never widen | PASS | `test_evaluator` (constraint cases) and `test_tasks_cli`. |
| X-13 No network, subprocess or model in product code | PASS | (a) Static guard: `test_static_guard` and `test_astguard` (alias-resolving syntax scan of every module under `jarvis/`) pass. (b) Runtime guard, now met: every `python -m jarvis` child the suite starts runs under the guard (it is installed and recorded no violation, checked by `assertGuardClean` against the child's marker file), with one deliberate exception, the negative control `test_a_child_without_the_guard_is_not_ended` (`tests/test_child_processes.py:148`), which is the only `run_jarvis` or `spawn_jarvis` call without a marker. Guarded children: `status`, `audit verify` (including the one after the race), the four race children, the crash children, `task create`, `task show`, and, added by PR #26 in `GuardedCommandTests`, `init`, `task evaluate`, `task run`, `report` (task and summary), and the registry and contract loaders (reached through `task evaluate`: an in-scope `READ_FILE` reaches `PHASE_NOT_ENABLED` only if both loaders accepted their files; an invalid contract gives `CONTRACT_INVALID`; a missing registry denies). The guard still ends a child that opens a socket, starts a process, loads ctypes or imports outside the standard library (`test_guard_ends_a_child_that_breaks_the_rules`), and the unguarded negative control still runs to completion. |
| X-14 Zero third-party installs | PASS | `test_static_guard.DependencyTests`: no manifest. Imports listed above are standard library. |
| X-15 Schema completeness | PASS | `test_store.SchemaCompletenessTests`: every section 18 audit field and the provenance block in every record. |
| X-16 Path canonicalisation | PASS WITH ENVIRONMENT LIMITATION | `test_canonicalizer.PathTrickTests`: dot-dot, junctions (into a secret location, out of a project, a protected root that is itself a junction), 8.3 names, case, non-ASCII roots all pass. **The symlink case is skipped on this machine** (needs Developer Mode or elevation) and is therefore unverified here. |

## Limitations (preserved)

- **X-16 symlink case:** unverified on this machine (above). It would be closed by running the suite with Developer Mode or elevation.
- **RUNNING-task re-evaluation is not implemented.** ADR-0002 D2 describes re-evaluation of a RUNNING task when the policy version changes (marked PROPOSED, to be confirmed by RK). The state table has no `RUNNING` to `BLOCKED` or `DEFERRED` edge, so there is nothing to apply it to.
- **Crash recovery of `task run` is not tested.** X-06 covers the audit-only write and `task create`, which share the same commit path; `task run` is covered by the runtime guard and by in-process tests only.
- **Plan steps `LIST_REGISTRY` and `SHOW_CONTROL_PLANE_CONFIG` are recorded no-ops.** Only `WRITE_REPORT` has a side effect.
- **No independent verifier.** Every task ends `NOT_VERIFIED`; `VERIFIED` is unreachable.
- The registry and contract file formats are Phase 1 engineering choices (schema 1). The `revocations.toml` format was accepted by RK on 2026-10-30. No registry or contract file exists.

## Operational store and configuration (read-only, re-checked on the merged tip)

- `D:\JARVIS\data` holds `jarvis.db` and `HEAD` only. `py -3.14 -m jarvis audit verify`: OK, tail sequence 0, tail hash `93c36dec…5b3a`. `status`: initialized, halted no, findings none, tasks none.
- SHA-256 prefixes of the four operational files, taken before and after this re-run and compared with the first review, are identical, including `jarvis.db` and `HEAD`. The review changed no operational data.
- `jarvis.toml` loads with the merged loader. `data_root` is `D:\JARVIS\data`, `governance_zone` is `D:\JARVIS\governance`, and `user_home` exists. All three directories exist and agree with ADR-0007 and the `status` output.
- `revocations.toml` loads as a valid empty list (schema 1, three empty lists).
- No `registry.toml` exists (`REGISTRY_MISSING`); project-scoped targets are therefore denied. This is expected.
- The ruleset `protect-main` `updated_at` is unchanged (`2026-10-11T23:37:01.214+05:30`) and `phase-0-freeze` still resolves to `e919b7a`.
- No audit anchor was created, and the `gh` credential-access decision (ADR-0009 section 10) is untouched.

## What this review did not do

No independent verification. No broad audit beyond the criteria. No change to ADRs, policy, governance configuration, rulesets, production code, or registry and contract files. The first audit anchor and the `gh` credential decision remain open for RK.
