# ADR-0015 — Governed Local Launch: opening approved apps, folders, files and games by voice or text

**STATUS: PROPOSED** (RK decided the scope in chat on 2026-11-13; this text becomes ACCEPTED only when RK merges the pull request that adds it, ADR-0001 D6)

| Field | Value |
|---|---|
| ID | ADR-0015 |
| Title | Governed local launch: opening approved apps, folders, files and games |
| Status | PROPOSED |
| Drafted | 2026-11-13, by Local Claude, from RK's chat decision |
| Authority class | USER AUTHORITY REQUIRED (G-05 for the policy entry and the catalog file; G-03 for the new capability definition) |
| Inputs | ADR-0003 (capability evaluation). ADR-0006 (the control plane starts no process). ADR-0011 D2 (named process-creating sites), D3 (localhost server rules). ADR-0013 Amendment 1 (model output is untrusted text). ADR-0014 (the third process site and the pattern of a catalog plus a capability plus an audit record). Beta plan BR-9. Master Context section 30 |
| Amends | The Beta plan (section 13, Amendment 3). Nothing else |

**Labels:** `PROPOSED` · `USER AUTHORITY REQUIRED` · `UNKNOWN` · `RK ACT` · `MEASURED` · `UNVERIFIED`.

## 1. Context and the conflict, stated plainly

RK decided on 2026-11-13 that JARVIS should be able to **open things on this laptop**: Windows tools such as Settings and Task Manager, a media player such as VLC, a handful of folders (Downloads, Music, Videos and others), a file such as a movie stored on the D: drive, and installed games. RK asked for a recommended list "acceptable, not very fixed and small", to be finished before the Beta.

This needs **no internet**. It does need a power JARVIS does not have: **starting a program**. Today JARVIS reads records and writes notes, and the standing rules say only named code may start processes: `interaction/child.py` and `interaction/voice_child.py` (ADR-0011 D2), plus `interaction/fetch_child.py` if ADR-0014 is accepted. "Open the browser" is on JARVIS's list of things it declines. RK is the owner and may widen scope; ADR-0001 requires the widening to be recorded and bounded. This ADR is that record. It is not a general "run programs" capability and must never become one.

## 2. Decision (all items PROPOSED)

### D1. Scope: four kinds of "open", nothing else
| Kind | What it does | Confirmation turn |
|---|---|---|
| `app` | Starts one program from RK's catalog (section 4 lists the recommendation) | No: low risk, logged |
| `folder` | Opens one catalog folder in File Explorer | No: low risk, logged |
| `file` | Opens one file found inside a catalog folder, with the program the catalog names for that file type | **Yes**: JARVIS names the exact file and program and waits for "yes" |
| `game` | Starts one game or game launcher from the catalog | **Yes**: same reason, plus a game is long running |

Everything else stays unsupported: JARVIS says plainly that it cannot do it and offers to note it. "Open Settings" opens the Settings **application**; JARVIS never changes a setting. Closing, killing, minimising or moving a program is not supported.

### D2. One more named process site, and it is dumb
- A new helper, `interaction/launch_child.py`, becomes the **fourth** process-creating site. The static test names all four and fails on any fifth.
- It starts a program from an **absolute executable path read from the catalog**, with arguments built from a **fixed template in the catalog entry** (for a file: the single resolved file path as one argument). Never a shell, never `cmd /c`, never `start`, never a string the user typed, never an environment passed through. The new process is detached (JARVIS does not wait for it, does not read its output, and does not hold its handles).
- It runs as RK, with RK's ordinary rights, and cannot elevate. A program that asks for administrator rights asks RK through Windows, as it would anyway.

### D3. Files: names are looked up, paths are never typed
1. The user says a name ("the Dune movie"). The name is **only a lookup token**, 2 to 60 letters, digits, spaces, hyphen, dot and apostrophe.
2. Code lists **names and extensions only** (never contents) in the catalog folders, to a depth of 4, stopping at 20,000 entries or 2 seconds. A match is a case-insensitive, punctuation-insensitive whole-word match on the file name. Several matches produce a numbered list and a question; none produces "I could not find that, sir".
3. The resolved path must pass: it is **inside a catalog folder after resolving the real path** (so `..`, junctions, symbolic links and mapped or network paths cannot escape); it is a regular file; its extension is in the **allow list** of D4; its name has no control characters.
4. **Never openable**, whatever the folder: executables and installers and scripts and shortcuts (`.exe .msi .bat .cmd .com .ps1 .psm1 .vbs .vbe .js .jse .wsf .hta .jar .reg .lnk .url .scr .dll .sys .cpl .msc .appx .msix`), disk images, archives (`.zip .7z .rar .iso`), and anything with no extension.
5. The directory listing is made by the process that handles the conversation, not by the dashboard. The dashboard still reads no file system (ADR-0011).

### D4. The catalog is RK's file, and JARVIS never edits it
A single file, `launch_catalog.toml`, lives in the governance zone beside the policy and registry. RK writes it; JARVIS reads it and **never writes it** (the same stance as the project registry). It is validated at start-up and again before each use; a bad entry is dropped with a plain notice, never guessed.

- **Fixed addresses.** An `app` entry may carry a fixed `https://` address in its `args`, written by RK (for example YouTube). An address from speech, from a model or from a page is **never** passed. JARVIS opening such an entry starts the browser, and it is the browser, not JARVIS, that then reaches the network; JARVIS gains no network access and its firewall rules are unchanged. Only the catalog's own address is opened, nothing is searched, and JARVIS cannot choose a video or a track.
- **Entries** (at most 64): `id`, `name`, `spoken` (alternative names), `kind`, and for apps and games `exe` (an absolute path on a local drive, ending `.exe`, existing) and `args` (a fixed list; the one placeholder `{file}` is allowed only for file types). For folders `path` (absolute, local, existing). For file types `extensions`, the program id to use, and the folders they apply to.
- **File types allowed** (the allow list, ADR-level maximum; RK may narrow it): video `.mp4 .mkv .avi .mov .webm .m4v`; audio `.mp3 .flac .wav .m4a .ogg`; images `.jpg .jpeg .png .gif .webp`; documents `.pdf .txt .md`. Nothing outside this list can be added by the catalog alone; widening it is an amendment to this ADR.
- Paths in the repository use environment variables or placeholders (`%USERPROFILE%`, `D:\<movies folder>`); a personal path appears only in RK's real catalog file, which is not in the repository.

### D5. Policy and audit
A new capability, `LAUNCH_LOCAL`, scoped by kind (`app`, `folder`, `file`, `game`), is evaluated by policy for each open. `RK ACT`: RK adds it to the policy file (governance, G-03/G-05); if absent, every open is refused with "that is not permitted, sir". Each open is recorded in the audit chain through two new control-plane commands (`launch authorize <kind> <catalog-id>` before, `launch record <kind> <catalog-id> <result>` after). The record holds kind, catalog id, result, and for a file the **extension and a short hash of the path**, not the file name (a movie title is personal). The control plane itself still starts no process (ADR-0006 stands).

### D6. Games
RK's catalog lists games or launchers explicitly. A game entry is either a program path with fixed arguments or a launcher with a fixed game address such as `steam://rungameid/<number>`, typed by RK into the catalog. JARVIS never scans a game library, never reads a launcher's files, and never invents a game: a game it does not have an entry for is "not on my list, sir". Because a launcher reaches the network on its own, the ADR notes that JARVIS does not gain network access by starting one, and the firewall rules on JARVIS's own programs are unchanged.

### D7. Conversation
New deterministic intents only (no model chooses a command): open an app, open a folder, open a file, play a game. Recognition is by fixed phrasing ("open ...", "launch ...", "start ...", "play ...", "show me ... folder"). The name is data and is matched only against the catalog. The existing refusal "open the browser" is replaced by a catalog lookup: the browser opens **if RK lists it**, otherwise JARVIS says it is not on its list. Reply wording is formed by code from fixed fields ("Opening Task Manager, sir.") and is not model text.

### D8. Failure behaviour
A missing program, a moved file, a refused policy check, a start-up failure each give one plain sentence and change nothing. No retry loop. `launch_enabled = false` in RK's configuration disables the whole feature.

## 3. What is deliberately not done
No arbitrary program or path, no command line from speech, no shell, no script execution, no installers, no archives, no closing or killing of programs, no keystroke or mouse automation, no screen reading, no changing of Windows settings, no administrator elevation, no web address from speech, a model or a page (only the fixed addresses RK writes in the catalog), no scanning of game libraries or folders for executables, no write to the catalog by JARVIS, no model-chosen action.

## 4. Recommended catalog (RK edits it; nothing here is installed or created by this ADR)

States below were `MEASURED` by Local Claude from its own tool on 2026-11-13 (a path existing on this machine), not from JARVIS.

**Apps (Beta recommendation)**
| Id | Opens | State today |
|---|---|---|
| `settings` | Windows Settings, via `explorer.exe` with the fixed argument `ms-settings:` | Windows built-in |
| `taskmgr` | Task Manager, `C:\Windows\System32\taskmgr.exe` | present |
| `explorer` | File Explorer, `C:\Windows\explorer.exe` | present |
| `calc` | Calculator, `C:\Windows\System32\calc.exe` | present |
| `notepad` | Notepad, `C:\Windows\notepad.exe` | present |
| `vlc` | VLC media player, `C:\Program Files\VideoLAN\VLC\vlc.exe`; the program for video and audio files | present |
| `browser` | Zen Browser, `C:\Program Files\Zen Browser\zen.exe` (opens its start page; RK's choice, replacing Edge, which is not listed) | present |
| `claude` | Claude desktop app (a packaged app), started as `explorer.exe` with the fixed argument `shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude` | installed; a detached start of a packaged app is `UNVERIFIED` |
| `spotify` | Spotify, `%APPDATA%\Spotify\Spotify.exe`; opens the app only, JARVIS cannot choose or play a track | present |
| `youtube` | A **fixed web shortcut** (D4): the `browser` program with the fixed address `https://www.youtube.com/`, written by RK in the catalog | depends on `browser`; address is RK's text, not speech |
| `steam` | Steam launcher, `C:\Program Files (x86)\Steam\steam.exe` | present |
| `epic` | Epic Games Launcher (path to be pinned by RK) | folder present, executable path `UNVERIFIED` |

Not recommended for the Beta: Paint (its classic path was not found; it is a store app), Command Prompt and PowerShell (they run commands; excluded on purpose), Registry Editor, Services, anything that needs administrator rights.

**Folders (Beta recommendation)**: Downloads, Music, Videos, Documents, Pictures and Desktop under the user profile (all present), plus **the folders RK names on the D: drive** (for example a movies folder). RK provides the list; the catalog needs only each folder's path. Project folders such as the repository stay out: they are governed by the project registry, not the launcher.

**Files**: movies, music, pictures and PDFs inside the folders above, by name, with confirmation (D1). Movies open in VLC, music in VLC, pictures and PDFs in the default viewer named in the catalog.

**Games**: RK lists each game he wants spoken for (a program path, or a launcher plus a game number). Until RK lists any, "play a game" opens the Steam and Epic launchers only if their entries exist.

## 5. Beta plan effects (Amendment 3, extended)
| Item | Change |
|---|---|
| BR-19 (new) | **Governed local launch** under ADR-0015: apps, folders, files, games from RK's catalog. Needs this ADR accepted, a `LAUNCH_LOCAL` policy entry and a catalog file (RK acts) |
| BR-9 / X-13 | Unchanged. The static test names the four process-creating sites |
| BU-12 (new) | Every limit in D2 to D5 has a test: unknown id, path escape (`..`, junction, symbolic link, UNC, mapped drive), forbidden extension, depth and entry limits, several matches, hostile name text, forged catalog entry, policy denied means no open, a failed start changes nothing, the audit record holds no file name |
| B-13 (extended) | Release notes state: JARVIS opens only what RK's catalog lists; it cannot close, control or install anything; it never types a command |
| Cut order | BR-15 is cut first, **BR-19 second**, before Stage B task create. The conversation, the galaxy and voice are not cuttable. A cut or a date change is reported the same day |
| Date | Not changed by this ADR |

## 6. Consequences and unknowns
- **Gain:** the assistant can do the everyday desktop things RK asked for with a small, auditable, switch-off-able surface and no network.
- **Cost:** a fourth process site, a new capability, two control-plane commands, a catalog file with a validator, a file-name matcher, new intents and the tests of BU-12. None is built until RK merges this ADR.
- **Risk:** a launched program is outside JARVIS's control: it can do anything RK's account can. The catalog limits what can be started; it cannot limit what a started program does. Opening a media file hands it to a program that parses untrusted content; the allow list and the confirmation turn reduce that, they do not remove it.
- **`UNVERIFIED`:** how a detached start behaves under Smart App Control for each program on the list (all listed programs are already installed and signed, but this was not tested); whether Windows treats `explorer.exe ms-settings:` identically from a detached child; the Epic launcher's executable path; that a detached start of the Claude packaged app and of a browser with a fixed address behave as expected; that the real path check resolves every junction on this machine's drives.
- **`RK ACT` list:** write the catalog file (apps, folders, games, file-type rules); add `LAUNCH_LOCAL` to the policy; confirm the D: folders; decide whether the browser is on the list.

## 7. Amendment 1 (2026-11-13): what the build settled

Everything below fills in or narrows the decision above; nothing widens it.

| Item | Result |
|---|---|
| Catalog format (D4) | TOML tables `[[app]]`, `[[folder]]`, `[[game]]` and `[[filetype]]` with `schema_version = 1`; a worked example with RK's recommended list is `docs/examples/launch_catalog.example.toml` (placeholders only). The real file is `<governance folder>\launch_catalog.toml`, RK's, never written by JARVIS. It is read afresh before every request and each program or folder is checked again just before use |
| Paths | Only `%USERPROFILE% %APPDATA% %LOCALAPPDATA% %PROGRAMFILES% %PROGRAMFILES(X86)% %SYSTEMROOT% %PROGRAMDATA%` may appear; any other variable, a relative path, a UNC path, `..`, a non-`.exe` program, a missing program or a missing folder drops that entry with a notice that names only its id |
| Arguments (D4) | Fixed lists of at most 8 plain strings; `{file}` only as a whole element of `file_args`; an `https://` address is allowed (RK writes it), `http://`, `ftp://`, `file://` and every other scheme are not; `steam://rungameid/...` only for games |
| File types (D3, D4) | A `[[filetype]]` rule names an app (one with `file_args`), extensions from the allow list and the folder ids it applies to. An extension outside the allow list drops the rule. The never-open list overrides everything. Search is by whole words of the file name, depth 4, 20,000 entries, 2 seconds, never following a link or junction, with a real-path containment check; several matches ask "which one", then ask for a yes |
| Process (D2) | `interaction/launch_child.py` is the fourth named process site: absolute `.exe`, fixed arguments, no shell, detached, no handles kept. **Environment:** not the caller's own, but a fixed short list of per-user locations (`USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `PROGRAMFILES`, `TEMP` and similar) plus a system-only `PATH`, because programs cannot find their settings without them; no token, key or project variable is passed. This is the one place where D2's "never an environment passed through" is read as "never JARVIS's own environment" |
| Policy (D5) | Version 4 adds exactly one capability, `LAUNCH_LOCAL` (L2, `CONTROL_PLANE_RECORD`), scoped by kind in the evaluated record. Version 3 is frozen in `tests/golden/policy_v3.toml`. `launch authorize` records LAUNCH_AUTHORIZED or LAUNCH_REFUSED; `launch record` records kind, catalog id and result, and for a file only its extension and an 8-character hash of its path, marked MEDIATED. A denied check starts nothing and records no "ok" |
| Conversation (D7) | "open / launch / start / bring up" for apps, folders and games; "play / watch / listen to" for apps, games and files (never folders); "show me ... folder". Apps and folders open at once; games and files wait for a yes. A name not in the catalog is "that is not on my list, sir"; a phrase that is not clearly a request (for example "start over") stays ordinary conversation |
| Switch-off (D8) | No `launch_enabled` key was added. Launching is off when there is no catalog file, with `--no-launch`, or when the policy row is removed; in each case "open the browser" gets the earlier plain answer |
| Measured | The example catalog validates in full on this machine (every listed program and folder present except the Epic launcher, which is not in the example). A detached start of Calculator through the whole path (intent, policy check, audit, launcher) worked under Smart App Control, and the audit chain verified afterwards (`MEASURED` 2026-11-13) |
| Still `UNVERIFIED` | Detached start of the other programs (Spotify, VLC, Zen, Steam, and the Claude packaged app through `explorer.exe shell:AppsFolder\...`); a browser opening a fixed address; a junction that leaves a catalog folder (a symbolic link is skipped by design and its test needs a privilege this account lacked, so it was skipped; junction behaviour is by `realpath` and untested); a mapped network drive in the catalog (RK's own choice; containment still applies); the Epic launcher's executable path |
| Tests | `tests/test_launch.py` (catalog rules, finder limits, process helper, control-plane commands, conversation flows, hostile names) and the static guard now naming four process sites |

## 8. Amendment 2 (2026-11-14): a title need not be spelled in full

RK asked not to have to say a whole film name. This widens a match rule only; the folders searched, the limits, the extension allow list, the never-open list, the containment check and the "which one, then yes" turns are unchanged.

| Item | Result |
|---|---|
| Match (D3) | Each word of what RK says must be a word of the file name, or the **start** of one when it is three letters or more ("dun" finds "Dune"; "inter" finds "Interstellar"). A word of one or two letters must match whole. The middle or end of a word never matches. Every word must be found, in any order |
| Order | A file whose name is exactly the words said comes first, then names where every word matched whole, then names that needed a word start; ties by name. Several matches still produce the numbered "which one" and then the "yes" |
| Not done | Matching "2" to "Two" (numerals and number words), spelling tolerance and fuzzy matching: each would widen the match further and is left for RK to decide |

