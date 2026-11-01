# TEMPORARY HANDOFF — why the conversation benchmark runs on the OLD laptop

**Status: TEMPORARY and NON-AUTHORITATIVE. Delete this file once the old-laptop benchmark is recorded and the governance changes below are merged or dropped.**

This note grants no authority. It cannot amend governance. If it conflicts with the Master Context, an accepted ADR or MCA, or RK's chat word, the record wins and this note is wrong. Written 2026-11-01. `7afb07e` is this note's creation baseline (the `main` commit it was written against), not the current `main`; later merges, including this note's own, move `main` on.

## Why this note exists

RK wants Beta conversation to be natural, real-time and fully local (speech-to-text, language model, text-to-speech). Whether that is feasible depends on hardware, and RK's rule (R8) is that hardware is measured, never inferred. RK's two laptops have different roles, so the benchmark must run on the machine that will do the work.

## Machines (roles as stated by RK; hardware as measured)

| | OLD laptop | NEW laptop (host `AR_1309`) |
|---|---|---|
| Role (RK) | backend | interface |
| Model | ASUS TUF Dash F15 FX516PM | ASUS TUF Gaming F16 FX608JPR |
| CPU | i5-11300H, 4C/8T | i7-14650HX, 16C/24T |
| RAM | 15.7 GiB (2 x 8 GiB, 3200 MT/s) | 31.6 GiB (2 x 16 GiB, 5600 MT/s) |
| GPU | RTX 3060 Laptop, 6144 MiB, CC 8.6 | RTX 5070 Laptop, 8151 MiB, CC 12.0 |
| Driver | 592.00 | 591.91 |
| Windows | 11 Home SL 10.0.26200 | 11 Home 10.0.26300 |

Old-laptop values are the inventory RK ran and pasted on 2026-11-01 (idle readings; Claude did not run them). New-laptop values were measured by Claude on the same date. Neither machine has any benchmark result yet. CUDA runtime version is not yet measured on either. A session cannot measure another machine: the old laptop must be measured by a session running on it.

## RK decisions received in chat (not yet governance records)

- R1: fast push-to-talk conversational turns. Hands-free, wake word and barge-in stay excluded.
- R2: conversation is MANDATORY for Beta; it replaces the optional model-demo scope; the core control-plane path is unchanged; Galaxy expansion stays limited; no gate is weakened.
- R3: Option 1. Amend ADR-0013, add a one-sentence MCA-003, no ADR-0014.
- R8: hardware must be measured.

The proposed text is in two scratch documents outside the repo (conversational requirement analysis; conversation governance proposal, both dated 2026-10-31). They are proposals, not records.

## What is NOT done

- No ADR-0013 amendment, MCA-003 or Beta Plan Amendment 2 is drafted. RK required the old-laptop inventory first; it was received on 2026-11-01 (RK-run commands, pasted in chat). RK has not yet approved drafting, so none is started.
- No benchmark has run on either laptop. No benchmark script exists.
- Nothing was installed. Installs and model downloads are RK's act (G-13).

## Next steps

1. RK opens a Claude session on the old laptop with a self-contained measurement-only prompt (Tier 0: read-only measurements into `D:\JARVIS-BENCH-OLD`; Tier 1: a proposal only, no installs without RK's yes). That laptop has no copy of this repo and does not need one.
2. RK pastes the resulting report to the main session.
3. The main session compares it with the new laptop, writes the benchmark specification, and waits for RK's explicit approval before drafting any ADR, MCA, gate, script or code.

## Cleanup when this note has done its job

This note exists only to carry context until the old-laptop benchmark is recorded and the conversation governance is merged or dropped. After that it should be deleted and the items created only for this work removed. **No cleanup is performed now.** Nothing below may be done without RK's explicit word in chat, one item at a time, and each target must be listed and looked at before it is deleted.

### Order and precondition

1. **Record first.** All benchmark evidence (the old-laptop `old_laptop_report.md`, `idle.csv`, every later benchmark output and report) is copied into a durable record RK has approved (a repository record merged by RK, or a location RK names) before any wipe. Evidence and reports are preserved, never deleted by this cleanup. If a result has not been recorded, stop.
2. **Checksum and verified backup.** Before any cleanup, every evidence file gets a SHA-256 checksum, listed with its exact path, size and date in the approved record. A backup copy is made in a location RK names, each copy's SHA-256 is recomputed and compared with the original, and the match is reported. A backup that is not verified identical counts as no backup, and the cleanup stops.
3. Only then, the targets below, one at a time.

### Exact targets (nothing else is a target)

| # | Target | Where | Notes |
|---|---|---|---|
| 1 | `docs/plans/TEMP_HANDOFF_OLD_LAPTOP_BENCHMARK_2026-11-01.md` (this file) | repository | Deleted in its own docs-only PR, merged by RK. |
| 2 | Remote and local branch `docs/temp-handoff-old-laptop-benchmark` | repository | Delete only after its PR is merged. |
| 3 | Remote and local branch `docs/temp-handoff-cleanup-clause` | repository | Delete only after its PR is merged. |
| 4 | Folder `D:\JARVIS-BENCH-OLD` | old laptop only | Created by the old-laptop Tier 0 session for scratch output. Delete only after items 1 and 2 of "Order" (record, then checksum and verified backup) are satisfied. Delete by exact folder path after listing its contents; never by pattern. |
| 5 | Tier-1 installs (defined below), including downloaded model weights | old laptop only | Only those named in RK's approved Tier-1 proposal, each with the exact paths and removal method recorded as required below. |
| 6 | The two conversation proposal documents `JARVIS_CONVERSATIONAL_REQUIREMENT_ANALYSIS_2026-10-31.md` and `JARVIS_CONVERSATION_GOVERNANCE_PROPOSAL_2026-10-31.md` | outside the repository, in a Claude session scratchpad | Their exact current paths were not found on 2026-11-01. Both documents stay untouched (not moved, edited, renamed or deleted) until they are located and their exact paths are listed and confirmed by RK. They are proposals, not benchmark evidence; delete only once their content is merged into a record or RK drops it. |
| 7 | Memory pointer | Claude memory folder for this project | No pointer to this note exists on 2026-11-01. If one is added later (for example `jarvis-handoff-<date>.md` or a line in `MEMORY.md` naming this note), it must be named exactly here, in the PR that deletes this note, and removed or marked superseded only after RK's word. |

### "Tier-1 installs" defined

A Tier-1 install is any software, runtime, library, model weight, driver component or tool that is installed or downloaded onto the old laptop specifically to run the speech-to-text, language-model or text-to-speech benchmark, and that was approved by RK in the Tier-1 proposal before it was installed. It does not include anything already present before the benchmark (Windows, the NVIDIA driver, the Intel graphics driver, existing Python or git), which stays. If no Tier-1 proposal has been approved and executed, there are no Tier-1 installs and nothing to uninstall.

For every Tier-1 item the approved proposal, or an addendum RK approves before the install, must record:

- **Exact install location:** the full folder or file path where it was installed, not a drive or parent folder.
- **Exact path of every downloaded model weight:** the full file path of each weight file, with its size and SHA-256. A weight is never identified by a pattern or a folder of "models".
- **Exact uninstall method:** the vendor uninstaller by name and version, or the single exact folder or file to delete, written so it can be carried out without guessing.
- **Pre-removal listing:** the target's contents listed before removal, shown to RK.
- **Post-removal verification, per item:** after removal, confirm the exact path no longer exists, the program is gone from the installed-programs list or no longer runs, any environment variable or PATH entry added for it is gone, and that nothing that existed before the benchmark (see the exclusions above) changed. Report each item's result separately. An item without a recorded verification is not counted as removed.

If any of these were not recorded at install time, nothing for that item is removed until RK approves a recovered, listed path.

### Prohibited during cleanup

- No wildcard or broad recursive deletion (no `*`, no `rm -rf`/`Remove-Item -Recurse` on a drive root, a parent folder or a pattern). Delete only an exact, previously listed path.
- `D:\JARVIS` must never be touched.
- `E:\JARVIS-PROJECT` must never be touched.
- The JARVIS repository's code, policy, tests and governance records must never be touched by cleanup; the only repository change is deleting this file in its own PR.
- The review branch `review/chatgpt-verification-2026-10-31` is preserved unless RK closes that review and explicitly says to remove it.
- Do not delete anything that holds a result RK still needs.

## Do not

Touch `D:\JARVIS` or `E:\JARVIS-PROJECT`, create B-06 files, enable Stage B or D-12, or treat this note as approval for anything.
