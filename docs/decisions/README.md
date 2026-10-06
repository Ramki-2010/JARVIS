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
- Local Claude may accept and implement ordinary engineering decisions after validating the relevant local facts.
- The user remains the authority for governance, security and privacy decisions, credential decisions, protected-project decisions, spending decisions, security-boundary changes, and high-impact or irreversible actions. These require explicit user approval.
- Neither Cloud Claude nor Local Claude may treat its own recommendation as user approval.
- ADRs must never override the Master Context (`../spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md`) or grant authority that it does not permit.
- An ADR may document an intentional interpretation or clarification of the Master Context.
- Superseded ADRs remain in history. They are marked as superseded, not silently deleted.

No ADRs have been recorded yet.
