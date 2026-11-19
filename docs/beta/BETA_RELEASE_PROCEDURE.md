# Beta release procedure and rehearsal drills

**Non-authoritative** (Beta documents are guides; the ADRs govern). Written 2026-11-20 after comparing release practice with another open-source project (`docs/architecture/openjarvis-lessons-2026-11-19.md`). **Cutting the release is RK's act**: Local Claude prepares everything below and stops before the tag.

## A. Before the tag

1. `git fetch`; `main` equals `origin/main`; no open pull request that belongs in the Beta; the working tree is clean.
2. The `tests` check is green on `main` and the full suite passes locally (`py -3.14 -m unittest discover -t . -s tests`). Record the count.
3. `py -3.14 scripts\boundaries.py` exits 0 on the machine that will run the Beta (anything UNKNOWN is read and explained).
4. Gates B-02, B-06, B-10, B-11 and the `pip freeze` of the voice environment are recorded in `docs/environment/` (Beta plan; each is still RK's or measured).
5. `CHANGELOG.md`: move "Unreleased" under a version heading and date, built from `gh pr list --state merged`, not memory.
6. The register and START HERE are current.

## B. The tag (RK's act)

Tag name proposed: `v0.1.0-beta.1`. RK says "tag it"; then:

```bash
git tag -a v0.1.0-beta.1 -m "JARVIS Beta 1" <commit>
git push origin v0.1.0-beta.1
```

## C. Checksums

From a clean checkout of the tag, produce one archive and its SHA-256, and record both in the release notes. The archive contains the repository only (never `D:\JARVIS`, never governance files, never models or the voice profile):

```bash
git archive --format=zip --prefix=jarvis-0.1.0-beta.1/ -o jarvis-0.1.0-beta.1.zip v0.1.0-beta.1
certutil -hashfile jarvis-0.1.0-beta.1.zip SHA256
```

Verify by hashing a second, independent archive of the same tag: the two hashes must match.

## D. Rehearsal drills (run on a fresh Windows account or a clean snapshot, before 23 Nov and again before the tag)

Adapted from a practice of testing on real machines, not only automated ones. Each drill has a pass line; write the result, not an impression.

| # | Drill | Pass line |
|---|---|---|
| 1 | Fresh account: follow `START_JARVIS.md` from scratch | Reaches a working dashboard link; every step needed is written down |
| 2 | **Start twice**: run `scripts\start-jarvis.cmd`, quit, run it again | Second start changes nothing it should not (no duplicate processes, no growing files) |
| 3 | First reply time after "the model is ready" | Measured and recorded (voice off: seconds; voice on: seconds); no claim without a number |
| 4 | `py -3.14 -m jarvis doctor` and `scripts\check-install.cmd` | Both clean |
| 5 | Backup, then restore verify (`scripts\backup.py`) | Verify passes |
| 6 | **Uninstall check**: remove what the Beta added | Nothing of JARVIS left running or scheduled; the governance and data folders are untouched unless RK removes them |
| 7 | Real microphone press: ring colours, quick tap, hold to talk | Behaviour matches ADR-0011 Amendment 3 (currently UNVERIFIED) |
| 8 | `scripts\boundaries.py` | Exit 0 |

### One failure drill per release (rotate; do at least one)

- Stop the model server (Ollama) in the middle of a conversation: JARVIS says so plainly and keeps working in text.
- Start with the approved-models list missing or edited: conversation is off, with a plain sentence, nothing else breaks.
- Start with the voice folder missing: text only, with a plain sentence.
- Pull the network during a weather request: the plain "could not read that" sentence, no hang.
- Start with a non-JARVIS program already using the dashboard's port (when a fixed port exists): refuses, never picks another.

## E. After the tag

Record in `docs/environment/` the commit, the test count, the archive hash, the drill results (pass or fail, with the evidence) and everything still UNVERIFIED. Do not describe a drill as passed that was not run.
