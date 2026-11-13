# New laptop (AR_1309): Beta build evidence, 2026-11-13

**Status: evidence record, NON-AUTHORITATIVE.** It grants no authority. Accepted ADRs, MCAs and RK's chat word win. Written by Local Claude on the new laptop. Every line is marked MEASURED (Local Claude ran it and saw the result), RK DECISION (RK said it in chat), INFERRED, ESTIMATE, or UNVERIFIED / UNKNOWN. Nothing here is `VERIFIED` in the JARVIS sense (there is no independent verifier in the Beta).

Machine: ASUS TUF Gaming F16, i7-14650HX, 31.6 GiB RAM, RTX 5070 Laptop 8151 MiB, Windows 11 Home 10.0.26300. RK decided on 2026-11-13 that this is the single Beta machine.

## 1. Repository state

`main` at `06e65e3` (after PR #61). Test suite 463 tests, OK, 1 skipped (MEASURED). No open pull requests. The GitHub ruleset `updated_at` is unchanged since Phase 0 (MEASURED, first half of B-12).

## 2. What was built and merged this period

| PR | What |
|---|---|
| #56 to #59 | Acceptance records: ADR-0001 Amendment 1 (installs by a session on RK's per-item chat approval), ADR-0012 Amendment 1 (a session may use an RK-supplied local voice sample), ADR-0013 Amendment 1 (conversation), MCA-003, Beta plan Amendment 2, Master Context 0.1-r3. |
| #60 | A character the console cannot print is shown as an escape instead of crashing piped output. One new test. |
| #61 | Stage A read-only dashboard and status ring (ADR-0011): localhost only, per-run token, exact Host and Origin check, GET only, strict content-security policy, 17 tests. The interaction child process uses `-E -s -m jarvis` (ADR-0011 Amendment 1). |

## 3. Real install on this machine (MEASURED)

`D:\JARVIS` holds governance (`jarvis.toml`, `revocations.toml`, `registry.toml`, a contract), data and the audit chain. Project `jarvis` points at a shallow clone at `E:\JARVIS-PROJECT\workspace`. `audit verify` is OK at tail 29 and `doctor` is OK with 0 warnings. Governance files were hash-compared before and after the B-06 run and did not change.

- **B-06 (end-to-end workflow on the real install): PASSED** with the real registry and contract. The five tasks left blocked by earlier attempts were cancelled on RK's word; the dashboard ring now reads CANCELLED (a real ADR-0011 state), not WAITING.
- **B-02 (fresh-clone full suite): dry run done** on this machine. The final run is planned at release-candidate freeze.
- **First backup** taken to `E:\JARVIS-BACKUPS\2026-11-13`.
- **B-10 clean-machine runbook** written (outside the repository for now).

## 4. Voice (ADR-0012), installed on RK's per-item approval (ADR-0001 A1)

Layout under `D:\JARVIS\voice\`: a Python 3.10 virtual environment (separate from the 3.14 control plane, ADR-0012), a **private copy of Python 3.10** (`python310`, 97 MB, copied 2026-11-13 so a firewall rule can name it without touching RK's other projects), models (`kokoro`, `whisper\small.en`, `voxcpm2`), the RK sample and its first-10-seconds cut, output clips and an `INSTALL_RECORD.md`.

- **Cloned voice:** VoxCPM2 (Apache-2.0, about 2B parameters), cloned once from RK's local sample with `build_prompt_cache` and reused. RK chose the **4-step setting, line 1 clip** (`clone_4steps_line1.wav`). `voice_settings.json` holds 4 steps, guidance 2.0, streaming on. RK confirmed "line 1"; the 4-step reading of "number 4" was Local Claude's interpretation and RK did not contradict it.
- **Speed (MEASURED, GPU, voice alone):** speech is made at about real time (rtf 1.03 at 4 steps). With streaming, the first 0.16 s piece of audio is ready about 0.13 to 0.16 s after the voice receives text, and later pieces keep pace (0.16 s of audio per about 0.15 s). With a half-second playback buffer it should sound continuous (continuity as heard by RK: UNVERIFIED until the conversation loop exists).
- **Rejected settings (MEASURED):** guidance 1.0 broke the speech (a 2 s sentence became 6 s). Fewer than 4 steps gave no useful gain. Do not use them.
- **Fallback voice:** Kokoro (British voices such as bm_george), fast, on CPU, not cloned.
- **Speech to text:** faster-whisper small.en on CPU, int8.
- **Sample provenance:** RK described the sample two ways (a voice RK trained; a Fish Audio library voice reading film dialogue). Both statements are kept; status UNVERIFIED (ADR-0012 Amendment 1).
- **Smart App Control (INFERRED from the failures):** newest unsigned library builds are blocked, older pinned ones pass. Pins in use: `torch==2.10.0+cu128`, `av 16.0.1`, `numba 0.61.2`, `llvmlite 0.44.0`. Do not upgrade pinned packages without re-testing. Triton is not needed (`optimize=False`).
- **Unplanned download, removed:** VoxCPM fetched a 19 MB denoiser into a ModelScope cache on `C:`. RK approved removal and it was done; clips now load with the denoiser off.

## 5. Language model (ADR-0013)

Ollama v0.40.16 portable under `D:\JARVIS\ollama` (SHA-256 in its install record, publisher signature Valid), models under `D:\JARVIS\models\ollama`, served only on `127.0.0.1:11434`. **RK chose `qwen3.5:9b`** (Q4_K_M, 6.6 GB, Apache-2.0) as the conversation model on 2026-11-13. The approved model list is RK's governance file (ADR-0013 D3) and is not yet written: RK DECISION pending.

Benchmark (one run per prompt, MEASURED): 9B on CPU about 10.7 tok/s, first token 1.2 s; 9B on GPU about 45 tok/s, first token 0.13 s; 4B on CPU about 18 tok/s. Quality was judged on three prompts only and is not a measurement: the 4B model made a false claim and odd assumptions, the 9B stayed honest.

## 6. Sharing the GPU between model and voice (MEASURED)

The cloned voice holds about 5.75 GiB of the 8 GiB GPU. The 9B model needs about 6.6 GB. They cannot both fit.

| 9B model setting while the voice generates | Model speed | Voice speed (1.0 = real time) |
|---|---|---|
| CPU only | 9.4 tok/s | 1.1 to 1.7 |
| 14 layers on GPU | 7.2 tok/s | up to 3.2 |
| automatic split | 2.4 tok/s | up to 7.2 |

A first reading of 36 tok/s for the automatic split was misleading. A plausible cause is Windows moving GPU memory into system RAM when the GPU is oversubscribed (INFERRED, not isolated). **RK DECISION: Setup A** (9B on CPU, cloned voice on GPU, CPU as the fallback). Setup B (9B on GPU, Kokoro on CPU) stays an option if speed matters more than the cloned voice. Estimated time to first spoken word is about 2 s; this is an ESTIMATE until the conversation loop is measured end to end.

## 7. Outbound firewall rule (D-13), applied by RK on 2026-11-13

RK ran `D:\JARVIS\firewall\jarvis-firewall-on.ps1` as administrator (G-05 is RK's act). It creates three outbound Block rules in group `JARVIS-D13`, one per program: the private Python copy, the voice venv launcher, and `ollama.exe`. Local Claude then tested (MEASURED):

- The voice venv Python and the private Python: a connection to an internet address failed with `PermissionError`.
- `ollama pull` failed with a socket access error (blocked).
- RK's ordinary Python 3.10 and Python 3.14: internet connections still worked, so RK's other projects are not affected.
- Loopback: the blocked voice Python reached the blocked Ollama on 127.0.0.1 and listed both models. One first try timed out while the server was still starting; a retry after waiting worked.
- The cloned voice still loads and speaks with the rules on (models load from disk).

Undo (administrator): `jarvis-firewall-off.ps1` switches the rules off, `-reenable.ps1` switches them on, `-remove.ps1` deletes them. The off switch is needed for any model download or `pip install`. The scripts live in `D:\JARVIS\firewall` (outside the repository). The rules block these programs by path; they do not stop other programs, and a program renamed or copied elsewhere is not covered.

## 8. Decisions RK made on 2026-11-13 (RK DECISION, chat)

1. Merge PR #61 (done).
2. ADR-0010 implementation deviations (Security notes section 4): "proceed with the limitations", i.e. accepted as documented limitations; no ADR text amended.
3. B-11 anchor: **no GitHub sign-out**; the limitation is stated in the release notes; RK makes the first anchor around 25 November.
4. Clone voice: 4 steps, line 1.
5. Remove the B-06 blocked tasks (done).
6. Model `qwen3.5:9b`.
7. Setup A.
8. Firewall rule, applied.
9. B-12 wording: Local Claude words it (Security notes section 5).

## 9. Still open

- Approved model list (RK's governance file).
- Old-laptop role and checks: see `docs/plans/OLD_LAPTOP_NEXT_STEPS_2026-11-13.md`.
- Build next: Stage B (note add and task create from the UI, with a confirmation turn), the read-only galaxy, the intent layer, the conversation loop with streaming voice, end-to-end timing, security review of `ui/`, `voice/` and `advisor/`, final B-02, B-10 on a clean machine, B-11 anchor.
- Optional cleanups needing RK's word: the Ollama identity and cache folder under the user profile (`.ollama`), the throwaway `D:\JARVIS\voice\sactest` folder.
