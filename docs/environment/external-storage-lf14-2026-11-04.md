# External operational storage created, LF-14 check — 2026-11-04

**Status: HISTORICAL EVIDENCE, NON-AUTHORITATIVE.** It records a local fact check. It grants no authority and decides nothing. If it conflicts with an accepted record, the record wins.

Labels as in ADR-0007: `VERIFIED` · `UNKNOWN`.

## What was done

- RK instructed the creation in chat on 2026-11-04: "proceed to create the external folder in Jarvis, mentioned on START HERE". That is the separate act on RK's instruction that ADR-0007 section 9 requires. This record is evidence of the act, not the instruction.
- `D:\JARVIS\`, `D:\JARVIS\governance\` and `D:\JARVIS\data\` were created, empty, with no content, ACL change or registry entry.
- Machine: ASUS TUF Dash F15 FX516PM (host `LAPTOP-ARE53VOA`, RTX 3060 Laptop), the laptop named "OLD laptop" in `docs/plans/TEMP_HANDOFF_OLD_LAPTOP_BENCHMARK_2026-11-01.md`, after a Windows reinstall. It is not the "NEW laptop" (host `AR_1309`).
- The repository was cloned to `D:\J.A.R.V.I.S AI Assistant` from GitHub on the same day (`main` at `9ac5732`, `phase-0-freeze` resolves to `e919b7a`).

## LF-14 re-check (ADR-0004 D2, ADR-0007 section 4)

| Check | Result |
|---|---|
| `D:\JARVIS`, `governance\` and `data\` are not inside any git work tree | `VERIFIED`: `git rev-parse` fails with "not a git repository" for all three; `D:\.git` does not exist |
| Not inside the JARVIS repository working tree | `VERIFIED`: `D:\J.A.R.V.I.S AI Assistant` is not a prefix of the paths. The tree is a sibling of the repositories at the top of `D:\` (`cbm-audit`, `J.A.R.V.I.S AI Assistant`, `Swaragam`) |
| Not inside a registered project root | `VERIFIED`: no project is registered (the registry does not exist yet) |
| Not in a cloud-synced folder | `VERIFIED`: no OneDrive account is registered on this machine (no entry under `HKCU:\Software\Microsoft\OneDrive\Accounts`); `%OneDrive%` is `C:\Users\ramki\OneDrive`, not under `D:` |
| D: file system | `VERIFIED`: NTFS |

## Facts that differ from ADR-0007 section 4 (measured on a different machine, 2026-10-12)

- `LongPathsEnabled` is **0** here (ADR-0007 recorded 1). Not changed: it is a system setting.
- C: and D: are on **different physical disks** here (disk numbers 1 and 0). ADR-0007 recorded D: on the same NVMe disk as C:. The ADR-0007 section 5 disk-loss concern is therefore not true of this machine in the same way. Not re-assessed.
- 8.3 short-name behaviour on D: (LF-10): `UNKNOWN`. `fsutil 8dot3name query D:` returned "Access is denied"; it needs elevation.

## Not established

- Whether `D:\JARVIS\` already exists on the NEW laptop (`AR_1309`). `docs/architecture/JARVIS_PRESENCE_AND_FASTTRACK_PROPOSAL_v0.1.md` states that it was created there and passed LF-14; this session could not observe that machine.
- Backup of `D:\JARVIS\` (ADR-0007 section 10): still `UNKNOWN`, `USER AUTHORITY REQUIRED`.
- The TEMP handoff note forbids touching `D:\JARVIS` during its cleanup. This creation was an explicit instruction from RK and is not part of that cleanup.
