# JARVIS — START HERE

Session recovery and orientation for a fresh Claude session. It tells you where to look and what to verify. It does not tell you what is decided.

## BOOT SEQUENCE

This document is a navigation and continuity aid. It grants no authority.

It cannot amend governance, and it cannot override RK, the Master Context, accepted ADRs, accepted MCAs, project contracts or repository governance. It holds pointers and procedures, not architecture and not task state. If it conflicts with an accepted record, the record wins and this file is wrong.

## AUTHORITY CHECK

The authority rules are defined in `docs/decisions/ADR-0001-authority-classification-and-governance-flow.md` and are not repeated here:

- **D1:** the authority hierarchy.
- **D6:** how RK's approval is expressed and recorded.
- **D9:** repository governance controls, and what no Claude session may do.

Continuity rules that add to it:

- Reports are evidence, not authority.
- Repository state beats any report.
- UNKNOWN remains UNKNOWN. Mark it, and do not fill it in.
- Do not reconstruct uncertain history from memory. Locate the record, or stop and ask RK.

## RESUME PROTOCOL

1. Read this file, then `CLAUDE.md`, then `docs/README.md`.
2. Establish live repository state:
   ```bash
   git status --short --branch
   git branch --show-current
   git log --oneline -n 10
   git tag -n
   git ls-remote --tags origin
   gh pr list --state open
   ```
3. Check what changed since the last gate: `git diff --stat phase-0-freeze..origin/main`.
4. Check the governance controls still in force: `gh api repos/{owner}/{repo}/rulesets`.
5. Locate the Master Context and read the sections your task touches.
6. Read the ADR register in `docs/decisions/README.md`, then any ADR or MCA relevant to the task.
7. Verify anything material that is not in an accepted record. Treat what remains unresolved as UNKNOWN.
8. Resume only within the authority actually established. If it is unclear whether a decision is yours to make, ADR-0001 D8 applies: stop and ask RK.

## WHERE THINGS LIVE

| What | Path | Status |
|---|---|---|
| Master Context | `docs/spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md` | Authoritative |
| Orientation | `docs/spec/JARVIS_AI_LLM_PROJECT_ORIENTATION.md` | Conceptual context |
| Accepted ADRs and register | `docs/decisions/` (start at `README.md`) | Authoritative once ACCEPTED |
| MCA records | `docs/decisions/MCA-*.md` | Authoritative once ACCEPTED |
| Environment snapshot | `docs/environment/phase-0-2026-10-06.md` | Historical evidence |
| Architecture draft | `docs/architecture/` | DRAFT — NON-AUTHORITATIVE. Merged to `main` in PR #5; it is absent at `phase-0-freeze`. Merging it accepted no decision in it. Verify with `git log -- docs/architecture/`. |
| Phase 1 control plane | `jarvis/`, `tests/`, `policy/policy.toml` | Implementation in progress, not complete. Policy changes are RK's decision (G-03). Tests: `py -3.14 -m unittest discover -s tests -t .` |
| Source repository | `D:\J.A.R.V.I.S AI Assistant\` | Code and version-controlled documentation only |
| External operational storage | `D:\JARVIS\` (`governance\`, `data\`) | Outside the repository, never a repository folder. Governed by ADR-0007. Creating it is a separate step: verify live whether it exists |
| Governance controls | `.github/CODEOWNERS` and the GitHub ruleset | Verify live; do not rely on this file |

## STATE AT LAST GATE

- Tag: `phase-0-freeze`
- Commit: `e919b7a2402a9a2364491e31fe4b25a12866f87e`
- Phase 0 baseline: frozen at `phase-0-freeze`.
- Phase 1: not started at the gate. It started later, on RK's instruction (2026-10-21), and is not complete. Read its current state from `git log` and the code, not from this file.

This records the gate only. Anything after it is discovered with the RESUME PROTOCOL, not read from here.

## BEFORE YOU STOP

- Leave the repository in a state the next session can read: no uncommitted work you have not reported, and no unreported branch or open PR.
- State what you did, what you verified, what you did not verify, and what is UNKNOWN. Name the evidence.
- Session handoff notes are evidence for the next session, not authority, and they must not be committed as a tracking system.
- Handoff location (Claude Code sessions only): Claude Code's per-project memory folder under the user profile, outside the repository. It is machine-local and is not available to Codex, Antigravity or JARVIS as a handoff channel; JARVIS cannot read it, because that folder is on the policy's secret-location list. RK approved it on 2026-10-21 as part of the recommended plan, not as a separate explicit decision. No accepted ADR or record decides the handoff location (ADR-0007 section 10 lists it as not decided). Other agents and later sessions continue from committed files and Git and PR state only. Do not create a handoff directory, and never create one inside the repository (ADR-0007).
