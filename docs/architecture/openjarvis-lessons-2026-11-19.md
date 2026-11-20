# What we can learn from OpenJarvis (2026-11-19)

**NON-AUTHORITATIVE.** A comparison written by Local Claude at RK's request. It decides nothing; any change it suggests needs its own decision under ADR-0001. Do not confuse the project below with this one: it is an unrelated open-source project that shares the name.

## Sources and what was and was not read

Read: the project's README on GitHub (`open-jarvis/OpenJarvis`), its Stanford "Scaling Intelligence" blog post, its documentation home page, and the documentation pages on memory and security architecture. **Not read: its source code**, and the pages on tools, system access, learning, telemetry and skills (the pages gave names only). Everything below is what those pages say, not what the code does. Product facts may have changed since.

## What it is

Apache-2.0 framework for personal AI that runs on the user's own device, from the Hazy Research and Scaling Intelligence groups at Stanford. Stated design: shared building blocks for on-device agents, evaluation that counts energy, latency and money alongside accuracy, and a learning loop that improves models, prompts and settings from locally kept usage traces. Local by default; cloud only as a fallback. It describes five parts: a model catalogue, an inference engine layer (Ollama and others, with hardware detection and a health command), agents (several kinds, including scheduled and always-on ones), tools and memory, and learning.

## Side by side

| Topic | OpenJarvis (per its pages) | JARVIS here | Assessment |
|---|---|---|---|
| Local-first model | Ollama and others, picks an engine from the hardware | Ollama, one approved model, GPU or CPU chosen automatically and reported | Same idea; ours is narrower and governed by an approved-models list |
| Health check | `doctor` command | `doctor` command, install check | Same |
| Permissions and audit | Guardrails are opt-in wrappers (warn, redact or block); an append-only audit table for security events; a sensitive-file check on file reads | Default-deny policy, hash-chained audit with an anchor, secret-location list, confirmation turns | Ours is stricter by default. Their opt-in default is the weaker choice |
| Memory | A searchable store of document chunks with retrieval and an injection size cap; delete one or clear all. The pages describe no user profile or fact extraction (a profile tool is named only) | None between sessions today; ADR-0016 proposes confirmed one-line notes | Their memory is document search, not "learning about the user", so there is little to copy for RK's request |
| Learning | Fine-tuning, prompt optimisation and engine tuning from local traces | None; ADR-0016 only stores confirmed notes | Heavy for this laptop, hard to reverse, and trains on personal data without a confirmation step. Not for the Beta |
| Skills | Portable skill format, importable from other projects and GitHub | Governed launch catalogue of approved apps | Importing third-party skills means running outsiders' instructions or code. Against our rules for now |
| Scheduling | Scheduled and always-on agents (a morning digest, a monitor) | Nothing runs unless asked | Needs a long-running process surface and an ADR |
| Efficiency | Measures latency, throughput and energy per query with a bench command | `--timing` and measured scripts, evidence in `docs/environment/` | A repeatable bench script would help |
| Interface | Command line, browser app, desktop apps | Dashboard, voice, phone via a private network | Comparable |

## Ideas worth taking, in order of value (none adopted)

1. **Scan before saving (cheap, deterministic).** Their secret and personal-data scanners run on text before it is stored or sent. Adopted in ADR-0016 D6 for notes about sir, and the same check could guard ordinary notes.
2. **A size budget on anything injected into the model.** They cap injected memory (about 2,048 tokens, a minimum relevance). ADR-0016 D5 adopts the same idea with a hard cap.
3. **Delete one and clear all as first-class controls.** Adopted in ADR-0016 D4.
4. **A repeatable bench script** reporting time to first word, tokens per second and the part of the model on the GPU, so measurements such as the 37 against 11 tokens per second can be rerun on any machine. Engineering item, no governance needed beyond review.
5. **A scheduled morning briefing** (weather and headlines at a set time). Attractive, but it needs a process that runs without being asked; post-Beta and an ADR.
6. **Hardware detection at start** to explain placement. Mostly done (the advisor reports where the model sits).

## Ideas rejected for now, and why

Model or prompt training from traces (heavy, personal data, hard to reverse); importing skills from other projects (untrusted code and instructions); opt-in guardrails (we default to refusing); a vector memory (not needed for one-line notes, adds a dependency, and installs need RK's per-item approval).

## UNVERIFIED

That the documentation matches the code; how their audit, approval and sandbox modules behave (only their names were visible); how their memory behaves in use. Worth a second look at their security pages and source only if RK wants a deeper comparison.

## Part 2: how it is developed and deployed (added 2026-11-20)

Read in addition: the public repository's metadata, root listing, release list, workflow names, `REVIEW.md`, `CONTRIBUTING.md`, the top of `CHANGELOG.md`, and the documentation pages on architecture overview, learning, security and system access. Still not read: the source code, and the workflow files themselves (names only).

### Facts

- Created February 2026; about 17,000 stars and 4,000 forks; 96 open issues; pushed to within a day of this reading. Python with a Rust bridge, a TypeScript front end and a desktop app. Apache-2.0. Releases: a tagged v1.0.0 (May 2026) and separate desktop releases (latest November 2026).
- **Process:** conventional commits, Ruff formatting enforced by a pre-commit hook and by CI, `uv` for packages, a Keep-a-Changelog file, a public roadmap, an issue template per kind, "comment `take` to claim an issue", and contributor tiers (contributor, reviewer, maintainer). Larger changes need an issue first. Changes that add dependencies or break the public interface are "unlikely to be merged".
- **Automated checks (workflow names):** tests, a static security scan (SAST), a docs build, a front-end build, a desktop build, Docker validation, an installer integration test, PyPI publishing, automatic tagging, and two that use Claude: one reviews each pull request, one triages issues.
- **The review rule file (`REVIEW.md`)** is a short checklist: relevance, completeness (does it do what the title claims, not stubbed), correctness (with the project's own hazards named), tests, security. It says what not to comment on (style, naming, untouched code) and asks for findings labelled blocking, suggestion or nit.
- **Deployment:** a one-line installer per platform; Docker, systemd, launchd and Windows service files; a hosted-app config; a desktop installer; a host self-check command (disk encryption, cloud-sync agents, exposed engine ports, remote-access tools) and a data-boundary report (what is local-only versus cloud-capable).
- **Self-improvement is tiered:** edits proposed by the learning loop are classed auto (parameters, routing; applied only if a benchmark gate passes), review (system prompts, example sets; queued for the user) or manual (fine-tuning; never automatic), with a git-backed rollback.

### Their own documentation admits gaps worth noting

By their pages: capability checks are open by default; the confirmation setting for tools "is accepted but never read"; the shell tool has no allowlist or sandbox unless enabled; the server and desktop app auto-approve tools; guardrails default to warn rather than block; prompt-injection defence is not covered. They are frank about it, which is good practice. None of this is a model for our security, which defaults to refusal. Their security pages do not make their approach safe to copy; they show what we already chose against.

### Where we are stronger, where weaker

| Area | Us | Them |
|---|---|---|
| Default security | default-deny policy, hash-chained audit with anchor, confirmation turns, exact Host and Origin, per-launch tokens | opt-in or warn-only for most controls |
| Governance | ADRs, RK's merge as the only approval, a protected main | maintainers merge; contributor ladder |
| Automated checks | **none in the repository**: tests, a secret scan and the install check run by hand on the laptop | a dozen workflows |
| Release process | manual; release notes in `docs/beta/`; no tag yet | autotag, changelog, signed installers, PyPI |
| Scope | narrow, with a stated cut order | very wide (mining, operators, channels, workflows, 30+ benchmarks); a caution about scope growth |
| Learning | none yet; ADR-0016 proposes confirmed notes | trace-driven, tiered, partly stubbed |

### Proposals from this, none adopted, each its own decision

1. **A review checklist file (`REVIEW.md`).** Docs only. The relevance, completeness, correctness, tests and security list plus blocking, suggestion and nit labels, with our hazards named (new socket or process, a new write route, a secret read, a governance file edited). Makes every pull request review, mine or an outside tool's, the same.
2. **A continuous-integration workflow** that runs the unit tests (and a secret scan) on every pull request. Today nothing runs unless run by hand. Open question: whether the 808 tests pass on a clean hosted Windows machine with no `D:\JARVIS` folder (UNVERIFIED). Adding a workflow is a repository-governance change, so RK decides; I would try it on a branch first.
3. **A read-only `doctor --boundaries`** that prints what leaves this machine (the lookup allowlist, whether the model server is loopback only, whether the private-network proxy exposes anything public, Smart App Control on). Aligns with ADR-0011 A4.6.5. Needs its own small decision.
4. **A tagged release for the Beta** with a changelog entry and checksums (already on the Beta list as B-13 in spirit).
5. **A tiering of any future self-improvement** (auto / review / manual) borrowed as vocabulary if learning ever goes beyond ADR-0016: for us only "review" and "manual" would exist, never "auto".
6. **A scheduled briefing** and a **message-channel front end** (Telegram, WhatsApp) are the two features most likely to tempt. A channel puts every message through a third party's servers, which is the reverse of our privacy line, so it would not replace the private network chosen for the phone.

### Rejected for us

Anonymous usage sharing and a public savings leaderboard (a prize for sharing data); training on usage; third-party skill import; a general shell tool for the model; wide scope for its own sake.

## Part 3: a closer reading of the repository (added 2026-11-20)

Read in addition to Parts 1 and 2: four of their workflow files (CI, the security scan, the Claude review job, the installer test, the auto-tag job), the release checklist, the pull-request template, the Dependabot file, their supply-chain policy (`.github/security/`), the roadmap, the open issues, the list of source modules and tests, and the opening of these modules: injection scanner, taint tracking, subprocess sandbox, SSRF guard, capability policy, host command and doctor. Still not read: the bodies of those modules beyond their openings, and any running behaviour. All of this is UNVERIFIED as to whether the code does what its names and comments say.

### New facts

- **Their CI is a gate in order.** A security job (a static scan with Bandit, a check of every locked Python and Rust dependency against public advisory databases, and a diff-based Semgrep scan) runs first; the lint job then fails unless the security result is exactly "success", so a skipped or cancelled scan cannot turn the check green. Tests run on Python 3.11 and 3.12 on Linux; installers are tested in fresh Ubuntu and Fedora containers and on macOS, nightly and on any change to the installer, ending with install, `doctor`, uninstall and a check that nothing is left behind.
- **Supply-chain policy is written down.** Advisory exceptions are a reviewed file: exact package and version, exact advisory IDs, a reason, a link, and an expiry within 90 days; expired, duplicate, wildcard or malformed entries fail the build; a new advisory on an excepted package is still rejected. Unknown package sources fail. Dependency updates arrive weekly, grouped, at most two pull requests at a time.
- **Their Claude review job is locked down:** it can be triggered only by owners, members and collaborators (not by outside commenters, who could otherwise reach the API key); it has least privilege on the repository; it reads the instructions from the checked-in `REVIEW.md`. They also note that their attempt to require the check by repository rule failed for lack of rights, so the rule exists as a prepared file. A reminder that a check not made mandatory is advice.
- **Release checklist (manual, on real machines):** fresh account on each platform; install within 5 minutes; first reply within 2 seconds of start; `doctor` exits clean; running the installer twice changes nothing ("already done"); uninstall leaves nothing; one failure drill per release (cut the network mid-install, delete the config, delete the environment, run as root).
- **Roadmap, honestly tagged:** each item is Ready, Design Needed or Research-Stage. Phone access is a named workstream: they chose message channels (iMessage and SMS through a paid relay, Slack) plus a browser tab, and say WhatsApp is blocked for unofficial clients.
- **Open issues show real defects:** among them "the Rust fast path of the shell tool ignores timeout, environment cleaning and exit code" and a pending fix to "enforce filesystem allowlists in tools". Their security surface is large and still being closed. 96 issues open on a project of this size is not unusual, but it confirms that wide scope costs.
- **Their guards worth comparing with ours:**
  - an SSRF guard that refuses private, loopback, link-local and cloud-metadata addresses, including addresses hidden inside IPv6 forms, checked on the address a name resolves to;
  - taint labels (personal, secret, private, external) with a table of which outbound tools may never receive which label;
  - a sandboxed subprocess with a cleaned environment (only a short list of variables passed) and an output cap;
  - prompt-injection patterns (override attempts, identity changes, exfiltration phrases, jailbreak names);
  - a host check and a data-boundary report.

### What we may have missed, by priority (each is a proposal, none adopted)

1. **A check that a lookup's resolved address is public.** Our fetcher (ADR-0014) allows only listed hosts, HTTPS only, certificate checked, no redirect, no cookie. It does not check what address the host name resolves to. With only public hosts on the list the risk is small, but a resolved-address check is cheap and is the one concrete hardening their SSRF module suggests. Would be a small ADR-0014 amendment. UNVERIFIED whether our code already refuses private results; I found no such check.
2. **Automatic dependency and secret scanning in the repository.** Secret scanning and push protection are already on for our repository. Dependency security alerts are disabled. Turning on alerts (not automatic upgrade pull requests, since pinned packages must not be upgraded) is a repository setting for RK. Our voice and fetcher environments live outside the repository, so an advisory check against their pinned list would be a script, not a setting.
3. **A required-check gate.** If CI is ever added, add it to the existing ruleset only on RK's word, and copy their lesson: the later job must fail unless the scan result is exactly success.
4. **A release drill list.** Their manual checklist maps to our B-10 clean-machine test: add "run the start script twice, second run changes nothing", "uninstall leaves nothing", "first reply time", and one failure drill (stop the model server mid-conversation; delete the models list; start with the voice folder missing) to the Beta rehearsal. Docs only.
5. **Review file and pull-request template.** Already proposed in Part 2; the template is three lines of question (what, how tested, checklist) and costs nothing.
6. **Injection patterns as a second, cheap layer for notes and remote lines.** We refuse instructions in data by design (the model's reply has no authority), so patterns are belt and braces. Worth considering only for ADR-0016 notes (an instruction inside a note) and for the phone profile, not as a main defence: pattern lists are easy to evade.
7. **Taint idea, reduced:** keep it as one rule: text that came from the phone, from a lookup or from a note about sir is never passed to a launch request or a lookup query. This follows from decisions already made (ADR-0016 D7, A4.6) and could be written as a test.

### Not worth copying

Their wide capability list with open-by-default grants; opt-in guardrails; auto-approval of tools in the server and desktop modes; a paid relay for phone messages; telemetry sharing; the learning loop beyond the tiering idea in Part 2.
