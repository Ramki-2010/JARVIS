# Pull request review checklist

For every pull request, whether the reviewer is RK, a Claude session or an outside tool. It decides nothing by itself: the ADRs, the Master Context and RK's merge govern (ADR-0001). It exists so every review asks the same questions. Style is not a review topic here; a failing test run or a plain-language mistake is.

## 1. Does it do what it says?

- Does the change match its title and description, completely? A partly built or stubbed feature is a finding.
- Is anything claimed in the description that the diff does not show? Is anything in the diff the description does not mention?
- Are numbers in the description (test counts, timings) the ones the author measured? Anything not measured must be labelled UNVERIFIED.

## 2. Our hazards (any "yes" needs RK's decision, recorded in an ADR or amendment first)

- A new socket, port, listening address or allowed host? (ADR-0011 D3, ADR-0014 D3)
- A new process, or a new place that starts a process? (ADR-0011 D2)
- A new write route, or a new way for text typed or spoken to change state? (ADR-0011 D3.9)
- A secret, key, token, password or personal file read, printed, logged or committed? (ADR-0008, `policy/policy.toml`)
- A governance file, the launch catalogue, the approved-models list, the close list, the ruleset or a policy edited by JARVIS or by the change? (RK edits these)
- Anything that makes the dashboard, the phone path, a lookup or the model reach further than before?
- A change to what JARVIS says about itself that could claim an ability it lacks (or deny one it has)?
- Personal detail in a public file: a real path, name, login, hostname, address? (placeholders only)

## 3. Is it correct and tested?

- Does the failure case have a test (the refusal, the bad input, the timeout), not only the good case?
- Were tests weakened, skipped or loosened to turn them green? That is a finding.
- Does the full suite pass, and does the automated `tests` check pass?
- For anything that touches the real machine (microphone, GPU, firewall, a real network): was it run for real, and is the result stated, or marked UNVERIFIED?

## 4. Is it safe to merge?

- Is it one thing? A pull request that mixes a decision with unrelated code is split.
- Does it say what it did not change ("nothing else changed") and what remains UNVERIFIED?
- Does it carry the ADR-0001 D7 trigger block (the matched triggers, as a claim for RK to confirm)?
- Is the merge RK's word? A chat "yes" to an idea is an input; the merge of the written decision is the record (ADR-0001 D6).

## Labelling findings

- **blocking**: must change before merge (a hazard in section 2 without a decision, a false claim, a failing or weakened test).
- **suggestion**: worth doing, the author may decline with a reason.
- **nit**: take it or leave it.

Do not comment on unchanged code, and do not argue about naming preferences.
