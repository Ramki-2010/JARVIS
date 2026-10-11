# ADR-0001 — Authority Classification and Governance Flow

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0001 |
| Title | Authority Classification and Governance Flow |
| Status | ACCEPTED |
| Drafted | 2026-10-09, by Cloud Claude |
| Authority class | USER AUTHORITY REQUIRED (triggers G-01, G-02, G-12, G-17 of the checklist in D5) |
| Inputs | Master Context (`JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md`, unchanged). CP-0 Review — Final (F2, §6, §8.3, §10.2). Local CP-0 Fact Report 2026-10-09. |
| Related | ADR-0002, ADR-0003, ADR-0004, ADR-0005, MCA-001 (all ACCEPTED) |

**Labels used** (from the CP-0 review): `VERIFIED` · `UNKNOWN` · `MASTER CONTEXT POLICY` · `PROPOSED` · `USER AUTHORITY REQUIRED` · `LOCAL FACT CHECK REQUIRED` · `ENGINEERING AFTER CP-0`. A fact tagged `VERIFIED (LF-n)` was observed by Local Claude in the 2026-10-09 fact report.

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-11 |
| How the acceptance was given | A written instruction from the founder to Local Claude on 2026-10-11. Under ADR-0001 D6 that instruction is an input. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this document. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6: approval applies to the exact text accepted) |
| Accepted text includes | D9 and section 5 as corrected on 2026-10-11: the ruleset and CODEOWNERS requirements, and the administrator-token residual risk, which the founder accepts |
| Resulting change | docs/README.md and docs/decisions/README.md updated per section 9 of this ADR, in the same pull request |

---

## 1. Context

1. `MASTER CONTEXT POLICY` The Master Context is the authoritative technical/product specification. It says governance is enforced outside the model (§12, §13, §26) and that JARVIS must not grant itself permissions or modify governance (§12 L5, §26).
2. `VERIFIED` The existing `docs/README.md` states only that the Master Context wins over the Orientation on technical/product rules. It does not state a full hierarchy, does not place RK at the top, and does not place ADRs, contracts or task constraints.
3. `VERIFIED` The existing `docs/decisions/README.md` says Local Claude "may accept and implement ordinary engineering decisions" and that "an ADR may document an intentional interpretation or clarification of the Master Context." Under the first, the actor who wants to proceed also decides whether the matter is "ordinary". Under the second, an ADR can change the meaning of a higher layer. The CP-0 review (F2) finds both contrary to the package's own rule that lower layers never override higher ones.
4. `VERIFIED (LF-4)` `credential.helper` is `manager` on the build machine. A builder session can therefore push to GitHub using RK's stored credentials. `VERIFIED (LF-15, 2026-10-11)` `gh` 2.102.0 is installed and authenticated as the repository owner, with scopes `repo`, `workflow`, `read:org` and `gist`, and admin permission on `Ramki-2010/JARVIS`.
5. `VERIFIED (LF-1)` The builder session runs with `permissionMode: "auto"`. Before isolation exists (ADR-0002, MCA-001), every control in this ADR that depends on a Claude session behaving is convention, not enforcement.
6. `VERIFIED (LF-15 and GitHub facts, 2026-10-11)` The repository `Ramki-2010/JARVIS` is public. It has no ruleset, no rule applying to `main`, no branch protection on `main` (the branch reports `protected: false`) and no CODEOWNERS file at any standard location. Secret scanning and push protection are enabled. The controls in D9 therefore do not exist today.

## 2. Decision

### D1. Authority hierarchy `PROPOSED`

Highest first. A lower layer never overrides a higher layer.

| # | Layer | What it is |
|---|---|---|
| 0 | **RK** | The owner. Final authority. |
| 1 | **Master Context** | Authoritative technical/product specification. Changes only through an accepted MCA, which produces a new Master Context version. |
| 2 | **Orientation** | Conceptual rationale. Adds no requirements. |
| 3 | **Accepted ADRs** | Binding decisions below the Master Context. |
| 4 | **Project contracts** | Per-project permissions, JARVIS-side (ADR-0004). |
| 5 | **Task constraints** | Per-task limits supplied by RK for a task. |
| 6 | **Implementation** | Code, configuration and tests. |

Rules:

- **R1.1** Where two layers conflict, the higher layer wins. The lower item is void to the extent of the conflict, and the conflict is recorded.
- **R1.2** A lower layer may narrow what a higher layer permits. It may never widen it.
- **R1.3** Where a layer is silent, the default is deny, then ask RK.
- **R1.4** Contracts and task constraints narrow only. Effective authority is the intersection of policy, contract and constraints.
- **R1.5** Implementation is not an authority source. Behaviour that differs from an accepted ADR is a defect, not a decision.

Not layers, and never authority:

- **MCAs.** An MCA is a change record. An accepted MCA produces a new Master Context version. The new version is the authority. The MCA is its history. (Resolves F2.)
- **Planning and evidence documents.** Delivery plans, CP-0 reviews, gate packages, environment snapshots and fact reports are inputs. They have no authority (review §10.2).
- **Drafts.** A document marked PROPOSED has no force.

### D2. Master Context and Orientation `PROPOSED`

- The Master Context governs technical and product rules. The Orientation supplies rationale only.
- On conflict the Master Context wins. The Orientation cannot add a requirement, a permission or a prohibition.
- Both documents are version-controlled in the repository. The committed copies are the source of truth. Pasted or uploaded copies are never authoritative.
- The Master Context changes only by MCA acceptance (D4).

### D3. ADR authority `PROPOSED`

- An ADR is binding only after RK accepts it (D6).
- An ADR may implement the Master Context: choose among options it permits, add detail, or narrow it.
- An ADR may not widen, reinterpret or contradict Master Context text. If an ADR needs a change to the Master Context, the ADR cannot supply it. An MCA is required.
- Where the Master Context is ambiguous, the ADR states the ambiguity and defers to RK (D8). It does not resolve it silently.
- This replaces the rule that an ADR "may document an intentional interpretation or clarification of the Master Context."
- Superseded ADRs stay in history, marked superseded.

### D4. Master Context changes `PROPOSED`

- Only an MCA may change Master Context text. An MCA states: ID, affected section(s), current text, proposed text, rationale, security/architectural impact, compatibility impact, and RK's acceptance.
- On acceptance a new Master Context version is issued with the amended text. The MCA remains as the change record.
- Until RK accepts an MCA, the Master Context applies exactly as written.

### D5. Explicit governance-trigger checklist `PROPOSED`

A decision is **USER AUTHORITY REQUIRED** if any trigger matches. A trigger is matched by its literal text, not by judgement about whether it "really" matters.

| ID | Trigger |
|---|---|
| G-01 | Any change to Master Context text, its version, or its status |
| G-02 | Any change to the authority hierarchy, this checklist, the ADR process or acceptance rules |
| G-03 | Any capability definition, level mapping, verdict mapping, reason-code-to-verdict mapping, default, or Phase-1 enabled set |
| G-04 | Any change to policy files, contracts, project registrations, revocation entries, or protected-project designation |
| G-05 | Any security boundary: isolation, sandbox, accounts, ACLs, firewall, network or egress rules |
| G-06 | Privacy: what data leaves the machine, what is committed to the public repository, where the governance zone and data root are |
| G-07 | Credentials and secrets: creating, storing, scoping, rotating or using them; the permission mode of any Claude session that can modify the repository |
| G-08 | Spending or any cost commitment, including the zero-spend policy |
| G-09 | Registering a project, or modifying protected project content |
| G-10 | Irreversible or high-impact actions: push, merge, deploy, delete, publish, external communication, financial action |
| G-11 | Audit-model semantics: schema, hash chain, provenance classes, files-read scope, anchoring |
| G-12 | GitHub governance settings: rulesets, bypass list, CODEOWNERS, force-push or deletion protection, required reviews, anchor ref protection |
| G-13 | Installing, upgrading or removing software; changing Windows, Git or Claude configuration |
| G-14 | Worker-brief rules, or any authority a worker or session would hold |
| G-15 | Phase order, phase scope, exit criteria, or closing a checkpoint |
| G-16 | The meaning of task constraints or of narrowing |
| G-17 | Anything not listed here, or any doubt whether a trigger matches |

### D6. User authority and how it is expressed `PROPOSED`

- RK decides every matched trigger.
- An approval is effective only when recorded in the repository by RK: RK merges a pull request that changes the document's STATUS to ACCEPTED. A chat statement is input to that act. It is not the record.
- Approval is never inferred from silence, from a recommendation, from a Claude session's judgement, from a successful test, or from an unchallenged PR.
- Approval applies to the exact text accepted. A later edit to an accepted ADR needs a new acceptance.
- `UNKNOWN` Whether RK wants a different recording mechanism. This is RK's call.

### D7. No self-classification `PROPOSED`

- Neither Local Claude nor Cloud Claude classifies authority, accepts an ADR or MCA, or treats its own recommendation as approval.
- Classification is mechanical. Every ADR and PR carries a block: matched triggers (by ID), or the named engineering item (below).
- A Claude session records the match. That record is a claim. RK's merge confirms or corrects it.
- `ENGINEERING AFTER CP-0` applies only to a decision that is named in an accepted ADR's engineering list (for example E-1 to E-9 in the CP-0 review §6.2, once recorded in ADR-0003, -0004, -0005, -0006, -0002). A decision not named there is USER AUTHORITY REQUIRED.
- A named engineering item may be decided and implemented by Local Claude without per-item approval. It stops and escalates if the decision would touch any trigger.
- Roles: Local Claude owns local machine facts and implements within accepted ADRs. Cloud Claude proposes and reviews. Neither is an authority over governance.

### D8. Ambiguity defaults to RK `PROPOSED`

If it is unclear whether a trigger matches, whether a layer conflicts, or what the Master Context means, the decision is USER AUTHORITY REQUIRED and the actor stops. Doubt never resolves in favour of proceeding.

### D9. Repository governance controls `PROPOSED` `USER AUTHORITY REQUIRED` (G-12)

Current state: none of the controls below exists (Context item 6, VERIFIED 2026-10-11). They are requirements, not facts, until RK applies and verifies them. Applying them is an act of RK. Preparing the definitions is not applying them.

**Required controls on the default branch `main`** (one ruleset):

- A pull request is required to change `main`. Required approving reviews: 0, because there is one owner account (see the CODEOWNERS limit below).
- Force pushes are blocked (the non-fast-forward rule).
- Branch deletion is blocked.
- The bypass list is empty.
- Enforcement is active.

**CODEOWNERS.** A `.github/CODEOWNERS` file assigns the owner to the governance paths in force: `/docs/spec/`, `/docs/decisions/`, `/policy/` and `/.github/`. The CP-0 review names `policy/`, `docs/adr/` and `docs/master/`. The repository uses `docs/decisions/` and `docs/spec/`, and `/policy/` is reserved by ADR-0003 D6 and does not exist yet. The file routes each review request to the owner.

**CODEOWNERS enforcement limit (`PROPOSED`, to verify on GitHub).** The ruleset setting "require review from code owners" stays OFF while there is a single account. [Likely] GitHub does not let a PR author approve their own PR. With one account and an empty bypass list, a required code-owner review could then never be satisfied, and `main` would become unmergeable. Enforced CODEOWNERS needs a second reviewer identity. That is a decision for RK (Open items). Until then CODEOWNERS is a routing and visibility control, not a gate.

**Other expectations.**

- The anchor ref (ADR-0005 D7) has force-push and deletion protection. A ruleset that targets only `main` does not cover another ref.
- No Claude session changes rulesets, CODEOWNERS or the bypass list, merges a PR, or approves one.
- **Known limitation:** a builder session pushes under RK's credentials (LF-4). To GitHub, builder-authored and RK-authored changes look identical. What is real is RK's own merge act. The accepted residual risk is recorded in section 5.

## 3. Alternatives considered

| Alternative | Rejected because |
|---|---|
| Keep the existing rule: Local may accept ordinary engineering ADRs | The actor classifies its own authority. |
| Let ADRs "interpret" the Master Context | An ADR would change a higher layer. Contradicts R1.1 and review F2. |
| Put RK below the Master Context | RK owns the project and the Master Context. |
| Treat MCAs as a layer under the Master Context | An accepted MCA would then compete with the text it amends. Review F2. |
| Rely on CODEOWNERS alone for governance | Solo-owner limitation (D9). |

## 4. Evidence

- Master Context §12, §13, §26, §33, §36 (cited for policy). Sections quoted exactly in MCA-001.
- `VERIFIED` `docs/README.md` and `docs/decisions/README.md` on branch `docs/pre-phase-1-gate` (read in full).
- `VERIFIED (LF-1)` permission mode `auto`. `VERIFIED (LF-4)` credential helper `manager`. `VERIFIED (LF-15 and GitHub facts, 2026-10-11)` `gh` 2.102.0 authenticated with scopes `repo`, `workflow`, `read:org`, `gist` and admin permission; no ruleset, branch protection or CODEOWNERS.
- CP-0 Review — Final: F2, §5.1, §6, §8.3, §10.2.

## 5. Security impact

- Positive: removes the self-classification and ADR-interpretation paths. Makes acceptance a recorded, RK-only act.
- Residual: the build session shares RK's identity and credentials (LF-1, LF-4). Convention only until isolation.
- **Residual risk recorded for RK's acceptance (effective only on RK's recorded acceptance of this ADR, D6): the administrator token.** The `gh` login on the build machine holds the `repo` and `workflow` scopes and admin permission on the repository (LF-15, VERIFIED). The build session runs in mode `auto` (LF-1). Any process running as RK that can use that token can disable or edit the ruleset and its bypass list, add or remove CODEOWNERS, push to any unprotected ref, edit workflows, and create or merge a pull request. The ruleset is a process control and a tripwire against accidents and against a session that follows the rules. It is not a barrier against a session holding the token. The risk remains until isolation and credential separation exist. Options for RK, not decided here: keep the token, replace it with a narrower one for build sessions, or sign `gh` out when no pull-request operation is needed (G-07, G-12).

## 6. Complexity impact

Low. Documentation and a PR checklist. No code.

## 7. Reversibility

High. A later ADR supersedes this one. Changing the hierarchy is itself G-02.

## 8. Authority class

USER AUTHORITY REQUIRED. Triggers G-01, G-02, G-12, G-17.

## 9. Consequences

If accepted:

- `docs/README.md` and `docs/decisions/README.md` must be updated to match. The two rules quoted in Context item 3 are superseded. That update is itself G-02 and needs RK's acceptance.
- Every ADR template gains the classification block (D7).
- RK's GitHub check (review §8.3) becomes a recorded prerequisite before the first audit anchor push (ADR-0005). The state as of 2026-10-11 is in Context item 6.
- RK applies the D9 ruleset, or records that it is deferred, before the specification is frozen. The ruleset definition and CODEOWNERS text are prepared separately and are not applied by this ADR.
- Local Claude's role narrows to facts and implementation of named engineering items.

## 10. Open items

| Item | Label |
|---|---|
| Applying the D9 ruleset on `main` (pull request required, force push and deletion blocked, empty bypass list). Current state: none exists | `VERIFIED` absent 2026-10-11; applying it is `USER AUTHORITY REQUIRED` (G-12) |
| Whether to keep, narrow or sign out the admin-scope `gh` token for build sessions (section 5) | `USER AUTHORITY REQUIRED` (G-07, G-12) |
| CODEOWNERS paths: `/docs/spec/`, `/docs/decisions/`, `/policy/`, `/.github/` (D9) | `PROPOSED`, `USER AUTHORITY REQUIRED` |
| A second reviewer identity, so that "require review from code owners" can be enforced | `USER AUTHORITY REQUIRED` (G-12) |
| Whether `permissionMode: "auto"` is acceptable for the build session | `USER AUTHORITY REQUIRED` (G-07) |
| Recording mechanism for RK's approval (D6) | `USER AUTHORITY REQUIRED` |
