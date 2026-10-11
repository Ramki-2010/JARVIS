# JARVIS Documentation

## Foundation documents

| Document | Role |
|---|---|
| [`spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md`](spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md) | **Authoritative** technical/product specification. |
| [`spec/JARVIS_AI_LLM_PROJECT_ORIENTATION.md`](spec/JARVIS_AI_LLM_PROJECT_ORIENTATION.md) | Conceptual and educational context. |

If the two conflict on technical/product rules, the Master Context takes precedence.

Current Master Context version: 0.1-r1 (amended by MCA-001). Earlier versions are recoverable from Git history.

## Other documentation

- **Decisions:** architectural decisions are recorded as numbered ADRs, and changes to the Master Context as numbered MCAs, under [`decisions/`](decisions/). The register in that folder's README lists their status.
- **Environment:** environment facts are recorded under [`environment/`](environment/).

## Source of truth

- Once committed, the Git repository is the authoritative source for these documents.
- Pasted text, uploaded copies and temporary session context do not override committed repository documentation.

## Roles and authority

- Cloud Claude may propose architectural decisions.
- Local Claude is the source of truth for local facts and performs implementation.
- User authority remains required for genuine governance, security, privacy, credential, financial, high-impact or irreversible decisions.
- The authority hierarchy (RK first), the governance-trigger checklist and how approval is recorded are defined in ADR-0001.
