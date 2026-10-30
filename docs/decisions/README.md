# Architectural Decision Records (ADRs)

ADRs are numbered records of architectural decisions. Each ADR records one meaningful decision.

## Required fields

- ID
- Title
- Status
- Decision
- Context
- Alternatives
- Evidence
- Security impact
- Complexity impact
- Reversibility
- Authority class
- Consequences

## Rules

- Cloud Claude proposes design and research conclusions and engineering ADRs.
- Local Claude owns empirical local facts and implements within the already-approved architecture, phase scope and governance boundaries.
- Ordinary engineering decisions are only those named in an accepted ADR's engineering list (ADR-0001 D7). Local Claude may decide and implement a named item after validating the relevant local facts. Any other decision is USER AUTHORITY REQUIRED. No session classifies its own authority, or accepts an ADR or an MCA.
- The user remains the authority for governance, security and privacy decisions, credential decisions, protected-project decisions, spending decisions, security-boundary changes, and high-impact or irreversible actions. These require explicit user approval.
- Neither Cloud Claude nor Local Claude may treat its own recommendation as user approval.
- ADRs must never override the Master Context (`../spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md`) or grant authority that it does not permit.
- An ADR may implement, detail or narrow the Master Context. It may not widen, reinterpret or contradict it. A change to the Master Context needs an accepted MCA, which produces a new Master Context version (ADR-0001 D3, D4).
- An ADR or MCA is accepted only by RK's recorded act: RK merges a pull request that sets its STATUS to ACCEPTED (ADR-0001 D6). A chat statement is an input to that act, not the record.
- Every ADR and pull request carries its governance-trigger classification (ADR-0001 D5, D7).
- Superseded ADRs remain in history. They are marked as superseded, not silently deleted.

## Register

| ID | Title | Status | Accepted | File |
|---|---|---|---|---|
| ADR-0001 | Authority Classification and Governance Flow | Accepted | 2026-10-11 | [`ADR-0001-authority-classification-and-governance-flow.md`](ADR-0001-authority-classification-and-governance-flow.md) |
| MCA-001 | Master Context Phase-Order Amendment | Accepted | 2026-10-11 | [`MCA-001-master-context-phase-order-amendment.md`](MCA-001-master-context-phase-order-amendment.md) |
| ADR-0004 | Contract and Governance-Zone Location | Accepted | 2026-10-11 | [`ADR-0004-contract-and-governance-zone-location.md`](ADR-0004-contract-and-governance-zone-location.md) |
| ADR-0003 | Capability Evaluation Model | Accepted | 2026-10-11 | [`ADR-0003-capability-evaluation-model.md`](ADR-0003-capability-evaluation-model.md) |
| ADR-0005 | Audit Model | Accepted | 2026-10-11 | [`ADR-0005-audit-model.md`](ADR-0005-audit-model.md) |
| ADR-0002 | Phase 1 Scope and Interpretation | Accepted | 2026-10-11 | [`ADR-0002-phase-1-scope-and-interpretation.md`](ADR-0002-phase-1-scope-and-interpretation.md) |
| ADR-0006 | Phase 1 Technical Stack and Local Implementation Baseline | Accepted; exclusions lifted by the 2026-10-21 amendment recorded in the document | 2026-10-11 | [`ADR-0006-phase-1-technical-stack.md`](ADR-0006-phase-1-technical-stack.md) |
| ADR-0007 | External Operational Storage | Accepted | 2026-10-12 | [`ADR-0007-external-operational-storage.md`](ADR-0007-external-operational-storage.md) |
| ADR-0008 | Initial User-Secret Locations and Build-Session Permission Mode | Accepted | 2026-10-21 | [`ADR-0008-user-secret-locations-and-build-session-permission-mode.md`](ADR-0008-user-secret-locations-and-build-session-permission-mode.md) |
| ADR-0009 | Audit-Anchor Location | Accepted | 2026-10-30 | [`ADR-0009-audit-anchor-location.md`](ADR-0009-audit-anchor-location.md) |
| ADR-0010 | Phase 2 Manual Worker Bridge | Accepted | 2026-10-30 | [`ADR-0010-manual-worker-bridge.md`](ADR-0010-manual-worker-bridge.md) |

The order of the rows is the acceptance order. Acceptance takes effect when RK merges the pull request that adds the records (ADR-0001 D6).
