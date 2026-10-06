# JARVIS Documentation

## Foundation documents

| Document | Role |
|---|---|
| [`spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md`](spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md) | **Authoritative** technical/product specification. |
| [`spec/JARVIS_AI_LLM_PROJECT_ORIENTATION.md`](spec/JARVIS_AI_LLM_PROJECT_ORIENTATION.md) | Conceptual and educational context. |

If the two conflict on technical/product rules, the Master Context takes precedence.

## Other documentation

- **Decisions:** future architectural decisions are recorded as numbered ADRs under [`decisions/`](decisions/).
- **Environment:** environment facts are recorded under [`environment/`](environment/).

## Source of truth

- Once committed, the Git repository is the authoritative source for these documents.
- Pasted text, uploaded copies and temporary session context do not override committed repository documentation.

## Roles and authority

- Cloud Claude may propose architectural decisions.
- Local Claude is the source of truth for local facts and performs implementation.
- User authority remains required for genuine governance, security, privacy, credential, financial, high-impact or irreversible decisions.
