# The voice stopped loading under Smart App Control (2026-11-28)

**Status: evidence, NON-AUTHORITATIVE.** It decides nothing. Marked MEASURED (seen on the new laptop on this date), INFERRED (best explanation, not proven) or UNKNOWN. Continues `smart-app-control-notes-2026-11-13.md` (section 3a: "a library that loads today may be blocked tomorrow").

## What happened (MEASURED)

On the first real run of `scripts\start-jarvis.cmd --dashboard --voice-root ...` the voice did not start: `OSError: [WinError 4551] An Application Control policy has blocked this file`, naming `torch\lib\c10.dll` in the voice environment. JARVIS carried on in text, as designed. The CodeIntegrity log (event 3077) records the block at 13:12 that day. Smart App Control was on (`VerifiedAndReputablePolicyState` = 1). The same file loaded on 2026-11-14.

## What was ruled out (MEASURED)

- Not an operating system update: the last updates were on 2026-11-12, before the voice last worked.
- Not the memory-closing script: nothing it closes is involved.
- Not the network: Microsoft's reputation endpoints answered from this machine.
- The file itself is unsigned (Authenticode "NotSigned"). INFERRED: Microsoft's cloud reputation verdict for it changed. UNKNOWN: why, and whether it will change back.

## Which builds of torch load (MEASURED, each file fetched by range from the official wheel, its checksum or CRC verified, and loaded with the signed Python; nothing was installed into the working voice environment)

| Build | `c10.dll` | `torch_cpu.dll` | `torch_cuda.dll` | `torch_python.dll` |
|---|---|---|---|---|
| 2.10.0 (installed) | blocked | not tested | not tested | not tested |
| 2.9.1 | loads | no verdict (a dependency was missing in the partial test) | **blocked** | not reached |
| 2.9.0 | blocked | blocked | blocked | blocked |
| 2.8.0 | loads | no verdict | **blocked** | blocked |
| 2.7.1 | loads | no verdict | **blocked** | blocked |
| 2.7.0 | test hung twice; no verdict | | | |

A full `import torch` of 2.9.1 in a throwaway folder failed on `torch_cuda.dll` (event 3077). Result: **no tested torch build loads its CUDA library** while Smart App Control is on. Reputation does not follow age or popularity in a way that can be relied on, and it differs file by file inside one build.

## Other voice libraries right now (MEASURED)

`numpy`, `onnxruntime` and `soundfile` import; `transformers` (which imports torch) and `ctranslate2` are blocked. All three `onnxruntime` files (`onnxruntime.dll`, `onnxruntime_providers_shared.dll`, `onnxruntime_pybind11_state.pyd`) are Authenticode "Valid", signed by Microsoft Corporation, which Smart App Control trusts by signature. `numpy`'s core file is unsigned and loads only on reputation.

## What Microsoft's documentation says (read 2026-11-28; community threads are not official guidance)

- There is no per-file "allow anyway". A file must be signed by a trusted provider or known to Microsoft's cloud.
- Signing is not enough on its own: the cloud reputation is checked as well, and RSA signatures only are accepted.
- Microsoft's managed signing service is open to organisations in the USA, Canada, the EU and the UK and to individuals in the USA and Canada.
- Sources: Microsoft Learn "Code signing for Smart App Control"; Microsoft Q&A on a signed app still blocked; Microsoft support "Smart App Control has blocked part of this app".

## Ways forward (none chosen; each is RK's decision)

1. Keep Smart App Control on and replace the unsigned-binary voice with components Smart App Control accepts by signature: Windows' own speech (signed by Microsoft), or models run through the Microsoft-signed `onnxruntime` (numpy and a few small unsigned files would still depend on reputation). Costs the cloned voice. Needs an ADR-0012 amendment.
2. Wait and re-test (free, no promise).
3. Turn Smart App Control off, or run the voice inside WSL2. Both were advised against by the 2026-11-13 notes and RK's rule; sources disagree whether Smart App Control can be turned back on afterwards (UNVERIFIED).

## Not done

No change was made to the voice environment, to Smart App Control or to any firewall rule. The voice program's own network block (WinError 10013) was respected: downloads used Windows' signed `curl.exe` into a throwaway folder, which was emptied afterwards.
