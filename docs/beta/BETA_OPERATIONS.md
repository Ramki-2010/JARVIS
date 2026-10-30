# JARVIS Beta: operations guide

**Status:** Beta documentation. Describes how to install, run, back up and restore the Beta. It does not change any decision; the accepted ADRs and the Master Context remain authoritative.
**Labels used below:** `TESTED` (an automated test covers it), `OBSERVED` (seen on the real install, with the date), `PLANNED` (not done yet), `RK ACTION` (only RK does this).

## 1. What the Beta is

A governed, human-in-the-loop assistant. JARVIS records tasks, reads files inside a project contract, writes a deterministic brief, stores the result a person relays back as untrusted data, keeps notes, and resumes cold. **A person runs the worker.** It makes no network connection, starts no process, calls no model, and runs no scheduler. See `BETA_SECURITY_AND_RELEASE_NOTES.md` for the limits.

## 2. Clean install

Prerequisites: Windows 11, Git, and **Python 3.14 through the `py` launcher** (`py -3.14 --version`). The `python` on PATH may be older and is never used. JARVIS uses only the Python standard library; nothing is installed with pip.

1. Clone the repository and open a terminal in it.
2. `scripts\check-install.cmd` checks Python 3.14 and runs `doctor` (read-only). `TESTED` (launcher pins the interpreter); a clean-machine run is `PLANNED` for Gate 6 (acceptance B-10).
3. The two operational folders are created by RK once, outside the repository (ADR-0004, ADR-0007). The launcher never creates them:
   - governance zone `D:\JARVIS\governance\` holds `jarvis.toml` (configuration), `revocations.toml`, `registry.toml` and `contracts\<project>.toml`. `RK ACTION`
   - data root `D:\JARVIS\data\` holds the database, `HEAD`, and the folders `memory\`, `briefs\`, `results\`, `reports\`.
4. `jarvis.toml` keys: `schema_version = 1`, `data_root`, `governance_zone`, `user_home` (absolute Windows paths, single-quoted). Nothing secret goes in it; the loader refuses secret-like keys and reads no environment variable.
5. First use only: `scripts\jarvis.cmd init` creates the database and its genesis record. It refuses to run if a store already exists. `OBSERVED` 2026-10-30 on the real install.
6. `RK ACTION`: write `registry.toml` and one contract per project you want JARVIS to read:

```toml
# registry.toml
schema_version = 1
[[projects]]
id = "myproject"                 # lower case letters, digits, hyphen
name = "My Project"
root = 'D:\path\to\myproject'
repository = "owner/repo"        # optional
description = "optional text"    # optional
```

```toml
# contracts\myproject.toml : a contract may only narrow, so every scope root lies inside the root
schema_version = 1
project_id = "myproject"
scope_roots = ['D:\path\to\myproject\src']
protected_paths = ['D:\path\to\myproject\src\core']        # optional: reads are allowed at a higher risk level
forbidden_operations = ["PUSH"]                            # optional
valid_until = "2027-01-01T00:00:00.000000Z"                # optional
```

7. `scripts\jarvis.cmd doctor` should end `doctor: OK`. A missing registry or contract is a warning, not a failure.

## 3. The workflow

```
scripts\jarvis.cmd resume                                  # cold start: health, projects, open tasks, notes
scripts\jarvis.cmd project list
scripts\jarvis.cmd project show myproject
scripts\jarvis.cmd task create --id fix-1 --project myproject --objective "Describe the work" ^
    --request READ_FILE=path:D:\path\to\myproject\src\main.py --request GENERATE_WORKER_BRIEF
scripts\jarvis.cmd task evaluate fix-1                     # RUNNING if every request is allowed
scripts\jarvis.cmd task run fix-1 --show-reads             # reads, then writes the brief
scripts\jarvis.cmd brief show fix-1                        # give this text to the worker (a person)
   ... the worker does the work outside JARVIS ...
scripts\jarvis.cmd result add fix-1 --file D:\path\to\worker-output.txt
scripts\jarvis.cmd note add --project myproject --text "Result #12 reviewed; next step is X."
scripts\jarvis.cmd resume --project myproject
scripts\jarvis.cmd audit verify
scripts\jarvis.cmd doctor
```

Rules that matter: reads happen only as steps of a task and only on a path that is allowed at the moment `task run` executes. A relayed result is stored word for word, labelled `UNTRUSTED, NOT VERIFIED`, and never changes a task, a policy or a brief. Nothing is ever `VERIFIED`: there is no independent verifier in the Beta.

## 4. Commands

| Command | Purpose |
|---|---|
| `init` | create the store (first use only) |
| `status`, `doctor` | state, and a PASS/WARN/FAIL health check |
| `audit verify` | verify the hash chain from genesis |
| `project list`, `project show <id>` | registered projects and their contracts (read-only) |
| `task create / evaluate / run / show / list`, `cancel` | task lifecycle |
| `brief show <task>` | the latest brief, checked against the chain |
| `result add / list / show` | relayed results (untrusted) |
| `note add / list / show` | notes (`--decision` marks a decision) |
| `resume [--project]` | cold-start summary |
| `report [<task>]` | task report, or a summary |

Exit codes: 0 ok, 1 unexpected error, 2 usage, 3 configuration error, 4 store missing, 5 audit failure or store halted, 6 store busy, 7 task error, 8 init refused, 9 doctor found a failure, 10 project registry unavailable or project unknown, 11 note refused, 12 brief unavailable, 13 result refused.

## 5. Reading doctor

`FAIL` means do not trust the install until fixed. `WARN` means something RK has not yet written. Typical lines: `FAIL audit chain` (run `audit verify`; restore from backup if the chain is broken), `FAIL notes|briefs|results: ..._FILE_CHANGED` (a file was edited after it was recorded), `..._FILE_UNRECORDED` (a file exists that the chain does not record, for example after a crash between writing the file and recording it; inspect, then move it away), `FAIL policy` (the policy file is missing or invalid; every capability is refused until fixed), `WARN registry: REGISTRY_MISSING`.

## 6. Backup and restore

What a backup holds: the database (copied with SQLite's own backup API, consistent while JARVIS is idle or running), `HEAD`, `memory\`, `briefs\`, `results\`, `reports\`, and the governance zone, plus `MANIFEST.json` with a SHA-256 for every file. **It contains your notes, relayed results and project paths: keep it private.** It must not go into Git or a cloud-synced folder unless RK decides so (G-06). Where backups live is an `RK ACTION` (open decision U-7); the tool takes any new, empty folder outside the install, ideally on another drive.

```
py -3.14 scripts\backup.py create E:\JarvisBackups\2026-11-20
py -3.14 scripts\backup.py verify E:\JarvisBackups\2026-11-20
```

`verify` checks every hash, restores into a scratch folder, runs the audit-chain verification, compares `HEAD`, and deletes the scratch folder. It never touches the install. `TESTED`: create and verify, each kind of damage, and a restored copy passing `doctor`, `audit verify` and `resume`. A drill on the real install is `PLANNED` (acceptance B-09).

Restore (manual and deliberate; nothing in JARVIS does it for you):

1. Close anything running JARVIS. Run `backup.py verify` on the backup you intend to use.
2. Rename the live folders: `D:\JARVIS\data` to `D:\JARVIS\data-old-<date>` and, only if the governance zone is being restored too, `D:\JARVIS\governance` likewise. Do not delete them.
3. Copy `<backup>\data` to `D:\JARVIS\data` and, if needed, `<backup>\governance` to `D:\JARVIS\governance`.
4. `scripts\jarvis.cmd audit verify` then `scripts\jarvis.cmd doctor`. Both must pass.
5. Keep the renamed folders until you are satisfied. Anything recorded after the backup is lost from the restored chain; it is still in the renamed folder.

Records store a path relative to the data root, so a restore to a different location also verifies. `TESTED`.

## 7. Updating

`git pull` on `main`, then `scripts\check-install.cmd`. Policy lives in `policy\policy.toml` in the repository; a new policy version is recorded in the store at the first evaluation after the update. Run the test suite with `py -3.14 -m unittest discover -s tests -t .`.

## 8. The audit anchor

The first anchor is made by RK, by pull request, under ADR-0009. It is not part of installing. Until it exists, the audit chain is tamper-evident only against changes that leave `HEAD` consistent; say so if you describe the Beta's integrity.
