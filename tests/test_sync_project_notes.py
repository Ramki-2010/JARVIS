"""scripts/sync_project_notes.py: reads only PROJECT_STATUS.md and local git state, cleans what it reads, skips unchanged notes."""

import importlib.util
import os
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sync_project_notes", os.path.join(REPO, "scripts", "sync_project_notes.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

STATUS = """# Project -- Status

## Current Version
Proj v1.0 (two ragas)

> a quote that must not be taken as the version

### Current Accuracy
| Raga | Clips | LOO Acc |
|---|---|---|
| A | 3 | 90% |
| **Overall** | **10** | **64.1% decided** |

### Active Gates

| Gate | Question | Status | Next action |
|------|----------|--------|-------------|
| Q-1 | q? | ANSWERED 2026-07 -- done | done |
| Q-2 | q? | **ACTIVE** -- see `docs/x_y.md`\x07 [link](http://example.com/a) | Do the thing |

## Philosophy
"""


class Clean(unittest.TestCase):
    def test_strips_markup_and_control_characters(self):
        self.assertEqual(sync.clean("**bold** `code` [text](http://x.y) a\x07b"), "bold code text a b")

    def test_is_bounded(self):
        self.assertLessEqual(len(sync.clean("word " * 200, 50)), 50)


class Build(unittest.TestCase):
    def make(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with open(os.path.join(tmp.name, "PROJECT_STATUS.md"), "w", encoding="utf-8") as fh:
            fh.write(STATUS)
        return tmp.name

    def build(self, repo):
        answers = {"rev-parse --abbrev-ref HEAD": "main", "rev-parse --short HEAD": "abc1234",
                   "rev-list --left-right --count HEAD...origin/main": "1\t2",
                   "log -5 --format=%cs %h %s": "2026-11-01 abc1234 First\n2026-10-31 def5678 Second"}
        with mock.patch.object(sync, "git", side_effect=lambda repo, *a: answers[" ".join(a)]):
            return sync.build_notes(repo)

    def test_three_notes_with_the_facts(self):
        notes = {k: t for k, _key, t in self.build(self.make())}
        self.assertEqual(set(notes), {"stage", "gates", "git"})
        self.assertIn("Proj v1.0 (two ragas)", notes["stage"])
        self.assertNotIn("quote", notes["stage"])
        self.assertIn("10 clips, 64.1% decided", notes["stage"])
        self.assertIn("1 ahead, 2 behind origin/main", notes["git"])
        self.assertIn("abc1234 First", notes["git"])

    def test_only_open_gates_and_clean_text(self):
        gates = {k: t for k, _key, t in self.build(self.make())}["gates"]
        self.assertIn("Q-2", gates)
        self.assertNotIn("Q-1", gates)
        self.assertNotIn("\x07", gates)
        self.assertNotIn("http", gates)

    def test_key_is_stable_for_same_content_and_marked(self):
        repo = self.make()
        a, b = self.build(repo), self.build(repo)
        self.assertEqual([k for _, k, _ in a], [k for _, k, _ in b])
        for kind, key, text in a:
            self.assertIn("[sync:%s:%s]" % (kind, key), text)
            self.assertLessEqual(len(text.encode()), 16 * 1024)

    def test_marker_pattern_round_trips(self):
        kind, key, text = self.build(self.make())[0]
        self.assertEqual(sync.MARK.search(text).groups(), (kind, key))


if __name__ == "__main__":
    unittest.main()
