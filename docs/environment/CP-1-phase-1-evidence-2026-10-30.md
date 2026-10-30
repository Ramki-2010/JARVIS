# CP-1 evidence — Phase 1 control plane — 2026-10-30

**Status: NON-AUTHORITATIVE EVIDENCE. NOT A CP-1 DECISION.** This note records what Local Claude checked. It is not independent verification (ADR-0002 D5, verification statement: none is available in Phase 1). CP-1 is decided by RK's review.

**Reviewed:** `main` at `606e7119d217a7704cda005b765ce53eedfb1408` (merge of PR #24), 2026-10-30, Windows, Python 3.14.7 (`py -3.14`).

**Basis:** ADR-0002 D1, D2, D5 (exit criteria X-01 to X-16 and the test process structure), ADR-0003 D12, ADR-0004, ADR-0005, ADR-0009, and the tests merged on `main`.

## Result

**CP-1: NOT READY.** One required criterion is OPEN: X-13 part (b), the runtime guard. Fifteen of sixteen criteria are PASS or PASS WITH ENVIRONMENT LIMITATION. The blocker is in the tests, not in product code, and the remedy is small (see "Blockers").

| Class | Count | Criteria |
|---|---|---|
| PASS | 14 | X-01 to X-12, X-14, X-15 |
| PASS WITH ENVIRONMENT LIMITATION | 1 | X-16 |
| OPEN | 1 | X-13 |
| NOT APPLICABLE | 0 | |

## Test run on the merged tip

- Command: `py -3.14 -B -m unittest discover -s tests -t . -v`, run on `main` at the commit above after a fast-forward pull. Not carried over from the earlier 249-test run on the PR branch.
- **Ran 249 tests, OK, skipped=1.** 248 passed.
- **Skipped:** `tests.test_canonicalizer.PathTrickTests.test_symlink_into_governance`. Reason given by the test: "cannot create a symlink without elevation or Developer Mode: UNKNOWN".
- Product code imports only the standard library (`argparse dataclasses datetime enum hashlib json ntpath os re sqlite3 sys tomllib typing`).

## X-01 to X-16

Directly verified means the suite ran the test on the commit above.

| ID | Class | Evidence |
|---|---|---|
| X-01 Capability table | PASS | `test_evaluator.CapabilityTableTests`. I also parsed the ADR-0003 D12 table text: 26 rows, and capability, level, verdict and reason match the test table (`tests/policy_d12.py`) with no mismatch. `test_policy.test_rules_equal_adr_0003_d12_table` shows the real `policy/policy.toml` equals that table. The ALLOW set is exactly four. |
| X-02 Default deny | PASS | `test_evaluator.DefaultDenyTests`; `test_tasks_cli` (unknown capability, unclassified target, project with no registry or contract denied). |
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
| X-13 No network, subprocess or model in product code | **OPEN** | (a) Static guard PASS: `test_static_guard` and `test_astguard` (alias-resolving syntax scan of `jarvis/`, including the modules added by PRs #22 to #24). (b) Runtime guard: the guard is installed and proven to end a child on a violation (`test_child_processes`), and the X-05 and X-06 children run under it. **But the suite does not meet "every `python -m jarvis` child runs under the guard":** the `audit verify` child at `tests/test_child_processes.py:231` runs without it, and no suite test runs `init`, `task evaluate`, `task run`, `report` or the registry and contract loaders in a guarded child. The one other unguarded child (`:141`) is the deliberate negative control. See "Blockers". |
| X-14 Zero third-party installs | PASS | `test_static_guard.DependencyTests`: no manifest. Imports listed above are standard library. |
| X-15 Schema completeness | PASS | `test_store.SchemaCompletenessTests`: every section 18 audit field and the provenance block in every record. |
| X-16 Path canonicalisation | PASS WITH ENVIRONMENT LIMITATION | `test_canonicalizer.PathTrickTests`: dot-dot, junctions (into a secret location, out of a project, a protected root that is itself a junction), 8.3 names, case, non-ASCII roots all pass. **The symlink case is skipped on this machine** (needs Developer Mode or elevation) and is therefore unverified here. |

## Blockers

1. **X-13(b) OPEN.** Directly observed gap in the suite, not a product-code failure.
   - What would close it, in a tests-only change: run the `audit verify` child at `:231` with a guard marker, and add guarded-child runs for `init`, `task evaluate`, `task run`, `report` and a project-path evaluation that loads a registry and contract.
   - Supplementary evidence, not repeatable from the repository: on 2026-10-30 I ran 13 commands once from a script outside the repository, each as a child with the guard marker set, in temporary directories (`init`, two `task create`, two `task evaluate` including one loading a registry and a contract, `task run`, `report` twice, `task show`, `task list`, `audit verify`, `status`, `cancel`). All exited 0 and none recorded a violation. This does not replace a suite test.
   - I made no change to tests or code in this review.

## Known limitations (preserved, evidence unchanged)

- **X-16 symlink case:** unverified on this machine (above).
- **RUNNING-task re-evaluation is not implemented.** ADR-0002 D2 describes re-evaluation of a RUNNING task when the policy version changes (marked PROPOSED, to be confirmed by RK). The state table has no `RUNNING` to `BLOCKED` or `DEFERRED` edge, so there is nothing to apply it to.
- **Plan steps `LIST_REGISTRY` and `SHOW_CONTROL_PLANE_CONFIG` are recorded no-ops.** Only `WRITE_REPORT` has a side effect.
- **No independent verifier.** Every task ends `NOT_VERIFIED`; `VERIFIED` is unreachable.
- The registry and contract file formats and the `revocations.toml` format are Phase 1 engineering choices (schema 1). `revocations.toml` was accepted by RK on 2026-10-30. No registry or contract file exists.

## Operational store and configuration (read-only)

- `D:\JARVIS\data` holds `jarvis.db` and `HEAD` only. `py -3.14 -m jarvis audit verify`: OK, tail sequence 0, tail hash `93c36dec…5b3a`. `status`: initialized, halted no, findings none, tasks none.
- SHA-256 prefixes of the four operational files, taken before and after this review, are identical, including `jarvis.db` and `HEAD`. The review changed no operational data.
- `jarvis.toml` loads with the merged loader. `data_root` is `D:\JARVIS\data`, `governance_zone` is `D:\JARVIS\governance`, and `user_home` exists. All three directories exist and agree with ADR-0007 and the `status` output.
- `revocations.toml` loads as a valid empty list (schema 1, three empty lists).
- No `registry.toml` exists (`REGISTRY_MISSING`); project-scoped targets are therefore denied. This is expected.
- No audit anchor was created, and the `gh` credential-access decision (ADR-0009 section 10) is untouched.

## What this review did not do

No independent verification. No broad audit beyond the criteria. No change to ADRs, policy, governance configuration, rulesets, implementation code, tests, or registry and contract files. The first audit anchor and the `gh` credential decision remain open for RK.
