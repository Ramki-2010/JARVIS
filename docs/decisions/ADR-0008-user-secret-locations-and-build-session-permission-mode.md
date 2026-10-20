# ADR-0008 — Initial User-Secret Locations and Build-Session Permission Mode

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0008 |
| Title | Initial User-Secret Locations and Build-Session Permission Mode |
| Status | ACCEPTED |
| Drafted | 2026-10-21, by Local Claude, from RK's written instructions of the same date |
| Authority class | USER AUTHORITY REQUIRED (G-07; G-03 for the policy content in D1) |
| Inputs | ADR-0002 §1 item 3, §10. ADR-0003 D2, D3, D6, §10. ADR-0004 D2, D3, §10. ADR-0006 §3.3. ADR-0007 §10. Master Context §13, §26, §40.8. Local read-only check of 2026-10-21 (section 4) |
| Related | ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0006, ADR-0007 |
| Resolves | The open item "Initial user-secret location list" (ADR-0003 §10, ADR-0004 §10, ADR-0007 §10) and the open item "Whether `permissionMode: "auto"` is acceptable while Phase 1 is built" (ADR-0002 §10). No accepted ADR is amended |

**Labels:** `VERIFIED` · `UNKNOWN` · `MASTER CONTEXT POLICY` · `PROPOSED` · `USER AUTHORITY REQUIRED` · `LOCAL FACT CHECK REQUIRED` · `ENGINEERING AFTER CP-0`.

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-21 |
| How the acceptance was given | Written instructions from the founder to Local Claude on 2026-10-21: to make the required changes for the initial secret-location list and the session permission mode, and the answer "Keep auto" to the permission-mode question. Under ADR-0001 D6 those instructions are inputs. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this document. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request |
| Still open | The policy file that carries the D1 list (ADR-0003 D6) is not created here. The canonicalizer that applies it (ADR-0003 D3, E-3) is not implemented here |

## Governance-trigger classification (ADR-0001 D7)

- Matched triggers: **G-07** (D1: which credential locations are protected; D2: the permission mode of a Claude session that can modify the repository) and **G-03** (D1 is content of the policy's secret-location list, ADR-0003 D2).
- Named engineering item: none. Matching mechanics in D1 are left to E-3.
- This block is a claim by the drafting session. RK's merge confirms or corrects it.

---

## 1. Context

1. `MASTER CONTEXT POLICY` ADR-0003 D2 defines the always-DENY target class `USER_SECRET_LOCATION`: ".ssh, browser profiles, credential stores, tool credential directories under the user profile, and anything on the policy's secret-location list". The exact Windows paths were left `UNKNOWN` and `USER AUTHORITY REQUIRED` (ADR-0003 §10, ADR-0004 §10, ADR-0007 §10).
2. The repository is public. A list containing the real user name or profile path would publish it. Committed documents use placeholders.
3. ADR-0006 §3.3: the control plane reads no environment variable that influences behaviour. The user-profile location therefore cannot come from `%USERPROFILE%` at run time.
4. ADR-0002 §1 item 3 recorded the build session's permission mode as `auto` (LF-1). ADR-0002 §10 left open whether that is acceptable while Phase 1 is built.
5. `MASTER CONTEXT POLICY` §40.8: "A permission prompt is not a security boundary."

## 2. Decision

All of D1 to D3 are `PROPOSED` `USER AUTHORITY REQUIRED`.

### D1. Initial user-secret location list

Every entry is relative to `<USER_HOME>`, the user's profile directory. A target whose canonical path equals an entry, or lies inside it, is classified `USER_SECRET_LOCATION` and is always DENY for every capability (ADR-0003 D2, D9 step 7, reason `TARGET_USER_SECRET`).

| Group | Entries under `<USER_HOME>` |
|---|---|
| SSH and signing keys | `.ssh`, `.gnupg` |
| Git and generic credentials | `.git-credentials`, `.netrc`, `_netrc` |
| Developer and cloud tool credentials | `.aws`, `.azure`, `.config\gcloud`, `.kube`, `.docker`, `.npmrc`, `.pypirc`, `.config\gh`, `AppData\Roaming\GitHub CLI` |
| AI tool credentials and configuration | `.claude`, `.claude.json`, `.codex`, `AppData\Roaming\Claude` |
| Windows credential and key stores | `AppData\Roaming\Microsoft\Credentials`, `AppData\Local\Microsoft\Credentials`, `AppData\Roaming\Microsoft\Protect`, `AppData\Roaming\Microsoft\Vault`, `AppData\Local\Microsoft\Vault`, `AppData\Roaming\Microsoft\Crypto` |
| Browser profiles | `AppData\Local\Google\Chrome\User Data`, `AppData\Local\Microsoft\Edge\User Data`, `AppData\Local\BraveSoftware\Brave-Browser\User Data`, `AppData\Roaming\Mozilla\Firefox\Profiles`, `AppData\Roaming\Opera Software` |

Rules:

1. **Where the list lives.** The entries above are policy content. They are carried by the policy file in the repository (ADR-0003 D6), with the `<USER_HOME>` placeholder, never the real path.
2. **Where `<USER_HOME>` comes from.** The control-plane configuration in the governance zone supplies it (ADR-0004 D2). It is never read from an environment variable (ADR-0006 §3.3).
3. **Matching.** Containment uses the ADR-0003 D3 rules: canonical paths, case-normalised, `commonpath` containment, so a sibling sharing a name prefix does not match. An entry that does not exist on the machine still matches by its normalised absolute form. The exact algorithm is `ENGINEERING AFTER CP-0` (E-3).
4. **The list only narrows.** It adds always-DENY targets. It never allows anything.
5. **Changes.** Adding, removing or editing an entry is a policy change (G-03) and a credential decision (G-07), made only by RK.

### D2. Build-session permission mode

1. Claude Code sessions that build JARVIS Phase 1 run in the `auto` permission mode. RK decided this on 2026-10-21.
2. No session uses the mode that skips permission checks (`bypassPermissions`).
3. No session changes its own permission mode, permission rules or settings. A change is RK's act, made in the app (G-07).
4. Changing the recorded mode is `USER AUTHORITY REQUIRED` (G-07).

### D3. What the permission mode is not

- The permission mode is not a security boundary (Master Context §40.8). Every mode runs as RK, with RK's file access and credentials (ADR-0002 §5).
- In `auto` mode the harness may ask for approval of some actions. That check is a safeguard, not a guarantee.
- Isolation remains a Phase 3 matter (MCA-001). Nothing in this ADR claims it.

## 3. Alternatives considered

| Option | Why not chosen |
|---|---|
| Put real profile paths in the list | Publishes the user name and profile layout in a public repository |
| Read the profile location from `%USERPROFILE%` at run time | Violates ADR-0006 §3.3 (no behaviour-influencing environment reads) |
| Default mode (ask before every edit and command) for build sessions | RK chose to keep `auto`. A prompt is not a boundary either (§40.8) |
| Accept-edits mode | RK chose to keep `auto` |
| Defer both items | They block the canonicalizer (X-09, X-16) and leave an ADR-0002 open item unanswered |

## 4. Evidence

- `VERIFIED` (Local read-only check, 2026-10-21, app session metadata): the build session's permission mode is `auto`.
- `VERIFIED` (same check): Remote Control is enabled for the build session, so it can also be driven from RK's other devices. Recorded as a fact. Not decided here.
- `VERIFIED` The repository is public (GitHub API, 2026-10-21).
- ADR-0003 D2, D3, D6, §10; ADR-0004 D2, §10; ADR-0006 §3.3; ADR-0007 §10; ADR-0002 §1, §5, §10; Master Context §40.8.

## 5. Security impact

- D1 makes JARVIS task actions deny these locations by classification. It does not stop any other process running as RK from reading them, and it does not protect a location missing from the list.
- D2 keeps the current residual risk recorded in ADR-0002 §5: a build session running as RK can do anything RK can. The mode reduces mistakes; it does not isolate.

## 6. Complexity impact

Low. One list carried in the policy file and one configuration value. No new mechanism.

## 7. Reversibility

High. The list changes by a policy change. The mode changes in the app by RK.

## 8. Authority class

USER AUTHORITY REQUIRED. Triggers G-07 and G-03.

## 9. Consequences

- The policy file, when created (ADR-0003 D6), carries the D1 list.
- The control-plane configuration gains a `<USER_HOME>` value for the canonicalizer.
- Tests X-09 and X-16 include at least one entry from each D1 group, a non-existent entry, and a sibling with a shared name prefix.
- The ADR-0002 §10 item on the permission mode is answered by D2.

## 10. Open items

| Item | Label |
|---|---|
| Creation of the policy file carrying D1 | `USER AUTHORITY REQUIRED` (G-03), by pull request |
| Canonicalizer implementation and matching details | `ENGINEERING AFTER CP-0` (E-3) |
| Secret locations outside `<USER_HOME>`, and password-manager data locations | `UNKNOWN`. Not listed here. Adding them is G-07 |
| Whether Remote Control should stay enabled for build sessions | `UNKNOWN`, `USER AUTHORITY REQUIRED` (G-07). Not decided here |
