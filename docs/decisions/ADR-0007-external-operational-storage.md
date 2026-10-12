# ADR-0007 — External Operational Storage

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0007 |
| Title | External Operational Storage |
| Status | ACCEPTED |
| Drafted | 2026-10-12, by Local Claude, from RK's written instruction of the same date |
| Authority class | USER AUTHORITY REQUIRED (G-06) |
| Inputs | ADR-0004 D1, D2, D3, §9, §10. ADR-0003 D2, D6. ADR-0005 D1, D3, D6, D7. ADR-0006 §4. ADR-0002 D1. Master Context §6.2, §17, §18. Local read-only checks of 2026-10-12 (section 4) |
| Related | ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006 |
| Supplements | ADR-0004 D2 (decides the physical paths that ADR-0004 left `UNKNOWN`). No accepted ADR is amended |

**Labels:** `VERIFIED` · `UNKNOWN` · `MASTER CONTEXT POLICY` · `PROPOSED` · `USER AUTHORITY REQUIRED` · `LOCAL FACT CHECK REQUIRED`.

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-12 |
| How the acceptance was given | A written instruction from the founder to Local Claude on 2026-10-12: "ACCEPT ADR-0007 AS WRITTEN." Under ADR-0001 D6 that instruction is an input. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this document. Effective only when RK merges it (ADR-0001 D6). Once merged, this ADR is authoritative |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6: approval applies to the exact text accepted) |
| Accepted text includes | D1 to D8: the locations `D:\JARVIS\governance\` and `D:\JARVIS\data\`, the principle, the repository-versus-external distinction, the `.gitignore` rule, the logical-names clarification, the audit-anchor exception, the test rule and the registry consequence |
| Relationship to other records | Supplements ADR-0004 D2 by resolving the physical locations that ADR-0004 left `UNKNOWN`. No accepted ADR is amended. The text of ADR-0004, ADR-0005 and ADR-0006 is unchanged, including their own open-item lists |
| Master Context | Not amended. No MCA is created (D5) |
| Still open | Creation of `D:\JARVIS\` and the two directories, and the LF-14 re-check, are a separate later action on RK's instruction. The user-secret location list, the audit-anchor ref, path and verification record, the session-handoff location, the layout of `memory/`, backup, and 8.3 short-name behaviour are not decided here (section 10) |

## Governance-trigger classification (ADR-0001 D7)

- Matched triggers: **G-06** (where the governance zone and data root are).
- Named engineering item: none.
- Not decided here, and not matched by this change: G-07 (secret-location list), G-12 (audit-anchor ref).
- This block is a claim by the drafting session. RK's merge confirms or corrects it.

---

## 1. Context

1. `MASTER CONTEXT POLICY` ADR-0004 D2, accepted 2026-10-11, requires the governance zone and the data root to be outside every git working tree, outside every registered project root and the JARVIS repository working tree, and not in a cloud-synced folder. Their physical paths were left `UNKNOWN` (ADR-0004 §10), to be chosen before Phase 1 writes anything (ADR-0004 §9).
2. ADR-0006 §10 condition 3 and ADR-0005 §10 carry the same open item.
3. No accepted text states that a directory inside the repository, hidden by `.gitignore`, fails that requirement. The requirement implies it. This ADR makes it explicit.
4. The Master Context uses relative names for the registry (`projects/`, §6.2), memory (`memory/`, §17) and audit (`audit/`, §17; §18). It gives no physical location for them.
5. RK decided on 2026-10-12 that JARVIS operational state lives in a separate storage tree. This ADR records that decision.

## 2. Decision

All of D1 to D8 are `PROPOSED` `USER AUTHORITY REQUIRED` (G-06).

### D1. Locations

| Role | Path |
|---|---|
| JARVIS source repository | `D:\J.A.R.V.I.S AI Assistant\` |
| External operational storage tree | `D:\JARVIS\` |
| Governance zone (ADR-0004 D2) | `D:\JARVIS\governance\` |
| Data root (ADR-0004 D2) | `D:\JARVIS\data\` |

`D:\JARVIS\` is a separate operational storage tree. It is not part of the repository. The two paths above are the physical locations that ADR-0004 left `UNKNOWN`.

### D2. Principle

> JARVIS operational state and persistent runtime data live outside the Git repository and all registered project roots. Repository-controlled source code, documentation, policy definitions, and explicitly authorized audit-anchor material remain version-controlled exceptions.

This is an architectural boundary, not a privacy convention.

### D3. What belongs where

| Belongs in the repository (version-controlled) | Belongs in the external tree |
|---|---|
| Source code. Documentation. ADRs. The Master Context. Policy definitions (ADR-0003 D6; ADR-0004 D2 table). Audit-anchor material only as stated in D6 | In `governance\`: contracts, project registry, revocation list, control-plane configuration, spend policy, other protected governance state (ADR-0004 D2). In `data\`: the SQLite store, task state, audit data and exports, audit `HEAD` material, reports, other runtime state the architecture explicitly authorises (ADR-0004 D2, ADR-0005 D1, D3, D6) |

- "Operational state" means the right-hand column. Files a language runtime generates inside the working tree, such as bytecode caches, hold no JARVIS operational state and are not covered by this ADR.
- This ADR does not say that every future JARVIS file belongs in `governance\` or `data\`. A new category of file needs its own accepted decision.
- Anything not in the right-hand column that is not stated here is `UNKNOWN`, and a session asks RK. It is not placed in the repository by default.

### D4. `.gitignore` does not make a repository-local directory compliant

- A directory inside the JARVIS repository working tree does not satisfy ADR-0004 D2, whether or not Git ignores it.
- `.jarvis/`, `.jarvis/local/`, `data/`, `governance/`, `audit/`, `runtime/`, `state/`, and any equivalent operational directory inside the repository are **not** alternative storage locations. This includes hidden or renamed variants.
- No session may justify repository-local operational state by adding or relying on a `.gitignore` entry.
- A change to this decision needs a superseding ADR (G-06).

Why `.gitignore` does not count. It only stops an accidental commit. It does not prevent deletion by commands such as `git clean -x` or a hard reset, or a forced add. It does not separate the three always-DENY target classes `JARVIS_SELF`, `GOVERNANCE_ZONE` and `DATA_ROOT` (ADR-0003 D2). It puts the authority files in the directory a worker's patch can change (ADR-0004 §1 item 3).

### D5. Logical names in the Master Context

The names `projects/` (§6.2), `memory/` and `audit/` (§17), and the audit record store of §18 are **logical architectural names**. The Master Context gives no physical location for them. Their physical operational locations are governed by D1 to D4. No repository folder with such a name is operational storage.

- This ADR details the Master Context. It does not amend it and creates no MCA.
- The physical layout of `memory/` is not decided here. That layout is a later-phase matter (Master Context §17), and where it holds operational state it falls under this boundary.

### D6. Audit-anchor exception (ADR-0005 D7)

ADR-0005 D7 has RK commit a copy of the audit `HEAD` (sequence number and record hash only, ADR-0005 D6) into the public repository by hand, weekly. That material is the one deliberate case of audit-derived data inside the repository.

- It is an explicit, authorised exception to D2, limited to that material.
- The audit store, its exports and the working `HEAD` file stay in `D:\JARVIS\data\`. The repository copy is a derived anchor.
- This ADR does **not** choose the carrying ref, the file path or the verification record. Those remain open under ADR-0005 D7 (G-12).
- This ADR does not change ADR-0005 D7.

### D7. Tests

Phase 1 tests that need a governance zone or a data root use **injected temporary directories**. No test writes test state into `D:\JARVIS\`. Product code takes both roots from configuration, so a test can supply its own. How this is enforced is not decided here.

### D8. Registry consequence

ADR-0004 D3 already rejects a project whose canonical root contains, equals or lies inside the repository, the governance zone or the data root. A root that contains `D:\JARVIS\` is therefore rejected, so `D:\` itself can never be registered as a project. Each project is registered at its own folder.

## 3. Alternatives considered

| Option | Why not chosen |
|---|---|
| A directory inside the repository, ignored by Git | Fails ADR-0004 D2 constraints 1 and 2. See D4. |
| `E:\JARVIS\` or `F:\JARVIS\` | Also satisfies every constraint and sits on a physically separate NVMe disk. RK chose D: for simplicity, as the established workspace volume. E: remains a possible later migration. Moving the zone later needs a superseding ADR and re-registering projects (ADR-0004 §7). |
| `C:\JARVIS\` | Satisfies the literal constraints, but C: is the OS volume. Not chosen. |
| `G:\` | Excluded by RK before evaluation. Not assessed here. |

## 4. Evidence

- `VERIFIED` (Local read-only checks, 2026-10-12): `D:\JARVIS` does not exist. `D:\` is not a git repository and has no `.git`. D: is NTFS on an NVMe disk (the same disk as C:). `LongPathsEnabled` is 1. OneDrive's only sync root is under the user profile on C:. The repository is `D:\J.A.R.V.I.S AI Assistant`. The proposed paths are 20 and 14 characters long.
- `VERIFIED` D: has three other git repositories at its top level. `D:\JARVIS\` would be a sibling of them, not a child.
- `VERIFIED` No project is registered.
- `LOCAL FACT CHECK REQUIRED` Re-run LF-14 once the directories exist (ADR-0004 §9).
- `UNKNOWN` 8.3 short-name generation on D: (LF-10, needs elevation).
- Master Context §6.2, §17, §18 (D5); ADR-0004 D2, D3, §9, §10; ADR-0005 D6, D7; ADR-0003 D2, D6.

## 5. Security impact

- Placement outside the working tree keeps the store and governance files from being published, committed or deleted by Git operations. It is **not** a security boundary before isolation exists. Any process running as the user can edit them (ADR-0004 §5, ADR-0005 D10).
- D: shares a physical disk with Windows and the repositories. Loss of that disk loses the audit store with the work.
- No backup of `D:\JARVIS\` is provided by Git or by this ADR.

## 6. Complexity impact

Low. One parent directory and two named children, no new tooling. One rule for tests (D7).

## 7. Reversibility

Moderate, as in ADR-0004 §7. Moving the zone or data root means a superseding ADR (G-06), re-registering projects and re-recording contract hashes.

## 8. Authority class

USER AUTHORITY REQUIRED. Trigger G-06.

## 9. Consequences

- `D:\JARVIS\`, `governance\` and `data\` are not created by this ADR. Creating them, and running the LF-14 check, are a separate act on RK's instruction before Phase 1 writes anything.
- The ADR-0004 §9 requirement "RK chooses the zone and data root" is met by this ADR's acceptance. The creation step is still open.
- Product code and tests treat both roots as configuration (D7).
- A session that finds operational state inside the repository treats it as a defect to report. It does not treat it as a valid location.

## 10. Open items

| Item | Label |
|---|---|
| Creation of `D:\JARVIS\`, `governance\` and `data\`, and the LF-14 re-check | `LOCAL FACT CHECK REQUIRED`, on RK's instruction |
| Initial user-secret location list | `UNKNOWN`, `USER AUTHORITY REQUIRED` (G-07). Not decided here |
| Audit-anchor ref, path and verification record | `UNKNOWN`, `USER AUTHORITY REQUIRED` (G-12). Not decided here |
| Session-handoff location | `UNKNOWN`, `USER AUTHORITY REQUIRED`. Not decided here |
| Physical layout of `memory/` | `UNKNOWN`, later phase |
| Backup of `D:\JARVIS\` | `UNKNOWN`, `USER AUTHORITY REQUIRED` |
| 8.3 short-name behaviour on D: | `UNKNOWN` (LF-10) |
