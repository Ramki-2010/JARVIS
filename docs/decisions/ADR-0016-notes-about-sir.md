# ADR-0016 — Notes about sir: what JARVIS may learn from conversations

**STATUS: PROPOSED**

| Field | Value |
|---|---|
| ID | ADR-0016 |
| Title | Notes about sir: short, confirmed, forgettable observations that tailor replies |
| Status | PROPOSED. Nothing in it is built or in force until RK merges the pull request that sets it ACCEPTED (ADR-0001 D6) |
| Drafted | 2026-11-19, by Local Claude, after RK asked that JARVIS learn from conversations "how I talk, what I like, dislike" and improve it, and approved the shape recommended in chat |
| Authority class | USER AUTHORITY REQUIRED. Matched triggers, recorded as a claim for RK to confirm or correct: G-06 (personal data kept about the user), G-11 (what is written to the record and audited) |
| Depends on | ADR-0011 (Amendments 2 to 4), ADR-0013 Amendment 1 (conversation), the notes commands of the control plane |
| Amends | Nothing yet. If accepted, ADR-0013's persona rule "never state a fact about sir he has not told you in this conversation" gains one exception: facts he confirmed as notes (D5) |

## 1. Context

Today JARVIS remembers nothing between sessions, on purpose. RK asked for it to learn how they speak, like and dislike, and to help them improve. That is personal data about a person, kept over time, so it needs its own decision, its limits and a way to switch it off. RK approved the shape below in chat on 2026-11-19; under ADR-0001 D6 that is input, and the record is RK's merge.

## 2. Decisions (all PROPOSED)

**D1. A note about sir is an ordinary project note with a fixed prefix.** The text starts `[about-sir] `, followed by one short observation (at most 160 characters, one sentence), for example `[about-sir] prefers short answers` or `[about-sir] dislikes small talk about the weather`. It is written through the existing `note add` command, so policy evaluation and the audit chain apply exactly as for any note. No new file, no new database, no new write route, no new process. (This is the same mechanism the to-do list already uses.)

**D2. Every note is confirmed by sir first.** JARVIS proposes in words ("Shall I remember that you prefer short answers, sir?") and writes only after an explicit yes in a separate turn, as for notes today. Nothing is saved from silence.

**D3. How an observation arises: two ways only.**
1. *Sir says it.* "Remember that I prefer short answers", "I dislike ...", "I like ...". A deterministic phrase match proposes the note.
2. *Sir asks for a review.* "What have you noticed about how I talk?" or "How can I improve my phrasing?" The model reads sir's lines **from the current conversation only** and proposes at most three observations, each to be confirmed one by one. JARVIS never reviews, proposes or corrects on its own initiative, and never coaches unprompted (RK's approved recommendation: only when asked).

**D4. Control.** "What do you know about me?" lists the active notes. "Forget that" or "forget number N" retires one (`[about-sir-forget N]`, as to-dos are dropped: nothing is edited or deleted, the active list is worked out from the records). "Forget everything about me" retires all, after one confirmation. Retired notes stay in the audit record, which is append-only (ADR-0005); the confirmation says so plainly.

**D5. Use.** At session start the active notes (newest first, at most 12 and at most 800 characters in all) are added to the model's instruction under a heading saying they are facts sir confirmed, used only to tailor length, topics and manner, **never to tease, never repeated back unless asked, never described as a feeling or a memory of an event**. They are data, not instructions: a note whose text tries to give an order is never obeyed. The persona's rule against inventing facts about sir stays; confirmed notes are the one stated exception.

**D6. What is never stored.** No transcripts, no raw lines of speech, no audio. No names, contacts, addresses, accounts, health, money, religion, politics or anything about other people. Before a note is proposed, a deterministic check refuses text that looks like a secret, a number sequence (phone, card, identity), an email address, a link or a path, and says why. A note over the length limit is refused, not truncated.

**D7. Where it lives and who sees it.** Only in the control-plane store on this machine (the same place as every note). Never sent anywhere, never given to a lookup (weather, headlines) or a launch request, never in the repository. The dashboard shows notes like any note.

**D8. Phone.** A remote session (ADR-0011 A4.6, A4.7) may read the notes about sir through the conversation ("what do you know about me?") but may **not** create or forget one: the `[about-sir]` and `[about-sir-forget]` prefixes are refused for remote lines, with a plain sentence. Reviews (D3.2) are refused remotely.

**D9. Off switch.** The advisor option `--no-profile` ignores all notes about sir for a run: none are loaded, proposed or reviewed. Without it, the feature is on only after RK merges this and the build.

**D10. Coaching content.** Reviews may comment on how sir phrases things (clarity, repeated words, long sentences) kindly and briefly, and may say what sir tends to ask about. Never on feelings, health, mistakes in facts, or other people. A review is one reply of at most three short sentences plus the proposals.

## 3. Alternatives considered

| Option | Why not chosen |
|---|---|
| A separate profile file or database | A new store and write path to secure and audit; the existing notes already give policy, audit and an append-only record |
| The model decides on its own what to remember | Silent personal data collection; contradicts D2 |
| Keep full transcripts and search them | Far more personal data than the purpose needs; heavy; hard to forget |
| Train or tune the model on conversations | Heavy on this machine, hard to reverse, nothing to confirm; not for the Beta |
| Unprompted coaching | RK's recommended option was coaching only when asked, and RK approved it |

## 4. Evidence

Mechanism proven by the to-do list (`[todo]` prefix, confirmation turn, drop marker) in `advisor/controller.py`. The model's prompt budget (ADR-0013 A1) leaves about 2,200 characters before the 6,000 limit tested in `tests/test_advisor.py`; D5's 800 fits. Comparison with another project's approach: `docs/architecture/openjarvis-lessons-2026-11-19.md` (non-authoritative).

## 5. Security and privacy impact

New: personal observations persist across sessions. Limits: confirmation (D2), no transcripts (D6), local only (D7), phone read-only (D8), off switch (D9), forgetting (D4), bounded size (D5, D6). Residual risks stated plainly: retired notes remain in the append-only audit record; anyone with access to the laptop's store can read the notes; a confirmed note could still be mistaken or out of date, so it is shown on request and easy to retire.

## 6. Complexity impact

One intent group, one prompt block and one checker in `advisor/`; no new surface. Estimated one working session with tests.

## 7. Reversibility

Run with `--no-profile`, or retire all notes (D4): behaviour returns to today's. Removing the code leaves ordinary notes.

## 8. Tests required before the build is merged

Propose-then-confirm for each way in D3.1; decline writes nothing; the checker refuses a secret, number sequence, email, link, path, over-long and multi-sentence text; list, forget one and forget all; only active notes load; the 12-note and 800-character caps; a note containing an instruction is not obeyed (it appears in the prompt only inside the confirmed-facts block); a review proposes at most three, one at a time; no review or proposal happens without being asked; a remote line can read but cannot create, forget or review; `--no-profile` loads and proposes nothing; no transcript is written anywhere; audit shows each write.

## 9. Not done / UNVERIFIED

Nothing is built. Whether a 9B local model produces useful, short, kind observations from one session is unmeasured and would be tested with RK's own sentences before merge. Whether tailoring by notes measurably changes replies is unmeasured.

## 10. Open items for RK

1. Accept, change or refuse each of D1 to D10.
2. The 160-character, 12-note and 800-character limits are my choices; change them if you wish.
3. Whether confirmed notes may ever be used for gentle teasing (proposed: never).
