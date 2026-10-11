# ADR-0004 — Contract and Governance-Zone Location

**STATUS: ACCEPTED**

| Field | Value |
|---|---|
| ID | ADR-0004 |
| Title | Contract and Governance-Zone Location |
| Status | ACCEPTED |
| Drafted | 2026-10-09, by Cloud Claude |
| Authority class | USER AUTHORITY REQUIRED (G-04, G-05, G-06, G-09). Item E-7 is `ENGINEERING AFTER CP-0` once this ADR is accepted. |
| Inputs | Master Context §6.2, §6.3, §10, §11, §14, §17, §18, §26, §33. CP-0 Review — Final (§4.2, §6, R21). Local CP-0 Fact Report 2026-10-09. Phase 0 snapshot (2026-10-06). |
| Related | ADR-0001, ADR-0002, ADR-0003, ADR-0005 |

**Labels:** `VERIFIED` · `UNKNOWN` · `MASTER CONTEXT POLICY` · `PROPOSED` · `USER AUTHORITY REQUIRED` · `LOCAL FACT CHECK REQUIRED` · `ENGINEERING AFTER CP-0`. `VERIFIED (LF-n)` = Local CP-0 Fact Report.

## Acceptance record

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Accepted by | RK, the owner of the project (the founder) |
| Acceptance date | 2026-10-11 |
| How the acceptance was given | A written instruction from the founder to Local Claude on 2026-10-11. Under ADR-0001 D6 that instruction is an input. The acceptance is recorded by RK's merge |
| Recorded in the repository by | The merge commit of the pull request that adds this document. Effective only when RK merges it (ADR-0001 D6) |
| Scope | The exact text of this document as added by that pull request. Labels such as PROPOSED inside the body are part of the accepted text and were not rewritten (ADR-0001 D6: approval applies to the exact text accepted) |
| Accepted text includes | Control-plane configuration files in the governance zone (D2) |
| Still open | The physical paths of the governance zone and the data root remain UNKNOWN (section 10). They must be chosen before Phase 1 writes anything (section 9) |

---

## 1. Context

1. `MASTER CONTEXT POLICY` §6.2: each project has a registry record (name, location, repository, allowed operations, required verification, instructions, workspace restrictions, memory location). §6.3: each project "should have a machine-readable contract." The possible files are `PROJECT.md`, `permissions.yaml`, `verification.yaml`. §6.3 does not say where they live. The §6.2 example puts the registry under JARVIS (`projects/swarag/`, etc.).
2. `MASTER CONTEXT POLICY` §10, §14: protected repository state stays untouched until approval. §11, §33: existing projects stay independent. §18: audit records are not editable by ordinary agent operations.
3. Risk if a contract lives in a project repository: a worker's patch could widen its own permissions through the merge path, or a hostile repository could supply its own contract.
4. `VERIFIED (LF-2)` The JARVIS workspace is `D:\J.A.R.V.I.S AI Assistant`. `VERIFIED (LF-9)` NTFS. `UNKNOWN (LF-14)` No data root has been specified, so no location was tested.
5. `VERIFIED` (Phase 0 snapshot) A OneDrive folder exists under the user profile. It holds `Swarag Overview.docx`. `UNKNOWN` Which folders OneDrive syncs.
6. `VERIFIED` (Phase 0 snapshot) None of the five ecosystem projects was found on this machine. Their locations are `UNKNOWN`.
7. `VERIFIED` The JARVIS repository is public (RK-stated; governance controls `UNKNOWN`, ADR-0001).

## 2. Decision

### D1. Contracts are JARVIS-side and live in the governance zone `PROPOSED`

- The authoritative contract for each project is a file in the **governance zone**, a JARVIS-controlled location outside every project repository and outside the JARVIS repository working tree.
- JARVIS loads contracts only from there. It never loads a contract from a project working tree, a sandbox clone, a downloaded archive or a model output.
- **Project-resident files are informational, not authority.** `PROJECT.md`, `permissions.yaml`, `verification.yaml` or similar files inside a project are not parsed at all in Phase 1 (CP-0 review §4.2). Later phases may read them as untrusted data. They can never grant or widen anything.
- No `WRITE_CONTRACT` capability exists, so JARVIS can never write a contract (ADR-0003 D12). A contract is created and edited by RK outside JARVIS.

### D2. Governance zone and data root `PROPOSED` `USER AUTHORITY REQUIRED` (G-06)

| Area | Holds | Not in git? |
|---|---|---|
| **Governance zone** | Contracts. Project registry. Revocation list. Control-plane configuration files. Spend policy (RK's decision, ADR-0001 G-08). | Yes: not in any git repository |
| **Data root** | The single SQLite store (tasks + audit chain, ADR-0005). Audit exports. Reports. HEAD files. | Yes: not in any git repository |
| **Repository (public)** | Policy definitions (ADR-0003). ADRs. Master Context. Code. | In git |

Constraints on both locations:

1. Outside every git working tree (verify with a `LOCAL FACT CHECK REQUIRED` once chosen; this is LF-14).
2. Outside every registered project root, and outside the JARVIS repository working tree.
3. Not in a cloud-synced folder, including the OneDrive folders. Task text may hold personal data (CP-0 review R21), and sync would copy governance and audit files off the machine. Which folders OneDrive syncs is `UNKNOWN`; it must be checked once a location is proposed.
4. On the same NTFS volume class as the work (LF-9), with long paths enabled (LF-11). Path-length margin to be tested once chosen.

**Physical paths:** `UNKNOWN`. LF-14 had no path to test. Whether the two areas are one directory tree or two is `USER AUTHORITY REQUIRED`. This ADR names them `<GOVERNANCE_ZONE>` and `<DATA_ROOT>`. No path is chosen or implied.

### D3. Rejection of JARVIS and governance targets `PROPOSED`

For any task action, these target classes are always DENY (ADR-0003 D2): `GOVERNANCE_ZONE`, `JARVIS_SELF`, `DATA_ROOT`, `USER_SECRET_LOCATION`.

- The project registry **rejects** registering any of these as a project: the JARVIS repository, the governance zone, the data root, or a user-secret location.
- A registration whose canonical root lies inside, contains, or equals any of them is rejected.
- In v0.1, JARVIS is not a project JARVIS can work on. A proposal to change JARVIS or its governance is a text report only (an L0 action). Any change is made by RK through the pull-request flow (ADR-0001).
- The control plane's own reads and writes of its store are internal operations, not task actions (ADR-0002 D1).

### D4. Project identity `PROPOSED`

- A project's identity is the pair **registry ID + canonical root path**.
- The registry ID is an immutable, lowercase slug chosen by RK.
- The canonical root path is resolved by the ADR-0003 D3 rules, strictly.
- If the root has moved, no longer resolves, or resolves to a different canonical path, the project becomes `UNKNOWN` (evaluations return `UNKNOWN_PROJECT`) until RK updates the registry. JARVIS never updates a path itself.
- A record may be created with an unresolved location (Master Context §6.2 allows it). It cannot be used for any action until resolved.
- `UNKNOWN` The five ecosystem projects have no registered location and none is assumed.

### D5. Overlapping roots `PROPOSED`

- Registering a root that equals, contains or lies inside another registered root is rejected.
- The check uses the canonical, case-normalised paths (ADR-0003 D3). The test includes junctions and symlinks, and non-ASCII characters in roots.
- Two projects cannot share a workspace (Master Context §11, independence).

### D6. Contract integrity `PROPOSED`

- Every evaluation records `contract_sha256`, the SHA-256 of the contract's canonical bytes (UTF-8, CRLF → LF, lone CR rejected, ADR-0003 D4).
- If the contract's hash differs from the hash used in the task's last evaluation, the task is re-evaluated (ADR-0003 D11). An audit event records `CONTRACT_HASH_CHANGED`.
- A missing, unreadable or invalid contract is DENY (`CONTRACT_MISSING`, `CONTRACT_INVALID`).
- **Limit.** The hash detects change. It does not prevent it. Before isolation, a process running as RK can edit both a contract and any hash recorded next to it. The audit chain and its off-machine anchor (ADR-0005) provide the detection.

### D7. Schema version `PROPOSED` `ENGINEERING AFTER CP-0` (E-7)

- Every contract, registry record and policy file declares an integer `schema_version`.
- An unknown version is DENY (`CONTRACT_SCHEMA_UNKNOWN`). A file that omits it is invalid.
- Adding a version is an engineering change recorded in an ADR amendment. Changing what a version means for authority is G-04.

### D8. Contract changes are governance changes `PROPOSED`

- Any change to a contract, registry entry, revocation list or spend policy is a permission or governance change (triggers G-03, G-04, G-09). It is made only by RK, outside JARVIS.
- JARVIS may detect a change (D6) and report it. JARVIS may not make or approve one.
- A contract may only narrow what policy and ADRs allow (ADR-0001 R1.4). A contract that grants more is void to that extent.

### D9. Contract contents (schema outline) `PROPOSED`

Per Master Context §6.3, a contract defines: scope; workspace; read, write and execution permissions; verification requirements; protected paths; forbidden operations. It adds `schema_version`, `project_id`, `valid_until` (optional, UTC). The exact field list is an `ENGINEERING AFTER CP-0` schema task (E-7). The file format is `UNKNOWN` (ADR-0006): `tomllib` is not available on the installed Python 3.10.11 (LF-8).

## 3. Alternatives considered

| Alternative | Rejected because |
|---|---|
| Contract in the project repository | A worker patch could widen its own permissions, or a hostile repository supplies its own contract. |
| Contract in the JARVIS repository | Public. Contains personal paths and project facts. Subject to builder commits. |
| Contract in the data root | Mixes authority with data the control plane writes continuously. |
| Registry keyed by path only | A moved or swapped directory would silently take over a project's permissions. |
| Allow JARVIS to propose contract edits it applies itself | Self-granted authority. |

## 4. Evidence

- Master Context §6.2, §6.3, §10, §11, §14, §18, §33 (quoted or cited exactly).
- `VERIFIED (LF-2, 8, 9, 11)`. `UNKNOWN (LF-14)`.
- `VERIFIED` Phase 0 snapshot: OneDrive folder; projects not found.
- CP-0 review: §4.2, §6.1 U-4, R21.

## 5. Security impact

- Removes the contract-in-repository escalation path.
- Stops registry takeover by a moved directory.
- Pre-isolation limit: governance-zone files are readable and writable by any process running as RK, including the build session (LF-1: `auto`). The ACL boundary comes with isolation, not here. D6 gives detection, not prevention.
- Cloud sync of governance or data files is a privacy leak risk (R21). D2 constraint 3 addresses it once a location is checked.

## 6. Complexity impact

Low. A location rule, two checks (overlap, self-target), a schema version and a hash.

## 7. Reversibility

Moderate. Moving the governance zone later means re-registering projects and re-recording hashes. A superseding ADR is required (G-06).

## 8. Authority class

USER AUTHORITY REQUIRED. Triggers G-04, G-05, G-06, G-09.

## 9. Consequences

- RK chooses `<GOVERNANCE_ZONE>` and `<DATA_ROOT>` before Phase 1 writes anything.
- A `LOCAL FACT CHECK REQUIRED` follows: not inside any git repository, not cloud-synced, path length acceptable.
- Phase 1 never parses project-resident files.
- The registry and contract schemas become Phase 1 deliverables (ADR-0002 D1 rows 2–3).

## 10. Open items

| Item | Label |
|---|---|
| Physical paths of the governance zone and data root | `UNKNOWN`, `USER AUTHORITY REQUIRED` |
| Whether the chosen paths lie inside a git repository or OneDrive-synced folder | `LOCAL FACT CHECK REQUIRED` (LF-14 and follow-up) |
| Locations of Swarag, Codebase Memory MCP, Global Guardrail, Swarag Guardrail, Universal Verification | `UNKNOWN` |
| Contract and registry file format | `UNKNOWN`, ADR-0006 |
| Initial user-secret location list | `UNKNOWN`, `USER AUTHORITY REQUIRED` (shared with ADR-0003) |
