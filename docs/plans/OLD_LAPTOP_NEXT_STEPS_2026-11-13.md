# Old laptop: what is needed next (2026-11-13)

**Status: PLAN NOTE, NON-AUTHORITATIVE until RK merges it.** It grants no authority and decides nothing. Where it conflicts with an accepted record or RK's chat word, the record wins. It supersedes the benchmark purpose of `TEMP_HANDOFF_OLD_LAPTOP_BENCHMARK_2026-11-01.md` (that note stays, with an update line, until RK's cleanup).

## 1. What changed

RK decided on 2026-11-13 that the **new laptop (AR_1309) is the single Beta machine**. The conversation, voice and language model are built and measured there (`docs/environment/new-laptop-beta-evidence-2026-11-13.md`). So the old-laptop benchmark in the 2026-11-01 note is no longer needed to choose a machine. The old laptop's GPU has 6 GiB, which cannot hold the cloned voice and a 9B model plan like the new laptop; no claim about it is made without a measurement (RK rule R8).

The old laptop's own evidence is **stale**: it was last recorded before the Windows reinstall of 2026-11-04 and before every change since (about 25 merged pull requests, the dashboard, the Unicode fix, the amended ADRs). Its `main` was `9ac5732` on 2026-11-04. Treat everything known about it as UNKNOWN until re-measured.

## 2. What the old laptop is useful for now

1. **B-10, clean-machine install (Beta acceptance, release gate).** Prove that JARVIS installs from a fresh clone and `doctor` runs healthy on a machine that is not the build machine. This is the one thing the new laptop cannot show about itself.
2. **B-02, fresh-clone full suite** as a second machine (independent of the new laptop's dry run).
3. A readable **second opinion** on the documents: does a session starting cold from the repository understand the state? (This tests `START HERE.md` and the docs, not code.)

It is **not** needed for voice, the model, or the dashboard in the Beta. Do **not** install Ollama, the voice venv or any model on the old laptop unless RK asks for it by name.

## 3. Steps, in order (read-only first)

All installs and changes need RK's per-item chat word (ADR-0001 Amendment 1). A session on the old laptop reports facts; it does not merge.

| # | Step | Kind | Evidence to bring back |
|---|---|---|---|
| 1 | `git fetch`, then `git status --short --branch`, `git log --oneline -n 10`, `git diff --stat phase-0-freeze..origin/main` | read-only | the outputs, and how far behind the clone is |
| 2 | `gh pr list --state open` and `gh api repos/{owner}/{repo}/rulesets` | read-only | PR list; ruleset `updated_at` (expected `2026-10-11T23:37:01.214+05:30`) |
| 3 | After RK's word, fast-forward to `origin/main` (no other change) | change, small | the new commit hash |
| 4 | `py -3.14 -m unittest discover -s tests -t .` | read-only | test count, OK or failures, any skip (new laptop: 463 OK, 1 skipped at `06e65e3`; the number will differ if `main` has moved) |
| 5 | Is `D:\JARVIS\` present on this machine, and what does `doctor` and `audit verify` say there? | read-only | the outputs, or "absent" |
| 6 | Is Python 3.14 present, which `py -0p` entries, git and gh versions? | read-only | the list |
| 6b | Smart App Control state and recent block events (the two commands in `docs/environment/smart-app-control-notes-2026-11-13.md`, section 5) | read-only | both outputs; whether SAC is on, off or in evaluation |
| 7 | **B-10** at the release-candidate freeze (target 26 November): follow the clean-machine runbook RK holds (`B10_CLEAN_MACHINE_RUNBOOK`): fresh clone to a new folder, create the data root and governance files only on RK's instruction, run `doctor`, `audit verify` and the suite | change, RK-gated | doctor result, suite result, anything that failed, and the exact commands used |
| 8 | Re-measure the old laptop inventory (hardware, free disk, driver) only if RK wants the benchmark question reopened | read-only | a dated inventory |

**Read first:** `docs/environment/smart-app-control-notes-2026-11-13.md` (what Windows Smart App Control blocked on the new laptop, the workarounds, and the rules: do not turn SAC off, do not upgrade pinned packages, report blocks instead of working around them).

## 4. Unresolved on the old laptop (RK decisions, not steps)

- The 2026-11-02 status check found an unsigned `dcntel.dll` beside an `updater.exe` under the Chrome program data folder; Defender quarantined it on 2026-11-03 and Windows was reinstalled. The status note made the unresolved security items a precondition for a **backend** role. That role no longer exists in the plan (the new laptop is the single machine), so the precondition is not blocking the B-10 clean-install test. Whether the reinstalled system is trusted enough to host B-10 is **RK's call**; a session cannot decide it.
- Cleanup of `D:\JARVIS-BENCH-OLD` and of the 2026-11-01 handoff note follows the order and the exact-path rules in that note, and needs RK's word per item. Nothing is deleted by this plan.

## 5. How a session on the old laptop should start

Open Claude Code in the repository folder on the old laptop. Ask it to: read `START HERE.md`, `CLAUDE.md` and `docs/README.md`; then run steps 1, 2, 4, 5 and 6 above (read-only) and report each result with its evidence, marking anything it could not check as UNKNOWN. It should not change anything until RK says so, and should say so if it finds this note stale.

## 6. What this note does not do

It does not accept a decision, change a gate, move the B-10 date, install anything, or touch `D:\JARVIS` or `E:\JARVIS-PROJECT` on either machine.
