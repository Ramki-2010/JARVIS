# TEMPORARY HANDOFF — why the conversation benchmark runs on the OLD laptop

**Status: TEMPORARY and NON-AUTHORITATIVE. Delete this file once the old-laptop benchmark is recorded and the governance changes below are merged or dropped.**

This note grants no authority. It cannot amend governance. If it conflicts with the Master Context, an accepted ADR or MCA, or RK's chat word, the record wins and this note is wrong. Written 2026-11-01 on `main` = `7afb07e`.

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

Old-laptop values were pasted by RK on 2026-11-01 (idle readings, no benchmark). New-laptop values were measured by Claude on the same date. Neither has any benchmark result yet. CUDA runtime version is not yet measured on either.

## RK decisions received in chat (not yet governance records)

- R1: fast push-to-talk conversational turns. Hands-free, wake word and barge-in stay excluded.
- R2: conversation is MANDATORY for Beta; it replaces the optional model-demo scope; the core control-plane path is unchanged; Galaxy expansion stays limited; no gate is weakened.
- R3: Option 1. Amend ADR-0013, add a one-sentence MCA-003, no ADR-0014.
- R8: hardware must be measured.

The proposed text is in two scratch documents outside the repo (conversational requirement analysis; conversation governance proposal, both dated 2026-10-31). They are proposals, not records.

## What is NOT done

- No ADR-0013 amendment, MCA-003 or Beta Plan Amendment 2 is drafted. RK has not approved drafting; RK wants the old-laptop inventory first.
- No benchmark has run on either laptop. No benchmark script exists.
- Nothing was installed. Installs and model downloads are RK's act (G-13).

## Next steps

1. RK opens a Claude session on the old laptop with a self-contained measurement-only prompt (Tier 0: read-only measurements into `D:\JARVIS-BENCH-OLD`; Tier 1: a proposal only, no installs without RK's yes). That laptop has no copy of this repo and does not need one.
2. RK pastes the resulting report to the main session.
3. The main session compares it with the new laptop, writes the benchmark specification, and waits for RK's explicit approval before drafting any ADR, MCA, gate, script or code.

## Do not

Touch `D:\JARVIS` or `E:\JARVIS-PROJECT`, create B-06 files, enable Stage B or D-12, or treat this note as approval for anything.
