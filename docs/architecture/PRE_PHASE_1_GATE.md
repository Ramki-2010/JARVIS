# JARVIS Pre-Phase-1 Gate Package

**Status:** DRAFT FOR REVIEW. Not approved. Not an ADR.
**Date:** 2026-10-07
**Repository state when drafted:** `main` at `503381e9b671384e5e56177efb279ae3a9f19ec7` (PR #1 merged)

This package satisfies Master Context section 39, which requires five items after environment inspection and before Phase 1 implementation: an architecture proposal, a repository/environment inventory, an implementation plan, a risk assessment and a Phase 1 change list.

## How to read this document

- The Master Context (`../spec/JARVIS_CORE_v0.1_MASTER_CONTEXT_UPDATED.md`, "MC") is authoritative. If this document contradicts it, the Master Context wins. This document does not modify it.
- The Orientation (`../spec/JARVIS_AI_LLM_PROJECT_ORIENTATION.md`, "ORI") supplies conceptual rationale.
- Per `../decisions/README.md`, nothing here becomes a decision until it is accepted under the JARVIS authority model and, where appropriate, recorded as an ADR. No ADRs exist yet.
- Every statement carries one of these labels:

| Label | Meaning |
|---|---|
| VERIFIED | Observed on this machine, or present in committed repository content. |
| UNKNOWN | Not established. Needs further inspection. |
| MC POLICY | Stated in the Master Context or Orientation. A rule, not an implemented control. |
| PROPOSED | A design proposal in this document. Not implemented. Not decided. |

Nothing in JARVIS is implemented. The repository contains documentation only.

---

## 1. ARCHITECTURE PROPOSAL

### 1.1 Principles (MC POLICY)

- Local-first, laptop-first, modular, extensible (MC header, sections 3 and 34). Cloud is an option, never a default dependency (MC 28, ORI 21).
- JARVIS orchestrates existing systems. It does not absorb or replace them (MC 5, 11).
- The model is infrastructure and is not the security boundary (MC 27, ORI 11 and 13). A JARVIS task is not a model session (ORI 13).
- Permissions are enforced technically, not by prompts (MC 13, 26, 40.8).
- Execution and verification are separate. The same reasoning path may not declare itself correct (MC 19).
- When uncertain, prefer simple, modular, observable, reversible, least-privilege and locally executable (MC 34).

### 1.2 Structure (MC section 5, restated)

```text
                         USER
                           |
                           v
                    +-------------+
                    | JARVIS CORE |
                    +-------------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
       Research        Claude Code     Verification
          |                |                |
          +----------------+----------------+
                           |
                           v
                    Project Workspace
                           |
          +----------------+----------------+
          |                |                |
        Swarag        Codebase MCP    Guardrails / UV
```

Cross-cutting controls, applied to every path above:

```text
        GOVERNANCE
            |
   CAPABILITY FIREWALL
            |
        SANDBOX
            |
        AUDIT LOG
```

The Orientation (section 11) expands the same chain as: Governance Kernel, Capability Firewall, Approval Engine, Sandbox/Worktree, Execution, Verification, Audit.

### 1.3 Components

All components are PROPOSED and not implemented. The "Source" column shows where the requirement comes from.

| Component | Proposed role | Source |
|---|---|---|
| JARVIS Core | Receives a task, identifies the project, loads its context, asks governance what is permitted, plans, selects tools, executes bounded work, tracks state, invokes verification, produces the report. Contains no model-specific logic. | MC 6.1 |
| Project Registry | One record per known project: name, location, repository, description, allowed operations, required verification, instructions, workspace restrictions, memory location. Projects do not share identical rules. A record may carry an unresolved location. | MC 6.2 |
| Project Contract | Machine-readable per-project scope: workspace, read, write and execution permissions, verification requirements, protected paths, forbidden operations. Schema to be designed at implementation. | MC 6.3 |
| Task Engine | Turns a request into a persisted structured task (ID, project, objective, constraints, allowed tools, risk level, state, plan, actions, results, verification, final status). A task survives restart. | MC 7 |
| Autonomous Engineering Loop | TASK, PLAN, INSPECT, RESEARCH, HYPOTHESIS, IMPLEMENT/EXPERIMENT, TEST, VERIFY, ANALYZE, REPORT. Failure path: classify, safe bounded retry, test, verify. Retries are bounded. | MC 8 |
| R&D Loop | Question, research, evidence, hypothesis, experiment design, experiment, measurement, analysis, conclusion, next hypothesis. Sources recorded, evidence separated from inference, uncertainty recorded, no fabricated citations. | MC 9 |
| Claude Code as coding worker | A worker JARVIS invokes inside a sandbox/worktree on a task definition. It is not JARVIS. JARVIS does not rebuild a coding agent. Starts only at the controlled-coding stage. | MC 10, ORI 10 and 25 |
| Verification layer | Project tests, then Universal Verification, then the project guardrail, then Global Guardrail, using only systems actually available and applicable. Adapters, no merging of implementations. Never invents results. | MC 19, 11 |
| Governance Kernel | Deterministic policy evaluation outside the LLM. Holds the autonomy-level definitions and the rules that map capability, project contract and level to allow, require-approval or deny. The model cannot grant itself authority or reinterpret levels. | MC 12 and 26, ORI 7 and 11 |
| Capability Firewall | Every tool action passes through a capability layer. Capabilities have identity, scope, permission, risk, auditability and revocation. Default is deny. | MC 13, 40.8 |
| Approval Engine | Records and checks explicit user approvals for L4 actions. Approval is a user act, never inferred from model output. Approval events are audited. | MC 12 and 18, ORI 11 |
| Sandbox / workspace boundary | Autonomous work happens in a controlled workspace. The protected repository is untouched until approval. Whether this is a Git worktree alone or a stronger boundary is an open decision (see 1.6). | MC 14 |
| Scheduler | One-time, recurring and background tasks with pause, resume and cancel. Scheduled tasks inherit permissions and never bypass governance. Late stage. | MC 16 |
| Memory | Start with project, task, decision and research stores. Governance memory is protected, secrets are stored separately, retrieved memory is treated as potentially stale. Full memory architecture is deferred. | MC 17, ORI 12 |
| Audit | One record per autonomous task with the MC 18 minimum fields. Not editable by ordinary agent operations. | MC 18 |
| Reporting | Executive result, work performed, evidence, files changed, tests, verification, problems, recommendation. | MC 21 |
| Model abstraction | The core talks to models through one interface so models are replaceable. v0.1 may use one primary model. No routing sophistication yet. | MC 27, ORI 13 |
| CLI | Simple commands before any UI. | MC 22 |

### 1.4 Governance Kernel outside the LLM (PROPOSED interpretation)

The Master Context requires technical enforcement and says the model is not the security boundary. This package proposes the following reading, which needs review:

- Policy evaluation is ordinary deterministic code. Its inputs are structured data (capability, project contract, task risk level, approval records). Free text from a model is never an input that can change a verdict.
- Policy definitions and approval records live in a governance zone that the coding worker and the model cannot write.
- The only path from a model's intent to a side effect is: model proposes an action, Capability Firewall asks the Governance Kernel, the Kernel answers allow, require-approval or deny, and the action is executed and audited.
- Until OS-level isolation exists, this separation is code-level and conventional. It is not a security boundary against a hostile or compromised worker (see the Windows limitations in section 2 and risks R1 and R15 in section 4).

### 1.5 Authority boundary

| Party | Authority | Source |
|---|---|---|
| Cloud Claude | Proposes design and research conclusions and engineering ADRs. | `docs/decisions/README.md` |
| Local Claude | Owns empirical local facts. Implements within the already-approved architecture, phase scope and governance boundaries. May accept and implement ordinary engineering decisions after validating local facts. | `docs/decisions/README.md`, `docs/README.md` |
| User | Genuine governance, security and privacy decisions, credential decisions, protected-project decisions, spending decisions, security-boundary changes, and high-impact or irreversible actions. Explicit approval required. | `docs/decisions/README.md`, `docs/README.md` |
| Future JARVIS runtime | Autonomous execution at L0 to L3 only, within deterministic policy. L4 requires explicit user approval. L5 is technically blocked. | MC 12 |

Further rules: neither Cloud Claude nor Local Claude may treat its own recommendation as user approval. No ADR may override the Master Context or grant authority it does not permit. This package grants no authority.

Autonomy levels (MC 12): L0 advice, L1 read-only, L2 reversible action (normally automatic), L3 bounded autonomous work (automatic inside explicit boundaries), L4 high-impact action (explicit approval: external communication, protected code changes, push or merge, deployment, financial actions, sensitive data sharing, permission changes), L5 forbidden (bypassing governance, disabling security controls, self-granted permissions, removing verification requirements, circumventing approval).

Initial capabilities (MC 13): READ_PROJECT, READ_FILE, SEARCH_WEB, WRITE_SANDBOX, RUN_TEST, RUN_EXPERIMENT, USE_CLAUDE_CODE, USE_CODEBASE_MEMORY, USE_VERIFICATION, CREATE_REPORT, CREATE_TASK, SCHEDULE_TASK. Initially blocked or approval-gated: DELETE_PROTECTED, PUSH, MERGE, DEPLOY, SEND_EMAIL, SEND_MESSAGE, MAKE_CALL, FINANCIAL_TRANSACTION, CHANGE_PERMISSION, CHANGE_GOVERNANCE, DISABLE_GUARDRAIL. The mapping of each capability to a level is not specified by the Master Context and is a Phase 1 design task.

### 1.6 Interpretations needing review before they are relied on

| Topic | Master Context says | This package proposes | Needed |
|---|---|---|---|
| Sandbox strength | "Sandbox / worktree" is the preferred boundary (MC 14). "A permission prompt is not a security boundary" and "use real sandboxing" (MC 40.8). | A Git worktree gives change isolation and review, not security isolation. A worktree shares the user's filesystem permissions. A stronger boundary is needed before autonomous code execution. | ADR (security boundary, user authority). |
| Governance zone | Governance memory is protected (ORI 12). Audit not editable by ordinary operations (MC 18). | A distinct location and interface for policy, approvals and audit, not writable by workers. | ADR. |
| Language and runtime | Not specified. Phase 0 asks to inspect available runtimes (MC 30). | Python is proposed as the implementation language. Python is not installed on this machine. | Decision, then explicit user instruction before any install. |
| Model abstraction timing | "Create a model abstraction" with no phase (MC 27). | No model calls in Phase 1. Define the abstraction when the first stage needing a model starts (research engine). | Review. |

---

## 2. REPOSITORY / ENVIRONMENT INVENTORY

Source: `../environment/phase-0-2026-10-06.md` (historical snapshot, 2026-10-06), plus repository state re-verified on 2026-10-07. Identifiers are generalized as in the snapshot.

### 2.1 VERIFIED

**JARVIS repository**
- GitHub repository `Ramki-2010/JARVIS` (public). `main` at `503381e9b671384e5e56177efb279ae3a9f19ec7`, a merge of PR #1 "Add JARVIS documentation baseline". The local checkout is synchronized with it.
- 9 tracked files: `.gitignore`, `LICENSE`, `README.md`, `CLAUDE.md`, `docs/README.md`, `docs/decisions/README.md`, `docs/environment/phase-0-2026-10-06.md`, and the two files under `docs/spec/`.
- No code, configuration, dependency files, CI workflows or ADRs.
- Authenticated push to the remote worked on 2026-10-06 after the user signed in to Git on this machine. The GitHub CLI (`gh`) is not installed.

**Machine**
- ASUS TUF Gaming F16 FX608JPR. Windows 11 Home, 10.0.26300, 64-bit.
- Intel Core i7-14650HX, 16 cores, 24 logical processors. 31.6 GB RAM (18.4 GB available at inspection).
- NVIDIA GeForce RTX 5070 Laptop, driver 591.91, 8,151 MiB VRAM. Intel UHD integrated graphics.
- Free disk: C: 465.9 GB, D: 349.9 GB, E: 474.9 GB, F: 475.6 GB.

**Virtualization and isolation**
- A hypervisor is detected and virtualization-based security is running.
- WSL is not installed. Docker and Docker Desktop are not present. Windows Sandbox is not present. Hyper-V binaries (`vmms.exe`, `vmcompute.exe`) are not present.

**Development tools**
- Present: Git 2.56.0.windows.2, Git Bash (bash 5.3.15), Windows PowerShell 5.1.26100.9444.
- Absent: Python (only the Microsoft Store alias stub), `py`, pip, uv, conda, Node.js, npm, PowerShell 7.
- The Claude Code CLI is not on PATH.

**Claude Code**
- Local session through the Claude desktop app 2.19675.1 (Agent SDK 0.3.288). Bundled Claude Code builds 2.1.286 and 2.1.288 are present.
- Authentication is an OAuth account login, not an API key. Credential and configuration files for it live under the user profile (contents not read).
- No project or user settings files, no `.mcp.json`, no MCP servers configured for the project, no plugins, no `allowedTools`.

**OS accounts**
- The current Windows account is a member of the local Administrators group and runs with a non-elevated, filtered token.
- Two enabled local accounts were created by the OpenAI Codex tool and are unrelated to JARVIS. Five built-in accounts are disabled.

**Existing ecosystem**
- Not found in the inspected locations: Swarag repository, Codebase Memory MCP, Global Guardrail, Swarag Guardrail, Universal Verification. The inspected locations were the user profile to depth 4, the roots of D:, E: and F: to depth 4, and a name search of Documents, Downloads, Desktop and OneDrive.
- A Swarag overview document (`Swarag Overview.docx`, a document and not a repository) exists under the user's OneDrive Documents folder.
- This does not establish that these projects exist or do not exist elsewhere.

### 2.2 UNKNOWN or UNRESOLVED

- Where each of the five ecosystem projects lives, and whether it is local at all. Nothing is known about how each is invoked, its language, its interfaces or whether it depends on a model.
- Q-003 research state. No Q-003 material is in the repository or was found locally.
- Whether the Virtual Machine Platform, WSL and Hyper-V optional features are enabled, and whether WSL2 is usable. Needs elevated inspection.
- Whether firmware virtualization is enabled. WMI reports false, which conflicts with the running hypervisor.
- The active Claude Code permission mode, and which bundled build this session uses.
- Whether the desktop app attaches MCP servers beyond project configuration.
- Whether another local account can be created, and what policy limits apply.
- What the Codex-created accounts can access.
- A safe workspace for autonomous work. MC section 30 lists "identify safe workspace" under Phase 0. It has not been identified.

### 2.3 Gaps against MC section 30 Phase 0

| Phase 0 item | State |
|---|---|
| Inspect environment | Done (snapshot). Elevated items open. |
| Inspect relevant project locations | Done for the inspected locations. The five projects were not found. |
| Inspect existing project instructions | Not possible. No project found. |
| Inspect Claude Code configuration | Done as far as safely visible. Permission mode unknown. |
| Inspect existing verification tools | Not possible. No tool found. |
| Inspect Python and Node versions | Done. Both absent. |
| Inspect storage | Done. |
| Identify safe workspace | Not done. |
| Produce an inventory | Done (the snapshot and this section). |

---

## 3. IMPLEMENTATION PLAN

### 3.1 Principles

- The stage order below is the requested order. It is a proposal. Where it differs from MC section 30, the table says so. Nothing starts without the entry gate shown.
- Install nothing and change no system settings unless the user explicitly instructs it for that step.
- Adapters, not rewrites. No existing project is modified (MC 11, 29).
- No framework or infrastructure is assumed. Docker, WSL2, Redis, PostgreSQL, vector databases, LangGraph, CrewAI, LangChain and OpenHands are not required by anything in this plan.

### 3.2 Stages

| Stage | Delivers | MC phase | Depends on | Entry gate |
|---|---|---|---|---|
| S0 Architecture and documentation | This package, reviewed. Ratifying ADRs where decisions are needed. | Pre-Phase-1 (MC 39) | PR #1 (done) | Review of this package. |
| S1 Minimum bootstrap | The smallest toolchain needed to build and test Phase 1: a language runtime and a test runner, plus an empty project skeleton. | Part of Phase 1 | S0 and a runtime decision | Explicit user instruction (installs software). |
| S2 Governance zone | A defined location and interface for policy, approvals and audit, with schemas and a deterministic evaluator. Before S4 it is protected by convention and code checks only. | Part of Phase 1 (capability registry, audit) | S1 | ADR on governance zone. |
| S3 JARVIS core | Phase 1 per section 5. | Phase 1 | S2 | Review of the Phase 1 change list. |
| S4 Isolation | An OS-level boundary between the governance zone, protected projects and workers, including filesystem and network limits and credential separation. | Not a numbered phase. A precondition for MC Phase 3 (and for exposing the governance zone to any worker). | S3 | User authority (system and security configuration) and an ADR. |
| S5 Swarag inert migration | A copy of Swarag placed under JARVIS control as read-only data, without modifying the original. | Prerequisite for the first acceptance test (MC 31) | S4 and locating Swarag | User authority (protected project). Location currently UNKNOWN. |
| S6 Research engine | Web research, source recording, research notes, evidence handling, bounded retries. First stage with model calls, so the model abstraction lands here. | Phase 2 | S4 | Review. |
| S7 Controlled Claude Code | Sandbox creation, task handoff, command and test execution, diff generation, result collection. Protected repositories untouched. | Phase 3 | S4, S5, S6 | Review. User authority for the sandbox boundary. |
| S8 Verification integration | Adapters for Universal Verification, Global Guardrail and Swarag Guardrail. Codebase Memory MCP is listed in the same MC phase and is integrated here separately. | Phase 4 | S7 and the projects being located | Review. |
| S9 Bounded autonomous R&D | The full R&D loop with bounded background execution. | Phase 5 | S8 | Review. |
| S10 Scheduler | Scheduled and recurring tasks, pause, resume, runtime limits. | Phase 6 | S9 | Review. |
| S11 Dashboard | Functional status and control UI. No 3D galaxy. | Phase 7 | S10 | Review. |

### 3.3 Dependencies in plain terms

- S2 needs S1 because the governance schemas and evaluator need a runtime to be built and tested.
- S3 depends on S2 because the capability registry and audit core in MC Phase 1 are the first users of the governance interface.
- S4 must precede any worker execution. Before S4, everything runs as one Windows user, so protection of the governance zone is conventional only.
- S5 and S8 cannot start until the ecosystem projects are located (UNKNOWN today).
- S7 needs S6 only for evidence handling. It needs S4 and S5 for isolation and a real target.
- The MC first acceptance test (investigate an open Swarag research question) needs S5 through S9.

### 3.4 Differences from MC section 30

- S1, S2, S4 and S5 do not appear as numbered phases in the Master Context. They are proposed here. S2 is carried inside MC Phase 1. S4 implements MC sections 13, 14 and 26. S5 supports MC section 31. The Master Context does not mention "inert migration" and does not mention how existing projects are brought under JARVIS control, so S5 needs review.
- In the Master Context, Claude Code integration (Phase 3) follows research (Phase 2). This plan keeps that order.

### 3.5 External projects

Default decision for every external project in MC section 40 is WATCH or STUDY. Integration requires a separate architectural decision (MC 40.10). No such decision has been made.

| Project | Status in this plan |
|---|---|
| OpenHands, mini-SWE-agent, Goose, Gemini CLI, OpenClaw, Hermes, Letta | WATCH/STUDY. MC 40.12 schedules experiments only after Phase 0 and Phase 1. |
| LangGraph, Pydantic AI, CrewAI | WATCH/STUDY. No framework is required. |
| MCP | Used where a protocol boundary helps (MC 40.8). Whether the ecosystem projects expose MCP is UNKNOWN. |
| Qwen3-Coder, llama.cpp, Ollama | WATCH/STUDY. Local models are optional. |
| Docker, WSL2, Redis, PostgreSQL, vector databases | Not required. Any use would need its own decision. |

---

## 4. RISK ASSESSMENT

"Current mitigation" lists only what exists today. In this repository that is documented policy (MC POLICY) and the Git and pull-request review flow. Where a row says "None implemented", no control exists. Stage IDs refer to section 3. The last column is where the mitigation must become enforceable, not where it is.

| ID | Risk | Threat | Consequence | Current mitigation | Remaining gap | Enforceable by |
|---|---|---|---|---|---|---|
| R1 | Governance bypass | A worker or model edits or avoids policy code, approvals or the firewall | Unauthorized actions at any level | MC POLICY forbids it (MC 12 L5, 26). Nothing enforces it. | Everything. All components are unbuilt and, even once built, run as the same Windows user until S4. | S2 (code), S4 (OS boundary) |
| R2 | LLM authority confusion | Model output treated as policy, approval or verification | Self-granted authority, false approvals | MC POLICY: model is not the boundary (ORI 11). | No evaluator exists. Approval Engine unbuilt. | S3 |
| R3 | Arbitrary code execution | Workers run commands, tests or experiments with the user's full rights | Damage or data loss on the machine | None implemented. | No sandbox. The worktree concept offers no security isolation. | S4, required before S7 |
| R4 | Filesystem access | Worker reads or writes outside its workspace | Protected projects altered, personal data read | None implemented. | No filesystem limits. Current account is in Administrators. | S4 |
| R5 | Credential exposure | A worker reads credential files held under the user profile (OAuth login files for Claude Code and for other installed tools) | Account compromise | Contents were not read during inspection. No technical protection. | Credentials share the user's profile and are readable by anything running as that user. | S4 |
| R6 | Network and data exfiltration | A worker or fetched content sends data out | Source or secrets leave the machine | None implemented. | No egress control. | S4, required before S6 handles untrusted content |
| R7 | Prompt injection | Web pages, repository files or tool output instruct the model | Model proposes harmful actions | MC POLICY: treat external input and tool output as untrusted (MC 26). | No mediation exists. The firewall would limit harm only once it exists and is enforced. | S3 (firewall), S6 (research content handling) |
| R8 | Memory poisoning | Bad data is written to memory and later trusted | Persistent wrong context | MC POLICY: retrieved memory may be stale. | No memory built. No provenance design. | S3 design, S9 enforcement |
| R9 | Malicious project files | Hooks, scripts or build files in a project run on test or build | Code execution via a project | None implemented. | Projects are not located. Project contracts do not exist. | S4, S7 |
| R10 | Compromised dependencies | A package pulled during bootstrap or later is malicious | Compromise of the build or runtime | None implemented. No runtime or packages installed yet. | No pinning or review policy. | S1 policy, S4 enforcement |
| R11 | Verification tampering | The worker alters tests, verification tools or their results | False passes | MC POLICY: independent verification (MC 19). | No verification integration. The ecosystem verification tools are not located. | S8, with S4 separation |
| R12 | Audit tampering | Audit records are edited or deleted | Loss of accountability | MC POLICY: not editable by ordinary operations (MC 18). | No audit store. No write protection. | S2 design, S4 enforcement |
| R13 | Self-modification | JARVIS changes its own code, policy or permissions | Loss of control | MC POLICY forbids changing governance (MC 26, 33). | Nothing prevents edits to the repository by whatever runs there. | S4, plus approval for governance changes |
| R14 | Permission drift | Permissions widen over time through convenience grants | Accumulated excess privilege | None implemented. | No permission store, no change process, no review. | S2 |
| R15 | Scheduler drift | A scheduled task outlives its intent or inherits stale permissions | Unbounded background activity | MC POLICY: scheduled tasks inherit permissions and are bounded (MC 15 and 16). | No scheduler. | S10 |
| R16 | Model failure and reward hacking | The model claims success, edits tests to pass, or loops | False results, runaway cost | MC POLICY: never fabricate results (MC 20), bounded retries (MC 8). | No enforcement of bounds, no independent check. | S3 (bounds), S8 (verification) |
| R17 | Cloud and local mismatch | Cloud-session assumptions differ from local facts | Wrong decisions, wasted work | The docs rule that Local Claude owns local facts, and the committed Phase 0 snapshot. | Snapshot is dated. Several facts are UNKNOWN. | Ongoing, each stage re-checks facts |
| R18 | Windows isolation limits | Windows 11 Home lacks Hyper-V and Windows Sandbox. WSL2 and Docker are absent. The hardware virtualization flag is ambiguous. | Few strong boundary options | VERIFIED facts in section 2 only. | Which isolation options are viable is UNKNOWN. Elevated inspection is needed. | S4 |
| R19 | Accidental modification of existing projects | A worker edits Swarag or another independent project | Loss of protected work | MC POLICY: protected repositories untouched until approval. | No project contracts. No protection. Projects not located. | S5 (read-only copy), S4 |

Risk notes:

- The single largest gap is that every proposed control is unbuilt and, once built, shares a user account with the thing it constrains. Several risks (R1, R3 to R6, R12, R13) cannot be reduced to an acceptable level by code alone. They depend on S4.
- Checks in this gate are documentation checks. No security test has been run.

---

## 5. PHASE 1 CHANGE LIST

Phase 1 corresponds to MC section 30 Phase 1 ("Minimal Jarvis Core": configuration, project registry, task model, task persistence, basic planner, capability registry, audit logging, CLI), together with S1 and S2 above. MC states: "No autonomous code modification yet." Phase 1 makes no model calls and executes no worker.

### 5.1 In scope

| # | Component | Minimal content | Basis |
|---|---|---|---|
| 1 | Project bootstrap | Project skeleton, dependency declaration, test layout. Runtime and tooling per an accepted decision. | S1 (PROPOSED) |
| 2 | Configuration | Typed configuration loaded from files. No secrets in configuration. | MC 30 |
| 3 | Project registry | Records with the MC 6.2 fields. Records may be created with an unresolved location. The five ecosystem projects are not assumed to exist. | MC 6.2 |
| 4 | Project contract schema and loader | Schema for the MC 6.3 fields. Validation only, no enforcement against processes. | MC 6.3 |
| 5 | Task model and persistence | Structured task with the MC 7 fields. Stored locally. Survives restart. Storage format to be recorded as an engineering decision. | MC 7 |
| 6 | Planner stub | Deterministic. Produces plan structure without calling a model. | MC 30 ("basic planner") |
| 7 | Capability registry | The 12 initial and 11 blocked or gated capabilities from MC 13, each with an assigned autonomy level and risk. | MC 13 |
| 8 | Deterministic capability and risk evaluation foundation | A function from capability, project contract, task and level to allow, require-approval or deny, with a reason. Default deny. Free text cannot change a verdict. | MC 13, 26 (PROPOSED reading) |
| 9 | Audit schema and core | The MC 18 fields, with an append-only writer. Tamper resistance is not claimed until S4. | MC 18 |
| 10 | Verification state model | Data types only, such as not run, passed, failed, unavailable, and whether independent. A result is never assumed to be a pass. No integrations. | MC 19 (PROPOSED, data model only) |
| 11 | Governance-zone interface and schemas | The policy, approval-record and audit interfaces. No OS enforcement. | S2 (PROPOSED) |
| 12 | CLI | Create and inspect tasks, status, list tasks, show a report. | MC 22 |
| 13 | Basic tests | Default-deny, blocked capabilities, task survives restart, audit completeness, schema validation. | MC 32, 37 |

### 5.2 Explicitly out of scope (later stages)

| Item | Stage |
|---|---|
| Web research, source recording, evidence handling, model abstraction | S6 (Phase 2) |
| Isolation, OS enforcement, credential separation, network policy | S4 |
| Swarag copy or migration | S5 |
| Claude Code integration, sandbox or worktree creation, command execution | S7 (Phase 3) |
| Universal Verification, Global Guardrail, Swarag Guardrail, Codebase Memory MCP adapters | S8 (Phase 4) |
| Autonomous R&D loop, background execution | S9 (Phase 5) |
| CLI `pause`, `resume`, `stop` (no background work exists yet) | S9 and S10 |
| Scheduler | S10 (Phase 6) |
| Dashboard | S11 (Phase 7) |
| Memory stores beyond task and project context (MC 17) | After verification (MC 4) |
| Evaluation of external agents or models (MC 40.12) | After Phase 1 |

### 5.3 Phase 1 exit criteria (from MC 37)

Implementation exists, relevant tests pass, failure cases are considered, permissions are enforced in code, audit logging works, documentation exists, verification is performed, no unrelated changes exist, and behavior matches the specification. Phase 1 does not claim an OS-level security boundary.

---

## 6. OPEN ITEMS FOR REVIEW

1. The stage order and the new stages S1, S2, S4 and S5 are not in the Master Context. They need review and, for S2, S4 and S5, an ADR.
2. Language and runtime choice, and when installation is authorized.
3. Whether the Phase 1 items 8, 10 and 11 (evaluation foundation, verification state model, governance-zone schemas) are within the MC Phase 1 scope or are early additions.
4. Where to place the model abstraction (MC 27 gives no phase).
5. Which isolation mechanism is viable on Windows 11 Home. Elevated inspection is needed first.
6. Where Swarag and the four other projects are, and whether they are available locally.
7. Where `pause`, `resume` and `stop` belong in the CLI.
8. This package asks for review by the Cloud architecture session. MC section 36 and ORI 25 say cloud-based code review services require explicit authorization. This is a design review of documentation, not a code review service. Please confirm that reading.
