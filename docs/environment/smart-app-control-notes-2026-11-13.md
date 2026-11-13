# Smart App Control: what blocked us, what we did, and what the old laptop must know (2026-11-13)

**Status: evidence and guidance, NON-AUTHORITATIVE.** It grants no authority and changes no rule. Marked MEASURED (seen by Local Claude on the new laptop), INFERRED (the best explanation of what was seen, not proven), or UNKNOWN. Written because the Beta date is near and RK wants no miscommunication between the two laptops.

## 1. What Smart App Control is, in plain words

Smart App Control (SAC) is a Windows 11 protection. When it is on, Windows runs only programs and libraries that are either signed by a trusted publisher or that Microsoft's cloud already knows as safe. Anything else is stopped at the moment Windows tries to load it. Python itself is signed and loads fine. The trouble is the *compiled helper files* (`.pyd` and `.dll`) inside some Python packages: the newest release of a package is often unsigned and too new for Microsoft to know it, so SAC blocks it. An older release that many people already use passes.

New laptop, MEASURED 2026-11-13: SAC is **on** (registry value `VerifiedAndReputablePolicyState` = 1; 0 is off, 2 is evaluation).

## 2. How a block looks, and how to see it

- In Python: `OSError: [WinError 4551] An Application Control policy has blocked this file`, usually when importing a package.
- In Windows Security: a notice such as "Smart App Control blocked part of this app" naming a file.
- In the log (MEASURED, works without administrator): Event Viewer, Applications and Services Logs, Microsoft, Windows, CodeIntegrity, Operational. Event 3077 is a block that was enforced, 3033 says a file did not meet the signing requirements. PowerShell:

```
Get-WinEvent -LogName 'Microsoft-Windows-CodeIntegrity/Operational' -MaxEvents 200 | Where-Object { $_.Id -in 3077,3033 } | Select-Object TimeCreated,Id,Message
```

On the new laptop the last blocks in that log are from the evening of 2026-11-12 (the install work below). **None has appeared since the pins in section 3 were applied** (MEASURED on 2026-11-13).

## 3. Every block we met, and the workaround

All of this is in the voice environment `D:\JARVIS\voice\venv` (Python 3.10). The control plane (Python 3.14, standard library only) never hit a block.

| # | What blocked | Symptom | Workaround | Result |
|---|---|---|---|---|
| 1 | `torch 2.11.0+cu128` (compiled libraries) | WinError 4551 on `import torch` | Install the previous release `torch==2.10.0+cu128` (tip from Gemini; recorded in `constraints.txt`) | torch loads, CUDA works (MEASURED) |
| 2 | `av 17.1.0` (a dependency of faster-whisper, used to read audio files) | `import faster_whisper` failed through `av` | First a stub `av` module only to prove nothing else was blocked, then the stub was removed and `av==16.0.1` pinned | Real import works; speech-to-text transcribed a test clip correctly (MEASURED) |
| 3 | `numba 0.68.1` (a dependency of librosa) | `import librosa` failed | First a stand-in to prove the rest was fine, then `numba==0.61.2` and `llvmlite==0.44.0` pinned | Real librosa works (MEASURED) |
| 4 | Triton (a speed-up compiler for torch) | Could not be installed or loaded | Not used. VoxCPM2 runs with `optimize=False`, which skips it. Not needed | No loss of function; speed is fine (rtf about 1.0) |
| 5 | `_dataset_orc.cp310-win_amd64.pyd` (RK's screenshot of a Windows Security notice) | Notice "blocked" | The file name is typical of the pyarrow package (INFERRED). The voice path never imports it, so nothing was changed | Voice works without it (MEASURED); root cause not pursued |

Other things that were **not** blocked (MEASURED, Authenticode "Valid"): Python 3.14, Python 3.10 and the private copy of Python 3.10 under `D:\JARVIS\voice\python310`, and `ollama.exe` (signed by Ollama Inc.). Git and `gh` are official signed installs.

Current pins that matter (MEASURED from `pip list`): torch 2.10.0+cu128, av 16.0.1, numba 0.61.2, llvmlite 0.44.0, numpy 2.2.6, scipy 1.15.3, faster-whisper 1.2.1, ctranslate2 4.9.0, onnxruntime 1.23.2, librosa 0.11.0, voxcpm 2.0.3, soundfile 0.14.0.

Why it works (INFERRED): SAC decides by the reputation of each file, and the older builds have it while the newest builds do not yet. We cannot prove the exact rule; we only observed that these older builds load and the newer ones do not.

## 4. Rules for everyone (both laptops) until the Beta ships

1. **Do not turn Smart App Control off.** By Microsoft's own description it cannot be turned back on without resetting Windows (recalled from Microsoft's documentation, UNVERIFIED here). It is also part of the protection the Beta relies on.
2. **Do not upgrade or reinstall any pinned package** in the voice environment. An upgrade can bring back a block that is hard to undo. If a package must change, test it first in a throwaway folder (the earlier test folder was `D:\JARVIS\voice\sactest`) by importing every compiled module before touching the real environment.
3. **If something is blocked:** stop, do not retry in a loop, do not look for a way around SAC, and report: the exact error text, the file path, the event ID and time from the log above, and the file's SHA-256 (`Get-FileHash`). Then RK decides.
4. **Freeze for the release candidate (target 26 Nov):** write `pip freeze` of the voice environment into its install record and change nothing after.

## 5. What the old laptop needs to do about this

The old laptop is **not** a voice or model machine in the Beta (see `docs/plans/OLD_LAPTOP_NEXT_STEPS_2026-11-13.md`). The B-10 clean-install test uses only Python 3.14 and the standard library, so SAC should not interfere. But the old laptop's SAC state is **UNKNOWN**: Windows was reinstalled on 2026-11-04, and a fresh Windows 11 install often starts SAC in evaluation mode, which can turn itself on or off. Read-only checks to add to the first session there:

```
(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy').VerifiedAndReputablePolicyState
Get-WinEvent -LogName 'Microsoft-Windows-CodeIntegrity/Operational' -MaxEvents 200 | Where-Object { $_.Id -in 3077,3033 } | Select-Object -First 20 TimeCreated,Id,Message
```

Report both outputs. Do not install the voice environment, Ollama or any model there. If B-10 meets a block, follow rule 3 above.

## 6. Guards and the Beta run (RK's concern, answered)

RK asked that guardrails and process-creation guards never cause a crash or a recovery step in the Beta run. State of play (MEASURED by tests and runs on 2026-11-13):

- **Most guards are tests.** The static guards and process-creation checks run only when the test suite runs (about 45 seconds, before a merge). They are not running inside the Beta program, so they cannot crash it.
- **Guards that do run inside the program fail safe, not hard.** If the approved model list is missing or the model's digest differs, conversation says so and the rest of JARVIS works. If the voice asset's SHA-256 differs from its record, the voice refuses to speak and text still works. If the voice worker cannot start, JARVIS continues in text. A model or voice error is shown as a message and changes nothing.
- **The child-process helpers only check their own arguments** (absolute interpreter path, no shell, size and time caps). Normal use cannot trigger a refusal.
- **No rule was loosened and none was added to slow the Beta.** The ADRs were read to stay consistent with them; nothing in them was changed this week except the amendments RK approved.
- **Not yet proven:** a full Beta rehearsal with the voice, the model and the dashboard running together. That is planned before the 23 Nov end-to-end gate; until then this section is a design statement backed by the tests above, not a rehearsal result.
