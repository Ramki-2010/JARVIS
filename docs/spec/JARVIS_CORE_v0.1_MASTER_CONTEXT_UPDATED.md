# JARVIS CORE v0.1
## Autonomous R&D, Coding, Research, and Project Operations
### Master Development Context for Claude Code

**Status:** Approved baseline  
**Version:** 0.1  
**Date:** 2026-10-06  
**Owner:** User  
**Primary developer:** Claude Code  
**Deployment target:** User's Windows gaming laptop  
**Architecture:** Local-first, laptop-first, modular, extensible

---

## 1. Purpose

Build the first small, useful version of JARVIS.

JARVIS v0.1 is not the complete personal AI operating system.

It is an autonomous engineering agent.

Its initial purpose is to work on existing projects:

- Swarag / Swargam
- Codebase Memory MCP
- Global Guardrail
- Swarag Guardrail
- Universal Verification
- Future projects

JARVIS v0.1 must support:

1. Autonomous research.
2. Project inspection.
3. Task planning.
4. Controlled coding.
5. Experiment execution.
6. Testing.
7. Verification.
8. Bounded retries.
9. Documentation.
10. Persistent task/project context.
11. Scheduled/background work.
12. Clear reporting.

The system must be useful before advanced UI features exist.

---

## 2. Project Philosophy

JARVIS must be developed independently.

Do not copy another Jarvis project's architecture.

External Jarvis projects, prompt packs, screenshots, and videos are inspiration only.

Useful concepts may be adopted.

Architecture must be derived from this specification.

Do not build a demo disguised as an autonomous system.

Do not optimize for cinematic presentation first.

Optimize for reliable autonomous engineering work.

---

## 3. User and Hardware Context

The owner is a solo developer.

Current resources:

- Gaming laptop.
- Additional hard-disk storage.
- Basic technical knowledge.
- Understanding of AI, LLMs, and neural networks.
- No dedicated server.
- No NAS.
- No permanent cloud infrastructure.

Cloud resources may be added later.

Therefore:

> JARVIS v0.1 must run locally.

Do not make cloud infrastructure a prerequisite.

Do not introduce unnecessary distributed architecture.

Do not require professional DevOps knowledge.

The architecture must remain understandable and maintainable by one person.

---

## 4. Development Strategy

Build the smallest reliable system first.

Use this progression:

```text
Foundation
    ↓
Governance
    ↓
Project Registry
    ↓
Task Engine
    ↓
Research
    ↓
Controlled Coding
    ↓
Testing
    ↓
Verification
    ↓
Memory
    ↓
Scheduling
    ↓
Background Autonomy
    ↓
Advanced UI
```

Do not implement future features prematurely.

Every component must have a clear reason.

---

## 5. v0.1 Core Architecture

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

Cross-cutting controls:

```text
                    GOVERNANCE
                        |
               CAPABILITY FIREWALL
                        |
               SANDBOX / WORKTREE
                        |
                   AUDIT LOG
```

JARVIS orchestrates existing systems.

It does not absorb or replace them.

---

## 6. Initial Components

### 6.1 Jarvis Core

Responsibilities:

- Receive task.
- Identify project.
- Load project context.
- Determine permissions.
- Create execution plan.
- Select tools.
- Execute bounded work.
- Track state.
- Invoke verification.
- Produce report.

The core must remain model-independent.

### 6.2 Project Registry

Maintain a registry for each known project.

Example:

```text
projects/
  swarag/
  codebase-memory-mcp/
  global-guardrail/
  swarag-guardrail/
  universal-verification/
```

Each project defines:

- Name.
- Location.
- Repository.
- Description.
- Allowed operations.
- Required verification.
- Project instructions.
- Workspace restrictions.
- Memory location.

Do not assume all projects have identical rules.

### 6.3 Project Contract

Each project should have a machine-readable contract.

Possible files:

```text
PROJECT.md
permissions.yaml
verification.yaml
```

The exact schema may be designed during implementation.

The contract must define:

- Scope.
- Workspace.
- Read permissions.
- Write permissions.
- Execution permissions.
- Verification requirements.
- Protected paths.
- Forbidden operations.

---

## 7. Task Engine

JARVIS must turn natural-language requests into structured tasks.

Example:

> Investigate Q-003 in Swarag.

Internal task:

```text
Task ID
Project
Objective
Constraints
Allowed tools
Risk level
Current state
Plan
Actions
Results
Verification
Final status
```

Tasks must persist.

A task must survive application restart.

---

## 8. Autonomous Engineering Loop

Primary execution loop:

```text
TASK
  ↓
PLAN
  ↓
INSPECT
  ↓
RESEARCH
  ↓
HYPOTHESIS
  ↓
IMPLEMENT / EXPERIMENT
  ↓
TEST
  ↓
VERIFY
  ↓
ANALYZE
  ↓
REPORT
```

Failure loop:

```text
FAILURE
   ↓
CLASSIFY FAILURE
   ↓
SAFE RETRY
   ↓
TEST
   ↓
VERIFY
```

Retries must be bounded.

Never create infinite loops.

---

## 9. R&D Mode

R&D is a first-class feature.

JARVIS must support:

```text
Question
  ↓
Research
  ↓
Evidence
  ↓
Hypothesis
  ↓
Experiment design
  ↓
Experiment
  ↓
Measurement
  ↓
Analysis
  ↓
Conclusion
  ↓
Next hypothesis
```

For research claims:

- Prefer primary sources.
- Record sources.
- Separate evidence from inference.
- Record uncertainty.
- Do not fabricate citations.
- Identify contradictory evidence.

---

## 10. Coding Mode

JARVIS should use Claude Code as a controlled coding worker.

Do not rebuild a coding agent unnecessarily.

Preferred flow:

```text
JARVIS
  ↓
Task definition
  ↓
Sandbox / worktree
  ↓
Claude Code
  ↓
Tests
  ↓
Verification
  ↓
Report
```

Initial automatic permissions:

- Read repository.
- Analyze repository.
- Create sandbox/worktree.
- Modify sandbox files.
- Run tests.
- Run approved commands.
- Generate documentation.
- Run approved experiments.

Approval required:

- Protected code modification.
- Push.
- Merge.
- Deployment.
- Permission changes.
- Governance changes.

---

## 11. Existing Project Systems

These remain independent.

JARVIS may orchestrate:

- Claude Code.
- Codebase Memory MCP.
- Universal Verification.
- Global Guardrail.
- Swarag Guardrail.
- Swarag itself.
- Future systems.

Do not merge these systems into one implementation.

Do not replace them with generic JARVIS subsystems.

Use adapters/interfaces where practical.

---

## 12. Governance

JARVIS autonomy levels:

### L0 — Advice

Analysis and recommendations.

No approval required.

### L1 — Read-only

Reading permitted resources.

No approval required.

### L2 — Reversible action

Safe reversible operations.

Normally automatic.

### L3 — Bounded autonomous work

Research, experiments, coding, testing, documentation.

Automatic within explicit boundaries.

### L4 — High-impact action

Requires explicit user approval.

Examples:

- External communication.
- Protected code changes.
- Push/merge.
- Deployment.
- Financial actions.
- Sensitive data sharing.
- Permission changes.

### L5 — Forbidden

Technically blocked.

Examples:

- Bypassing governance.
- Disabling security controls.
- Granting itself permissions.
- Removing verification requirements.
- Circumventing approval systems.

---

## 13. Capability Firewall

Every tool action must pass through a capability layer.

Initial capabilities:

```text
READ_PROJECT
READ_FILE
SEARCH_WEB
WRITE_SANDBOX
RUN_TEST
RUN_EXPERIMENT
USE_CLAUDE_CODE
USE_CODEBASE_MEMORY
USE_VERIFICATION
CREATE_REPORT
CREATE_TASK
SCHEDULE_TASK
```

Initially blocked or approval-gated:

```text
DELETE_PROTECTED
PUSH
MERGE
DEPLOY
SEND_EMAIL
SEND_MESSAGE
MAKE_CALL
FINANCIAL_TRANSACTION
CHANGE_PERMISSION
CHANGE_GOVERNANCE
DISABLE_GUARDRAIL
```

Do not rely on prompts alone.

Enforce permissions technically.

---

## 14. Sandbox

Autonomous coding must happen in a controlled workspace.

Preferred:

```text
Project repository
      |
      +-- protected source
      |
      +-- autonomous worktree/sandbox
```

JARVIS should be able to:

- Create sandbox.
- Modify sandbox.
- Run tests.
- Compare changes.
- Generate patch/diff.
- Request approval.

Protected repository state must remain untouched until approval.

---

## 15. Background Autonomy

JARVIS may continue working without the user present.

Each background task must have:

- Maximum runtime.
- Maximum retry count.
- Allowed tools.
- Allowed directories.
- Network policy.
- Resource budget.
- API budget if applicable.
- Stop conditions.

Example:

```text
Task: Investigate Q-003
Runtime: bounded
Workspace: Swarag sandbox
Tools: research + coding + tests
Push: prohibited
Deploy: prohibited
External communication: prohibited
```

---

## 16. Scheduler

Implement a basic scheduler.

It should support:

- One-time tasks.
- Recurring tasks.
- Background tasks.
- Pause.
- Resume.
- Cancel.

Scheduled tasks inherit the same permissions.

Scheduling must never bypass governance.

---

## 17. Memory v0.1

Do not build the full memory architecture yet.

Start with:

```text
memory/
  projects/
  tasks/
  decisions/
  research/
```

Store:

- Project context.
- Important decisions.
- Task history.
- Research findings.
- Useful technical context.

Separate audit data:

```text
audit/
```

Sensitive memory must not be casually exposed.

---

## 18. Audit Log

Every autonomous task must produce an audit record.

Minimum fields:

```text
task_id
timestamp
project
objective
risk_level
tools_used
files_read
files_modified
commands_run
research_sources
models_used
tests_run
verification_results
retries
errors
final_status
approval_events
```

Audit records must not be editable by ordinary agent operations.

---

## 19. Verification

JARVIS must distinguish execution from verification.

Do not allow the same reasoning path to simply declare itself correct.

Use available independent systems.

For applicable projects:

```text
JARVIS
  ↓
Implementation
  ↓
Project tests
  ↓
Universal Verification
  ↓
Project Guardrail
  ↓
Global Guardrail
```

Use only systems actually available and applicable.

Do not invent verification results.

---

## 20. Failure Handling

JARVIS must fail safely.

If uncertain:

1. Research if safe.
2. Attempt bounded investigation.
3. Report uncertainty.
4. Ask the user if consequential.

Never fabricate:

- Results.
- Sources.
- Test success.
- Verification success.
- Tool execution.
- File changes.

If a tool fails:

```text
Detect
  ↓
Classify
  ↓
Retry if safe
  ↓
Try approved alternative
  ↓
Escalate
```

---

## 21. Reporting

Every completed autonomous task must produce:

### Executive result

What happened?

### Work performed

What did JARVIS do?

### Evidence

What supports the result?

### Files changed

Exactly what changed.

### Tests

What passed and failed?

### Verification

What was independently checked?

### Problems

What remains unresolved?

### Recommendation

What should happen next?

Keep reports concise but complete.

---

## 22. Initial CLI

Build a simple CLI before advanced UI.

Example commands:

```text
jarvis task "Investigate Q-003"
jarvis status
jarvis tasks
jarvis pause
jarvis resume
jarvis stop
jarvis report
```

Exact syntax may change.

Keep it simple.

---

## 23. Initial UI

Do not build the cinematic 3D galaxy yet.

Start with a functional dashboard.

Show:

```text
JARVIS
STATUS
CURRENT PROJECT
CURRENT TASK
CURRENT ACTION
MODEL
TOOLS
AUTONOMY LEVEL
VERIFICATION
ERRORS
```

Controls:

```text
Pause
Resume
Stop
View Task
View Logs
View Report
```

The 3D Knowledge Galaxy belongs to a later phase.

---

## 24. Knowledge Galaxy — Later

The supplied Jarvis UI references inspired this feature.

Eventually it should visualize:

- Projects.
- Memories.
- Documents.
- Tasks.
- Research.
- Decisions.
- Evidence.
- Agents.
- Tools.
- Verification.
- Relationships.

Relationships should be typed:

```text
supports
contradicts
derived_from
depends_on
verified_by
created_by
related_to
```

The galaxy is a visualization layer.

It must not become the governance layer.

---

## 25. Voice — Later

Voice is not part of v0.1.

Later support:

- Speech input.
- Speech output.
- Wake word.
- Barge-in.
- Interruption.
- Status indicators.
- Mute.
- Mobile support.

Do not let voice complexity delay autonomous engineering.

---

## 26. Security Principles

Non-negotiable:

JARVIS must not:

- Grant itself permissions.
- Disable guardrails.
- Modify governance.
- Bypass approval.
- Expose secrets unnecessarily.
- Modify protected repositories without approval.
- Perform financial transactions autonomously.
- Send external communication autonomously initially.
- Circumvent filesystem restrictions.

Use least privilege.

Treat external input as untrusted.

Treat tool output as potentially untrusted.

Treat retrieved memory as potentially stale.

---

## 27. Model Strategy

The model is infrastructure.

JARVIS must not depend on one model.

Create a model abstraction.

Future routes may include:

- Fast model.
- Reasoning model.
- Coding model.
- Research model.
- Verification model.
- Local model.

v0.1 may use one primary model.

Do not over-engineer model routing yet.

---

## 28. Cost and Resource Strategy

Do not require expensive cloud infrastructure.

Prefer local execution when practical.

Cloud APIs may be used when necessary.

All future API-heavy tasks should support budgets.

Do not allow uncontrolled API loops.

Use additional HDD storage for:

- Logs.
- Experiments.
- Cached research.
- Project snapshots.
- Backups.
- Large datasets.

Do not require NAS or cloud.

If local resources become insufficient, propose cloud expansion.

Do not silently introduce cloud dependencies.

---

## 29. Development Method

For every implementation phase:

```text
Inspect
  ↓
Plan
  ↓
Implement
  ↓
Test
  ↓
Verify
  ↓
Report
```

Do not make broad speculative changes.

Do not rewrite unrelated project code.

Do not modify existing projects merely to simplify integration.

Prefer adapters.

Prefer small commits.

Keep changes reversible.

---

## 30. Required Initial Phases

### Phase 0 — Repository and environment inspection

Before coding:

- Inspect current environment.
- Inspect relevant project locations.
- Inspect existing project instructions.
- Inspect Claude Code configuration.
- Inspect existing verification tools.
- Inspect available Python/Node/runtime versions.
- Inspect available storage.
- Identify safe workspace.

Do not modify projects during inspection.

Produce an inventory.

### Phase 1 — Minimal Jarvis Core

Implement:

- Configuration.
- Project registry.
- Task model.
- Task persistence.
- Basic planner.
- Capability registry.
- Audit logging.
- CLI.

No autonomous code modification yet.

### Phase 2 — Research Engine

Implement:

- Web research.
- Source recording.
- Research notes.
- Evidence handling.
- Research task execution.
- Bounded retries.

### Phase 3 — Controlled Coding

Integrate Claude Code.

Implement:

- Sandbox/worktree creation.
- Task handoff.
- Command execution.
- Test execution.
- Diff generation.
- Result collection.

Protected repository remains untouched.

### Phase 4 — Verification Integration

Integrate applicable:

- Universal Verification.
- Global Guardrail.
- Project-specific guardrails.
- Codebase Memory MCP.

Use adapters.

Do not merge implementations.

### Phase 5 — Autonomous R&D

Implement:

```text
Question
→ Research
→ Hypothesis
→ Experiment
→ Code
→ Test
→ Verify
→ Analyze
→ Report
```

Add bounded background execution.

### Phase 6 — Scheduler

Add:

- Scheduled tasks.
- Recurring research.
- Background project work.
- Pause/resume.
- Runtime limits.

### Phase 7 — Functional Dashboard

Add the basic UI.

Do not build cinematic UI yet.

---

## 31. First Acceptance Test

Do not declare v0.1 complete until JARVIS can perform:

> Investigate an open research question in Swarag.

Expected:

```text
1. Identify Swarag.
2. Load project context.
3. Identify relevant research state.
4. Inspect repository.
5. Research external sources.
6. Form hypotheses.
7. Create sandbox.
8. Implement bounded experiment.
9. Run tests.
10. Run applicable verification.
11. Analyze results.
12. Record findings.
13. Produce report.
14. Recommend next action.
```

Requirements:

- No protected repository changes.
- No unauthorized external communication.
- No governance changes.
- No fabricated results.

---

## 32. Secondary Acceptance Tests

Test:

- Codebase Memory MCP.
- Global Guardrail.
- Universal Verification.
- One project-specific guardrail.
- Failure recovery.
- Task resume after restart.
- Kill/stop behavior.
- Permission denial.
- Sandbox isolation.
- Audit completeness.

---

## 33. Non-Goals for v0.1

Do NOT build yet:

- 3D galaxy.
- Full voice assistant.
- Wake word.
- Mobile application.
- WhatsApp.
- Telegram.
- Phone calling.
- Financial integrations.
- Full computer vision.
- Full autonomous desktop control.
- Multi-agent swarm.
- Cloud cluster.
- Self-modifying governance.
- Autonomous deployment.
- Autonomous production merging.

These belong to later versions.

---

## 34. Engineering Rule

When uncertain, prefer:

```text
Simple
Modular
Observable
Reversible
Least privilege
Locally executable
```

Avoid:

```text
Complex
Distributed
Opaque
Irreversible
Over-permissioned
Cloud-dependent
```

---

## 35. Claude Code Working Rules

Before modifying this Jarvis project:

1. Inspect existing files.
2. Read project instructions.
3. Identify current state.
4. Explain the intended change.
5. Make the smallest safe change.
6. Run relevant tests.
7. Verify behavior.
8. Report exact changes.
9. Report failures honestly.

Do not claim success without evidence.

Do not fabricate tool results.

Do not silently skip verification.

Do not modify unrelated projects.

---

## 36. Review Policy

Perform local review before pushing.

Do not use cloud-based code review services.

Do not use `/code-review ultra`.

Do not use `/ultrareview`.

Report issues and suggested fixes only.

Cloud-based review requires explicit authorization.

---

## 37. Definition of Done

A feature is complete only when:

- Implementation exists.
- Relevant tests pass.
- Failure cases are considered.
- Permissions are enforced.
- Audit logging works.
- Documentation exists.
- Verification is performed.
- No unrelated changes exist.
- Actual behavior matches the specification.

---

## 38. Long-Term Direction

JARVIS will eventually expand into:

```text
Autonomous Engineering
        ↓
Research
        ↓
Project Management
        ↓
Knowledge Management
        ↓
Personal Assistant
        ↓
Voice
        ↓
Computer Control
        ↓
Mobile
        ↓
Full Personal AI Operating System
```

Do not implement the future prematurely.

Build the foundation that makes future expansion safe.

---

# 39. Immediate Instruction to Claude

Treat this document as the current authoritative product specification.

Do not blindly implement future features.

Do not infer permissions beyond this document.

Do not change governance rules yourself.

Do not merge independent projects into Jarvis.

Do not optimize for visual spectacle before functionality.

The immediate objective is:

> Build a small, reliable, local-first autonomous engineering agent.

It must be capable of:

**research → plan → code → test → verify → report.**

Start with inspection.

Do not begin implementation until the environment and repositories are understood.

After inspection, produce:

1. Architecture proposal.
2. Repository/environment inventory.
3. Implementation plan.
4. Risk assessment.
5. Phase 1 change list.

Then proceed incrementally.

---

# 40. External Open-Source Agent Ecosystem Reference

**Research snapshot:** 2026-10-06

This section records external open-source projects and research ecosystems
that are relevant to JARVIS.

These projects are references, not architectural authorities.

JARVIS must not copy their architecture blindly.

The purpose is to understand:

- Existing agent patterns.
- Autonomous coding loops.
- Research agents.
- Memory systems.
- Tool orchestration.
- MCP integration.
- Sandboxing.
- Long-running execution.
- Evaluation.
- Local model execution.
- Open-weight coding models.
- Failure modes.
- Community practices.

When studying an external project, separate:

```text
OBSERVED FACT
    ↓
USEFUL PATTERN
    ↓
JARVIS-SPECIFIC DECISION
```

Do not confuse popularity with correctness.

Do not add dependencies merely because another project uses them.

---

## 40.1 Autonomous Coding and Software Engineering Agents

### OpenHands

Repository:
https://github.com/All-Hands-AI/OpenHands

OpenHands is an open-source agentic software development environment.

Relevant capabilities include:

- Autonomous software engineering.
- Repository interaction.
- Shell/tool use.
- Browser interaction.
- Sandboxed execution.
- Agent SDK/runtime concepts.
- Evaluation through the OpenHands Index.

Why JARVIS should study it:

- Strong reference for autonomous engineering workflows.
- Useful comparison for sandboxed coding.
- Useful reference for agent/tool boundaries.
- Useful reference for long-running engineering tasks.
- Useful benchmark and evaluation ecosystem.

Do not assume OpenHands should become the JARVIS core.

JARVIS has a different objective:

```text
JARVIS = orchestrator + governance + project intelligence
OpenHands = autonomous engineering environment
```

---

### SWE-agent

Repository:
https://github.com/SWE-agent/SWE-agent

SWE-agent is a research-oriented agent for solving real GitHub
software issues with language models.

The project is particularly important because it exposes a relatively
simple agent-computer interface.

Current project guidance states that mini-SWE-agent has superseded
SWE-agent for much current development.

Why JARVIS should study it:

- Minimal agent architecture.
- Research-friendly implementation.
- Tool/interface design.
- GitHub issue → agent → patch workflow.
- Reproducible software-engineering experiments.
- Strong connection to SWE-bench.

Important lesson:

> Simple agent scaffolds can be surprisingly capable.

Do not over-engineer JARVIS before measuring the need.

---

### mini-SWE-agent

Repository:
https://github.com/SWE-bench/SWE-bench

The SWE-bench ecosystem now includes a very small coding-agent
implementation commonly referred to as mini-SWE-agent.

Why JARVIS should study it:

- Demonstrates how small an effective coding harness can be.
- Useful counterexample to unnecessarily large agent runtimes.
- Useful for experiments on task decomposition and tool use.

JARVIS should prefer simplicity where capability does not suffer.

---

### Aider

Repository:
https://github.com/Aider-AI/aider

Aider is an open-source terminal-based AI pair-programming system.

Relevant ideas:

- Existing-codebase operation.
- Repository mapping.
- Git-aware changes.
- Multi-file editing.
- Model/provider flexibility.
- Human + agent collaboration.

Why it matters to JARVIS:

Aider demonstrates that useful coding agents can remain relatively
small and model-independent.

JARVIS should study:

- Repository understanding.
- Diff-oriented editing.
- Git workflows.
- Model abstraction.

JARVIS should not replace Claude Code with Aider automatically.

Claude Code remains the current controlled coding worker.

---

### Cline

Repository:
https://github.com/cline/cline

Cline is an open-source autonomous coding agent.

Relevant ideas:

- Planning and execution.
- File editing.
- Command execution.
- Browser/tool interaction.
- Human approval boundaries.
- MCP integration.
- Autonomous operation.

Why JARVIS should study it:

- Agent permission UX.
- Tool orchestration.
- Coding workflow design.
- MCP usage.
- Approval patterns.

Important:

JARVIS governance must be enforced outside the model.

UI approval prompts alone are not sufficient security.

---

### Goose

Repository:
https://github.com/block/goose

Goose is an open-source, extensible local agent from Block.

Relevant ideas:

- Local execution.
- Extensible tools.
- MCP integration.
- Coding and engineering tasks.
- Model/provider flexibility.

Why JARVIS should study it:

- Plugin/tool architecture.
- Local-first operation.
- MCP integration.
- Extensibility without forcing every feature
  into the core.

This aligns strongly with JARVIS's adapter-first philosophy.

---

### Gemini CLI

Repository:
https://github.com/google-gemini/gemini-cli

Gemini CLI is an open-source terminal AI agent.

Relevant ideas:

- Terminal-first operation.
- Persistent project context.
- Checkpointing.
- Skills.
- MCP integration.
- File and shell tools.
- Policy/trusted-folder controls.
- Non-interactive/headless execution.

Why JARVIS should study it:

- CLI design.
- Context files.
- Checkpoint/resume behavior.
- Policy controls.
- MCP integration.
- Headless automation.

JARVIS should remain model-independent.

---

### OpenCode

Repository:
https://github.com/anomalyco/opencode

OpenCode is an open-source local coding agent.

The repository's security documentation is especially relevant.

It explicitly describes shell, file, and web capabilities and
documents that its permission mechanism is not a true sandbox.

Why JARVIS should study it:

- Local agent architecture.
- Tool permissions.
- Security tradeoffs.
- Model/provider abstraction.

Important security lesson:

> Permission prompts are not equivalent to sandboxing.

JARVIS requires real capability enforcement and sandbox boundaries.

---

### Roo Code

Repository:
https://github.com/RooCodeInc/Roo-Code

Roo Code was an open-source multi-mode coding agent.

The repository was archived on 2026-05-15.

Relevant historical concepts:

- Code mode.
- Architect mode.
- Ask mode.
- Debug mode.
- Custom modes.
- MCP integration.

Why retain this reference:

The mode separation is useful for thinking about specialized
agent behavior.

Status matters:

> Archived. Use as historical/reference material, not as a dependency.

---

### Continue

Repository:
https://github.com/continuedev/continue

Continue was an influential open-source coding agent available through
CLI and IDE integrations.

The repository is now read-only after its final 2.0 release.

Why study it:

- IDE/CLI integration patterns.
- Open-source coding-agent evolution.
- Model/provider abstraction.
- Community-driven developer tooling.

Status:

> Historical/reference project. Not an active JARVIS dependency.

---

## 40.2 General Autonomous Agent and Personal Assistant Systems

### AutoGPT

Repository:
https://github.com/Significant-Gravitas/AutoGPT

AutoGPT is one of the most historically important open-source
autonomous-agent projects.

The current platform supports:

- Agent creation.
- Complete workflows.
- Scheduling.
- Triggers.
- Integrations.
- Self-hosting.
- Visual workflow construction.

The original AutoGPT Classic is now unsupported.

Why JARVIS should study AutoGPT:

- Historical autonomous-agent patterns.
- Goal decomposition.
- Long-running execution.
- Scheduling.
- Tool integration.
- Agent lifecycle.

Important lesson:

Early autonomous agents often exposed the problem of giving an
LLM too much freedom without strong execution controls.

JARVIS should learn from those failure modes.

---

### OpenClaw

Repository:
https://github.com/openclaw/openclaw

OpenClaw is an open-source personal AI assistant designed to run
on the user's own devices and communicate through many channels.

Relevant concepts:

- Local state.
- Persistent memory.
- Multiple model/harness backends.
- Messaging channels.
- Desktop/mobile interfaces.
- Personal-assistant operation.
- Credential and state locality.

Why JARVIS should study it:

- Personal-assistant architecture.
- Local-first state.
- Channel abstraction.
- Model/harness abstraction.
- Device-oriented deployment.

Important distinction:

```text
OpenClaw = personal assistant / device-channel system
JARVIS   = autonomous engineering + R&D orchestrator first
```

JARVIS may later learn from this category.

---

### Hermes Agent

Repository:
https://github.com/NousResearch/hermes-agent

Hermes is an open-source personal AI agent from Nous Research.

Relevant concepts:

- Persistent memory.
- Skills.
- Learning from experience.
- Subagents.
- Scheduled jobs.
- Terminal.
- Browser.
- Messaging gateway.
- Desktop interface.
- Model/provider flexibility.

Why JARVIS should study it:

- Skill architecture.
- Persistent agent state.
- Experience-driven improvement.
- Background jobs.
- Personal-assistant interfaces.

Important lesson:

> Skills should be composable extensions, not core bloat.

---

### Letta

Repository:
https://github.com/letta-ai/letta

Current active source:
https://github.com/letta-ai/letta-code

Letta evolved from MemGPT and focuses heavily on stateful agents.

Relevant ideas:

- Persistent memory.
- Agent identity.
- Long-term state.
- Stateful conversations.
- Local/self-hosted operation.
- Agent SDK.
- Agent channels.

Why JARVIS should study it:

- Long-term memory architecture.
- Agent identity.
- State persistence.
- Memory lifecycle.
- Context management.

JARVIS should not blindly adopt a single memory architecture.

Our memory model deliberately separates:

```text
USER MEMORY
PROJECT MEMORY
TASK STATE
DECISION MEMORY
WORKFLOW MEMORY
AGENT STATE
AUDIT LOG
SYSTEM CONFIG
SECRET STORE
```

---

## 40.3 Agent Frameworks and Orchestration Systems

These are potential implementation references.

They are not automatically JARVIS dependencies.

### LangGraph

Repository:
https://github.com/langchain-ai/langgraph

LangGraph focuses on stateful agent workflows.

Relevant concepts:

- Graph-based workflows.
- Persistent checkpoints.
- Cycles.
- Human-in-the-loop.
- Long-running tasks.
- Stateful execution.

Why study it:

JARVIS has a naturally stateful execution loop.

However, JARVIS should first implement its own minimal orchestration
model rather than adopting a large framework prematurely.

---

### LangChain / Deep Agents

Repository:
https://github.com/langchain-ai/langchain

LangChain provides broad model/tool abstractions.

Its ecosystem includes:

- LangGraph.
- Deep Agents.
- Integrations.
- Agent observability/evaluation tooling.

Why study it:

- Model interoperability.
- Tool abstraction.
- Agent composition.
- Long-running agent patterns.

Risk:

A large general framework can become the architecture instead of
serving the architecture.

Avoid framework-driven design.

---

### CrewAI

Repository:
https://github.com/crewAIInc/crewAI

CrewAI focuses on role-based multi-agent orchestration.

Relevant ideas:

- Agents.
- Tasks.
- Crews.
- Flows.
- Tool integrations.
- Workflow orchestration.

Why study it:

Useful reference for future multi-agent systems.

Not required for v0.1.

JARVIS should remain single-orchestrator first.

---

### Microsoft Agent Framework

Current successor to AutoGen.

AutoGen repository:
https://github.com/microsoft/autogen

Microsoft's repository currently states that AutoGen is in maintenance
mode and recommends Microsoft Agent Framework for new development.

Why study the ecosystem:

- Agent orchestration.
- Multi-agent workflows.
- Human interaction.
- Tool execution.
- Enterprise patterns.

Do not begin JARVIS with AutoGen.

---

### Pydantic AI

Repository:
https://github.com/pydantic/pydantic-ai

Pydantic AI is a typed Python agent framework.

Relevant ideas:

- Typed agent interfaces.
- Structured outputs.
- Tools.
- MCP.
- Evals.
- Guardrails.
- Persistence.
- Durable execution.
- Coding/research agent capabilities.

Why JARVIS should study it:

Strong reference for type-safe agent orchestration.

Potentially useful later if JARVIS needs a typed agent layer.

---

### Agno

Repository:
https://github.com/agno-agi/agno

Agno provides an SDK/runtime/control-plane approach for agent systems.

Relevant ideas:

- Agent platforms.
- Memory.
- Knowledge.
- Guardrails.
- MCP.
- APIs.
- Control plane.
- Observability.

Why study it:

Useful reference for a future production control plane.

Do not introduce its infrastructure into v0.1 unless required.

---

### Mastra

Repository:
https://github.com/mastra-ai/mastra

Mastra is a TypeScript framework for AI applications and agents.

Relevant concepts:

- Workflows.
- Agents.
- Memory.
- MCP.
- Evaluation.
- Developer tooling.
- TypeScript-first orchestration.

Why study it:

Useful alternative architectural perspective.

JARVIS should not become TypeScript-first merely because Mastra does.

---

## 40.4 Model Context Protocol Ecosystem

### Model Context Protocol Specification

Repository:
https://github.com/modelcontextprotocol/modelcontextprotocol

MCP standardizes interaction between AI applications and external
context/tools.

Current architecture separates:

```text
Host
  ↓
MCP Client
  ↓
MCP Server
  ↓
Tool / Resource
```

Why this matters to JARVIS:

JARVIS already depends conceptually on adapters.

MCP can provide a standardized integration boundary for:

- Project tools.
- Research tools.
- Memory systems.
- GitHub.
- Filesystems.
- Databases.
- Verification systems.

JARVIS should use MCP where it provides a clean boundary.

Do not force every internal component through MCP.

Internal calls can remain direct when safer and simpler.

---

### Official MCP Servers

Repository:
https://github.com/modelcontextprotocol/servers

Reference servers include examples for:

- Filesystem.
- Git.
- Memory.
- Fetch.
- Time.
- Sequential thinking.

Important warning from the project:

These are reference implementations.

They should not automatically be treated as production-secure
components.

JARVIS must evaluate each tool against its own threat model.

---

## 40.5 Open-Weight Models and Local Inference

JARVIS is model-independent.

However, local models may eventually reduce:

- API cost.
- Network dependency.
- Latency for simple tasks.
- Privacy exposure.
- Background execution cost.

### Qwen3-Coder

Repository:
https://github.com/QwenLM/Qwen3-Coder

Qwen3-Coder is an open coding-model family with an ecosystem around
coding agents and local/open-weight deployment.

Why study it:

- Coding capability.
- Open-weight model ecosystem.
- Local model possibilities.
- Agent-oriented coding workflows.

Do not assume a local model should replace Claude Code.

Use measured evaluations.

---

### DeepSeek-Coder

Repository:
https://github.com/deepseek-ai/DeepSeek-Coder

DeepSeek-Coder is a family of code language models trained heavily
on project-level code.

Why study it:

- Open coding-model history.
- Code completion/infill.
- Local coding-model experiments.
- Model capability benchmarking.

It may be useful for future low-cost/local coding experiments.

---

### llama.cpp

Repository:
https://github.com/ggml-org/llama.cpp

llama.cpp provides local LLM/VLM inference across a broad range
of hardware.

Relevant capabilities:

- Local inference.
- Quantization.
- CUDA support.
- CPU/GPU hybrid inference.
- OpenAI-compatible server.
- Hugging Face model loading.

Why JARVIS should study it:

It is a strong foundation for future local-model execution.

The architecture should allow:

```text
JARVIS
  ↓
MODEL ABSTRACTION
  ↓
Cloud model OR local model
```

without changing task logic.

---

### Ollama

Repository:
https://github.com/ollama/ollama

Ollama provides a simple local model runtime and API.

Relevant ideas:

- Local model management.
- REST API.
- OpenAI-compatible interface.
- Windows support.
- Coding-agent integrations.

Why study it:

It may provide the simplest route for local-model experiments
on the user's laptop.

Do not make Ollama mandatory.

---

## 40.6 Evaluation and Benchmark Ecosystem

JARVIS must be evaluated as a system.

Do not measure only model intelligence.

### SWE-bench

Repository:
https://github.com/SWE-bench/SWE-bench

SWE-bench evaluates systems against real GitHub software issues.

Important concepts:

- Real repositories.
- Real issues.
- Patch generation.
- Reproducible evaluation.
- Docker-based execution.
- SWE-bench Verified.
- Multimodal variants.

Why JARVIS should study it:

Useful for measuring autonomous software-engineering performance.

Potential future JARVIS benchmark:

```text
Task
→ Agent trajectory
→ Patch
→ Tests
→ Verification
→ Result
```

---

### OpenHands Index

Repository:
https://github.com/OpenHands/openhands-index-results

The OpenHands Index expands beyond simple bug fixing.

It covers areas such as:

- Bug fixing.
- Application creation.
- Test generation.
- Information gathering.

Why JARVIS should study it:

JARVIS's mission extends beyond coding.

This benchmark category is closer to the long-term JARVIS direction.

---

### AgencyBench

Repository:
https://github.com/GAIR-NLP/AgencyBench

AgencyBench evaluates long-horizon real-world autonomous-agent tasks.

It covers:

- Backend development.
- Code.
- Frontend.
- Games.
- Research.
- MCP.

Its tasks can require many tool calls and long execution periods.

Why this matters:

JARVIS is explicitly intended to perform long-running autonomous work.

AgencyBench is therefore a useful reference for future system-level
evaluation.

---

### SWE-agent / SWE-bench Ecosystem

Organization:
https://github.com/SWE-bench

This ecosystem includes:

- SWE-bench.
- SWE-agent.
- SWE-smith.
- Experiment results.
- Sandbox/evaluation infrastructure.

Why study it:

It demonstrates the importance of evaluating the complete stack:

```text
Model
+
Agent scaffold
+
Tools
+
Environment
+
Task
+
Evaluation
```

This reinforces a core JARVIS principle:

> Agent performance is a system property, not only a model property.

---

## 40.7 External Ecosystem Comparison

Use this mental map:

```text
                 OPEN-SOURCE AGENT ECOSYSTEM

       PERSONAL ASSISTANTS
       ├── OpenClaw
       ├── Hermes
       └── Letta

       AUTONOMOUS CODING
       ├── OpenHands
       ├── SWE-agent / mini-SWE-agent
       ├── Aider
       ├── Cline
       ├── Goose
       ├── OpenCode
       ├── Gemini CLI
       └── historical Roo / Continue

       AGENT FRAMEWORKS
       ├── LangGraph
       ├── CrewAI
       ├── Pydantic AI
       ├── Agno
       ├── Mastra
       └── Microsoft Agent Framework

       TOOL / CONTEXT PROTOCOL
       └── MCP

       LOCAL MODEL RUNTIMES
       ├── llama.cpp
       └── Ollama

       OPEN CODING MODELS
       ├── Qwen3-Coder
       └── DeepSeek-Coder

       EVALUATION
       ├── SWE-bench
       ├── OpenHands Index
       └── AgencyBench
```

---

## 40.8 What JARVIS Should Learn From These Projects

### 1. Keep the core small

mini-SWE-agent and Aider show that useful agent behavior
does not require an enormous framework.

### 2. Separate orchestration from execution

JARVIS should orchestrate workers.

It should not become one giant coding agent.

### 3. Treat tools as capabilities

Tools should have:

- Identity.
- Scope.
- Permission.
- Risk.
- Auditability.
- Revocation.

### 4. Use real sandboxing

A permission prompt is not a security boundary.

### 5. Persist state

Long-running work requires:

- Task state.
- Checkpoints.
- Recovery.
- Resume.
- Audit history.

### 6. Evaluate the complete system

Measure:

```text
Model
+
Prompt/context
+
Agent loop
+
Tools
+
Environment
+
Verification
```

### 7. Prefer model independence

The agent should survive model changes.

### 8. Keep integrations modular

MCP is useful where a protocol boundary helps.

Adapters remain appropriate for internal systems.

### 9. Make verification independent

The agent should not be the sole judge of its own success.

### 10. Do not equate autonomy with unrestricted access

The strongest systems increasingly combine:

```text
Autonomy
+
Tool use
+
State
+
Evaluation
+
Security boundaries
```

not unrestricted computer access.

---

## 40.9 What JARVIS Should NOT Copy

Do not copy:

- Another project's complete architecture.
- Another project's UI.
- Another project's prompt hierarchy.
- Another project's memory model.
- Another project's agent loop without testing it.
- Another project's permission model.
- Another project's cloud assumptions.
- Another project's dependency graph.
- Another project's multi-agent design.
- Another project's benchmark claims as proof of JARVIS capability.

Do not add a framework because it is popular.

Do not add an agent because it has many GitHub stars.

Do not treat benchmark performance as production safety.

Do not treat an open-source license as proof of security.

---

## 40.10 Research Tracking Rule

External projects must be treated as moving targets.

For important dependencies or references, periodically record:

```text
Project
Repository
Current status
Last checked
License
Architecture relevance
Security relevance
Performance relevance
Potential use
Known limitations
Decision
```

Possible decisions:

```text
WATCH
STUDY
EXPERIMENT
ADAPT
INTEGRATE
REJECT
HISTORICAL
```

The default decision is:

> WATCH / STUDY

Integration requires a separate architectural decision.

---

## 40.11 Current JARVIS Position

JARVIS is not intended to compete with all these projects.

Its unique target is the orchestration layer across the user's
existing engineering ecosystem.

Conceptually:

```text
                       JARVIS
                          |
              +-----------+-----------+
              |           |           |
          Research     Coding     Verification
              |           |           |
              v           v           v
          Research     Claude      UV / Guardrails
          Engines       Code
              |           |
              +-----+-----+
                    |
                    v
             Project Systems
                    |
        +-----------+-----------+
        |           |           |
      Swarag     MCP      Future Projects
```

External projects should therefore be viewed as components of the
ecosystem JARVIS may interoperate with.

JARVIS itself remains the coordinator.

---

## 40.12 Immediate Research Priority

Do not integrate any of these projects yet.

First inspect and build the minimal JARVIS core.

After Phase 0 and Phase 1, evaluate experimentally:

1. OpenHands.
2. mini-SWE-agent.
3. Goose.
4. Gemini CLI.
5. OpenClaw.
6. Hermes.
7. Letta.
8. LangGraph.
9. Pydantic AI.
10. MCP.
11. Qwen3-Coder.
12. llama.cpp / Ollama.

For each experiment, answer:

```text
What problem does it solve?
Can JARVIS solve it more simply?
Should JARVIS integrate it?
Should JARVIS only use it as a worker?
Does it create a new security boundary?
Does it increase operational complexity?
Does it improve measurable capability?
Can it remain optional?
```

The answer must be evidence-based.

---

## 40.13 Source References

Primary references reviewed for this section:

- OpenHands: https://github.com/All-Hands-AI/OpenHands
- SWE-agent: https://github.com/SWE-agent/SWE-agent
- SWE-bench: https://github.com/SWE-bench/SWE-bench
- Aider: https://github.com/Aider-AI/aider
- Cline: https://github.com/cline/cline
- Goose: https://github.com/block/goose
- Gemini CLI: https://github.com/google-gemini/gemini-cli
- OpenCode: https://github.com/anomalyco/opencode
- Roo Code: https://github.com/RooCodeInc/Roo-Code
- Continue: https://github.com/continuedev/continue
- AutoGPT: https://github.com/Significant-Gravitas/AutoGPT
- OpenClaw: https://github.com/openclaw/openclaw
- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Letta: https://github.com/letta-ai/letta
- LangChain: https://github.com/langchain-ai/langchain
- LangGraph: https://github.com/langchain-ai/langgraph
- CrewAI: https://github.com/crewAIInc/crewAI
- Microsoft AutoGen: https://github.com/microsoft/autogen
- Pydantic AI: https://github.com/pydantic/pydantic-ai
- Agno: https://github.com/agno-agi/agno
- Mastra: https://github.com/mastra-ai/mastra
- MCP specification: https://github.com/modelcontextprotocol/modelcontextprotocol
- MCP servers: https://github.com/modelcontextprotocol/servers
- Qwen3-Coder: https://github.com/QwenLM/Qwen3-Coder
- DeepSeek-Coder: https://github.com/deepseek-ai/DeepSeek-Coder
- llama.cpp: https://github.com/ggml-org/llama.cpp
- Ollama: https://github.com/ollama/ollama
- OpenHands Index results: https://github.com/OpenHands/openhands-index-results
- AgencyBench: https://github.com/GAIR-NLP/AgencyBench

This research is a reference layer.

It does not override the JARVIS specification above.

---

# 41. Updated Instruction to Claude Code

Before implementing any new architecture, consider the external
ecosystem documented in Section 40.

Do not copy external systems.

Use them to challenge assumptions.

When proposing an architectural decision, state where appropriate:

```text
JARVIS DECISION
EXTERNAL PATTERN CONSIDERED
WHY ADOPTED / REJECTED
TRADEOFF
SECURITY IMPACT
COMPLEXITY IMPACT
```

Prefer the simplest architecture that meets JARVIS requirements.

External project adoption requires explicit architectural justification.

The default is:

**Study first. Integrate later.**

