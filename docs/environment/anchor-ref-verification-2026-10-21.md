# Audit-anchor ref verification — 2026-10-21

**Purpose.** The ADR-0005 D7 check: does the ref that would carry the audit anchor have a ruleset that blocks force-push and deletion, with an empty bypass list? This note records what GitHub reported. It is evidence. It grants no authority. RK's merge of the pull request that adds it is the recorded check (ADR-0001 D6; ADR-0009 D5).

**Checked at:** 2026-10-21T14:11Z, by Local Claude, with read-only `gh api` calls against `Ramki-2010/JARVIS`. No token or credential is shown here.

## Result for `main`

| Control required by ADR-0005 D7 | Reported by GitHub | Result |
|---|---|---|
| A ruleset targets the carrying ref | `protect-main` (id 24887473), target `branch`, `ref_name.include = ["~DEFAULT_BRANCH"]`; default branch is `main` | PASS |
| Ruleset is active | `enforcement: active` | PASS |
| Force-push blocked | rule `non_fast_forward` present; reported in the rules that apply to `main` | PASS |
| Deletion blocked | rule `deletion` present; reported in the rules that apply to `main` | PASS |
| Pull request required | rule `pull_request` present (0 approvals required) | PASS |
| Bypass list empty | `bypass_actors: []`; `current_user_can_bypass: "never"` for the checking account | PASS |
| Code-owner review | `require_code_owner_review: false` (as designed while there is one account, ADR-0001 D9) | as designed |

`rules/branches/main` returned `deletion`, `non_fast_forward`, `pull_request`. The branch reports `protected: true` at commit `63f8d88f34bda188d985dd3fe6b7c7050224b9e5`. The repository is public and its default branch is `main`.

## Ruleset timestamps (baseline for later checks)

Read at 2026-10-21T14:39Z: `created_at` `2026-10-11T23:37:01.177+05:30`, `updated_at` `2026-10-11T23:37:01.214+05:30`, `enforcement: active`, default branch `main`, `main` at `63f8d88f34bda188d985dd3fe6b7c7050224b9e5`. The ruleset has not been edited since it was created. ADR-0009 D5 compares each later `updated_at` with this one.

## What this does not cover

- **Tags:** no ruleset targets tags (0 tag rulesets). A tag would not be a verified anchor.
- **Other branches:** the ruleset covers the default branch only.
- **Enforcement was not tested** by an attempted force-push or deletion. The result above is GitHub's configuration, not a behavioural test.

## Commands (read-only)

```text
gh api repos/Ramki-2010/JARVIS/rulesets
gh api repos/Ramki-2010/JARVIS/rulesets/24887473
gh api repos/Ramki-2010/JARVIS/rules/branches/main
gh api repos/Ramki-2010/JARVIS/branches/main
gh api repos/Ramki-2010/JARVIS
```
