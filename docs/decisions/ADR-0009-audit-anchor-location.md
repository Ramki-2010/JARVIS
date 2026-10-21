# ADR-0009 — Audit-Anchor Location

**STATUS: PROPOSED — NOT ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0009 |
| Title | Audit-Anchor Location |
| Status | PROPOSED. Not accepted. No force until RK accepts it (ADR-0001 D6) |
| Drafted | 2026-10-21, by Local Claude, from RK's instruction to proceed with the recommended Decision 3 |
| Authority class | USER AUTHORITY REQUIRED (G-12, G-06) |
| Inputs | ADR-0005 D6, D7, §10. ADR-0001 D6, D9, G-06, G-12. ADR-0007 D6. `jarvis/store.py` (the `HEAD` file format). Live GitHub ruleset check of 2026-10-21 (`docs/environment/anchor-ref-verification-2026-10-21.md`) |
| Related | ADR-0001, ADR-0004, ADR-0005, ADR-0007 |
| Supplements | ADR-0005 D7 (decides what D7 left `UNKNOWN`: the carrying ref, the file path and the place of the verification record). No accepted ADR is amended |

**Labels:** `VERIFIED` · `UNKNOWN` · `PROPOSED` · `USER AUTHORITY REQUIRED` · `LOCAL FACT CHECK REQUIRED`.

## Governance-trigger classification (ADR-0001 D7)

- Matched triggers: **G-12** (which ref carries the anchor; a CODEOWNERS path is added), **G-06** (what is committed to the public repository).
- Named engineering item: none.
- This block is a claim by the drafting session. RK's merge confirms or corrects it.

---

## 1. Context

1. ADR-0005 D6: the audit `HEAD` is a small file holding only the sequence number and the record hash of the latest record. It is written to the data root.
2. ADR-0005 D7: RK copies `HEAD` into the public repository by hand, weekly. JARVIS opens no socket for this. The anchor counts as off-machine only once RK has recorded a verified ruleset that blocks force-push and deletion on the carrying ref, with an empty bypass list. Which ref carries it, and where the check is recorded, are left open. D7 names `docs/phase0/inventory.md` for the record. That path does not exist.
3. `VERIFIED` (2026-10-21, `docs/environment/anchor-ref-verification-2026-10-21.md`): the ruleset `protect-main` is active on the default branch `main`. It has the rules `deletion`, `non_fast_forward` and `pull_request`, an empty bypass list, and `current_user_can_bypass` is `never`. No ruleset covers tags. No ruleset covers any other branch.
4. `VERIFIED` `jarvis/store.py` writes `HEAD` as one line, `<seq> <64 lowercase hex>`, with a trailing newline.
5. `VERIFIED` The data root holds no `HEAD` file yet, so there is nothing to anchor today.
6. `VERIFIED` The repository is public.

## 2. Decision

All of D1 to D6 are `PROPOSED` `USER AUTHORITY REQUIRED` (G-12, G-06).

### D1. The carrying ref is `main`, through the normal pull-request workflow

- The anchor lives on `main`. It is added by a pull request that RK merges, like any other change.
- No new ruleset, branch or tag is created for the anchor. A dedicated branch or a tag would need a new ruleset, applied by RK (ADR-0001 D9). Tags are covered by no ruleset today.
- This satisfies the ADR-0005 D7 condition for `main`, as recorded in the verification note.

### D2. The anchor file

- Path: `audit-anchor/ANCHOR.txt`, at the repository root.
- Append-only. One line per anchor: the content of the data-root `HEAD` file, `<seq> <hash>`.
- A valid line matches `^[0-9]+ [0-9a-f]{64}$`. Nothing else is in the file. No timestamp is written, since the Git commit supplies the date.
- The file is created at the first anchor. This ADR creates no file.
- The line is audit-derived data inside the repository. It is the one authorised case that ADR-0007 D6 describes, and it does not widen that exception.

### D3. Who does what

- RK copies the `HEAD` line and merges the pull request (ADR-0005 D7). A Claude session should not author an anchor line, so that the anchor stays apart from the sessions whose work it checks.
- **This separation is procedure. It is not technically enforced.** While sessions use RK's GitHub credentials (ADR-0001 §5), a session can open and merge a pull request, and can edit the ruleset, and GitHub cannot tell it from RK. The ruleset requires a pull request but requires 0 approvals, code-owner review is off, and the account has administrator permission. The anchor therefore detects tampering by an actor that cannot use those credentials. It is not independent of a session or process running as RK.
- A session may check the format of a line RK has prepared, and may report a mismatch.

### D4. CODEOWNERS

`/audit-anchor/` is added to `.github/CODEOWNERS`, routed to the repository owner. This is routing and visibility only. "Require review from code owners" stays OFF (ADR-0001 D9).

### D5. Verification record

- The ADR-0005 D7 check is recorded as a dated note in `docs/environment/`. The first is `anchor-ref-verification-2026-10-21.md`, added with this ADR.
- This ADR designates `docs/environment/` as the place for the record. `docs/phase0/inventory.md`, which ADR-0005 D7 names, does not exist, and a folder named after a frozen phase is not used. RK's merge of this ADR and the note is the recorded check.
- **The check is repeated live in every anchor pull request.** The pull request description records: the default branch name; the `protect-main` ruleset id, `enforcement`, rule types and bypass list; the SHA of `main`; and the ruleset's `updated_at`.
- The baseline is the `updated_at` in `anchor-ref-verification-2026-10-21.md` (`2026-10-11T23:37:01.214+05:30`). A later `updated_at` that does not match a change RK made means the ruleset changed, and the anchor does not count as off-machine until the change is explained and the check is recorded again.
- This is a detective control. It does not stop a ruleset edit.

### D6. When the first anchor is pushed

- ADR-0005 D7 says "weekly, from Phase 1". With no `HEAD` file there is nothing to anchor. The first anchor is pushed when the data root holds a `HEAD` file, and the weekly cadence runs from then.
- The open item "tool to scan a commit for personal data before pushing HEAD" (ADR-0005 §10) is met by the D2 format check, because a valid line holds only a number and a hash.

## 3. Alternatives considered

| Option | Why not chosen |
|---|---|
| A dedicated branch | Needs a new ruleset with the same protections, applied by RK. No gain over a weekly pull request. |
| A tag | No ruleset covers tags today. Not a verified anchor without a new ruleset. |
| Keep the anchor off GitHub | Defeats the purpose: ADR-0005 D7 needs a public copy that an actor without GitHub credentials cannot rewrite. |
| Put the verification record in `docs/phase0/` | Creates a folder named after a frozen phase for one note. |

## 4. Evidence

- `VERIFIED` ruleset, branch protection, default branch and visibility: `docs/environment/anchor-ref-verification-2026-10-21.md` (live `gh api` results, 2026-10-21T14:11Z).
- `VERIFIED` HEAD format: `jarvis/store.py`, `_write_head` and `read_head`.
- ADR-0005 D6, D7, §10. ADR-0001 D6, D9. ADR-0007 D6.

## 5. Security impact

- The anchor proves that a record at or before the anchored sequence number was not rewritten, if the public copy was not also rewritten (ADR-0005 D7, D10). On `main` that needs the ruleset to stay in force. The check is repeated on change (D5).
- Known limitation (ADR-0001 D9, §5): a build session pushes under RK's credentials, so to GitHub a session's change and RK's look the same. Independence of the anchor from sessions is **procedural, not technically enforced**: a session using those credentials can author and merge an anchor pull request, and can change the ruleset. What the ruleset enforces is a required pull request, no force-push, no deletion and an empty bypass list (configuration verified; enforcement not tested).
- The decision on narrowing or removing session access to RK's GitHub credentials is not made here. It stays open (ADR-0001 §10; G-07, G-12).
- Records after the last anchor, up to a week of activity, remain rewritable without detection (ADR-0005 D10).

## 6. Complexity impact

Low. One file, one CODEOWNERS line, one dated note, one pull request a week once the store has records.

## 7. Reversibility

High before the first anchor. After it, anchor lines stay in Git history. A different carrying ref would need a superseding ADR (G-12).

## 8. Authority class

USER AUTHORITY REQUIRED. Triggers G-12, G-06.

## 9. Consequences

- `audit-anchor/` does not exist until the first anchor.
- The `.github/CODEOWNERS` change (D4) takes effect when RK merges.
- RK takes on the weekly pull request once the store holds records (ADR-0005 §9).
- If `main`'s ruleset is weakened or the default branch changes, the anchor no longer counts as off-machine until the check is repeated.

## 10. Open items

| Item | Label |
|---|---|
| Whether to narrow or remove session access to RK's GitHub credentials (the `gh` login and Git credential manager) | `USER AUTHORITY REQUIRED` (G-07, G-12). ADR-0001 §10. Not decided here |
| The first anchor and the first `HEAD` file | Not before the store holds records |
| Whether to test enforcement by an attempted force-push on a scratch ref | `UNKNOWN`, `USER AUTHORITY REQUIRED`. Not done: it could damage the protected branch if the ruleset were wrong |
| Backup of `D:\JARVIS\` | `UNKNOWN`, `USER AUTHORITY REQUIRED` (ADR-0007 §10) |
