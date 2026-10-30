"""`note add / list / show` through cli.main (ADR-0010 D6, Beta plan BR-5).

Policy version 1 does not know RECORD_NOTE (policy version 2 is a later, separate
change), so these tests initialize the store with a test policy that is the real file
plus one RECORD_NOTE row. Temporary directories only.
"""

import io
import json
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from jarvis import cli, display, notes
from jarvis.store import Store

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_POLICY = os.path.join(REPO, "policy", "policy.toml")
NOW = "2026-10-30T10:00:00.000000Z"

NOTE_ROW = """
[[capability]]
name = "RECORD_NOTE"
base_level = "L2"
requires_isolation = false
allowed_classes = ["CONTROL_PLANE_RECORD"]
phase_enabled = true
mechanism_implemented = true
forbidden_l5 = false
non_goal = false
"""


def note_policy_text():
    with open(REAL_POLICY, "r", encoding="utf-8") as fh:
        text = fh.read()
    # The capability rows precede the [secret_locations] table; appending after it would
    # put the row in the wrong table, so insert before it.
    marker = "[secret_locations]"
    assert marker in text
    return text.replace(marker, NOTE_ROW.lstrip("\n") + "\n" + marker, 1)


class NotesCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.data = os.path.join(self.tmp, "data")
        self.gov = os.path.join(self.tmp, "gov")
        self.home = os.path.join(self.tmp, "home")
        self.proj = os.path.join(self.tmp, "proj")
        for d in (self.data, self.gov, self.home, self.proj):
            os.makedirs(d)
        self.cfg = os.path.join(self.tmp, "jarvis-test.toml")
        self.write(self.cfg, "schema_version = 1\ndata_root = '%s'\ngovernance_zone = '%s'\n"
                   "user_home = '%s'\n" % (self.data, self.gov, self.home))
        self.policy = os.path.join(self.tmp, "policy-note.toml")
        self.write(self.policy, note_policy_text())
        self.write(os.path.join(self.gov, "revocations.toml"),
                   "schema_version = 1\ncapabilities = []\nprojects = []\ncontract_hashes = []\n")
        self.write(os.path.join(self.gov, "registry.toml"),
                   "schema_version = 1\n[[projects]]\nid = \"p\"\nname = \"P\"\nroot = '%s'\n" % self.proj)
        patcher = mock.patch.object(cli, "utc_now", lambda: NOW)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.assertEqual(self.run_cli("init", "--policy", self.policy)[0], cli.EXIT_OK)

    @staticmethod
    def write(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def run_cli(self, *argv, stdin=None):
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin or "")):
            code = cli.main(["--config", self.cfg] + list(argv), out)
        return code, out.getvalue()

    def add(self, *extra, text="remember this", policy=None):
        return self.run_cli("note", "add", *extra, "--text", text, "--policy", policy or self.policy)

    def records(self):
        conn = sqlite3.connect(Store.db_path(self.data))
        try:
            return [json.loads(r[0]) for r in conn.execute("SELECT record FROM audit_log ORDER BY seq")]
        finally:
            conn.close()

    def memory_files(self):
        found = []
        for folder, _d, files in os.walk(os.path.join(self.data, "memory")):
            found += [os.path.join(folder, f) for f in files]
        return found


class NoteTests(NotesCase):
    def test_a_project_note_is_recorded_listed_and_shown(self):
        code, text = self.add("--project", "p", text="the plan is X\nsecond line")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("note recorded:", text)
        (path,) = self.memory_files()
        self.assertIn(os.path.join("memory", "projects", "p"), path)
        code, listing = self.run_cli("note", "list", "--project", "p")
        self.assertEqual(code, cli.EXIT_OK, listing)
        self.assertIn("note  project/p", listing)
        self.assertIn("notes: 1", listing)
        seq = int(os.path.basename(path)[:-4])
        code, shown = self.run_cli("note", "show", str(seq))
        self.assertEqual(code, cli.EXIT_OK, shown)
        self.assertIn("the plan is X\nsecond line", shown)
        self.assertIn("data, not instruction:", shown)
        self.assertIn("audit verify: OK", self.run_cli("audit", "verify")[1])

    def test_the_audit_record_carries_the_hash_and_mediated_provenance_but_not_the_text(self):
        self.add("--project", "p", text="SECRET-LOOKING-BUT-TYPED-TEXT")
        record = [r for r in self.records() if r["event"] == "NOTE_RECORDED"][0]
        self.assertEqual(record["detail"]["sha256"].__len__(), 64)
        self.assertEqual(record["provenance"]["detail"], "MEDIATED")
        self.assertEqual(record["provenance"]["files_modified"], "OBSERVED")
        self.assertEqual(record["files_modified"], [record["detail"]["path"]])
        self.assertNotIn("SECRET-LOOKING", json.dumps(record))
        self.assertEqual(record["tools_used"], ["RECORD_NOTE"])
        self.assertEqual(record["detail"]["author"], "RK_TYPED")

    def test_task_note_and_decision_note(self):
        self.assertEqual(self.run_cli("task", "create", "--id", "t1", "--project", "p",
                                      "--objective", "x", "--request", "CREATE_TASK")[0], cli.EXIT_OK)
        code, text = self.add("--task", "t1", text="about the task")
        self.assertEqual(code, cli.EXIT_OK, text)
        code, text = self.add("--project", "p", "--decision", text="we chose Y")
        self.assertEqual(code, cli.EXIT_OK, text)
        paths = sorted(os.path.relpath(f, os.path.join(self.data, "memory")).split(os.sep)[0:2]
                       for f in self.memory_files())
        self.assertEqual(paths, [["decisions", "p"], ["tasks", "t1"]])
        self.assertIn("notes: 1", self.run_cli("note", "list", "--task", "t1")[1])
        self.assertIn("decision", self.run_cli("note", "list", "--project", "p")[1])

    def test_scope_errors(self):
        self.assertEqual(self.add("--task", "t1", "--decision")[0], cli.EXIT_NOTE)
        self.assertIn("NOTE_TASK_UNKNOWN", self.add("--task", "nope")[1])
        self.assertIn("NOTE_PROJECT_UNKNOWN", self.add("--project", "nope")[1])
        self.assertIn("NOTE_SCOPE_INVALID", self.add("--project", "../x")[1])
        self.assertEqual(self.memory_files(), [])

    def test_bad_text_is_refused(self):
        self.assertIn("NOTE_TEXT_INVALID", self.add("--project", "p", text="   ")[1])
        self.assertIn("NOTE_TEXT_INVALID", self.add("--project", "p", text="a\x1b[31mred")[1])
        self.assertIn("NOTE_TOO_LONG", self.add("--project", "p", text="x" * (notes.MAX_NOTE_BYTES + 1))[1])
        self.assertEqual(self.memory_files(), [])
        self.assertEqual([r["event"] for r in self.records()], ["GENESIS"])

    def test_text_can_come_from_standard_input(self):
        code, text = self.run_cli("note", "add", "--project", "p", "--text", "-",
                                  "--policy", self.policy, stdin="from stdin")
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertEqual(len(self.memory_files()), 1)

    def test_the_real_policy_does_not_allow_notes_yet(self):
        for name in ("jarvis.db", "HEAD"):
            os.remove(os.path.join(self.data, name))
        self.assertEqual(self.run_cli("init", "--policy", REAL_POLICY)[0], cli.EXIT_OK)
        code, text = self.add("--project", "p", policy=REAL_POLICY)
        self.assertEqual(code, cli.EXIT_NOTE)
        self.assertIn("NOTE_NOT_ALLOWED", text)
        self.assertIn("UNKNOWN_CAPABILITY", text)
        self.assertEqual(self.memory_files(), [])

    def test_a_revoked_capability_is_refused(self):
        self.write(os.path.join(self.gov, "revocations.toml"),
                   "schema_version = 1\ncapabilities = [\"RECORD_NOTE\"]\nprojects = []\ncontract_hashes = []\n")
        code, text = self.add("--project", "p")
        self.assertEqual(code, cli.EXIT_NOTE)
        self.assertIn("REVOKED", text)
        self.assertEqual(self.memory_files(), [])

    def test_a_missing_registry_refuses_project_notes(self):
        os.remove(os.path.join(self.gov, "registry.toml"))
        code, text = self.add("--project", "p")
        self.assertEqual(code, cli.EXIT_NOTE)
        self.assertIn("NOTE_REGISTRY_UNAVAILABLE", text)


class NoteIntegrityTests(NotesCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.add("--project", "p", text="original")[0], cli.EXIT_OK)
        (self.path,) = self.memory_files()
        self.seq = int(os.path.basename(self.path)[:-4])

    def test_a_changed_note_is_detected_by_show_and_doctor(self):
        with open(self.path, "ab") as fh:
            fh.write(b"edited later\n")
        code, text = self.run_cli("note", "show", str(self.seq))
        self.assertEqual(code, cli.EXIT_NOTE)
        self.assertIn("NOTE_FILE_CHANGED", text)
        self.assertNotIn("original", text)
        code, text = self.run_cli("doctor", "--policy", self.policy)
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("FAIL notes: NOTE_FILE_CHANGED #%d" % self.seq, text)

    def test_a_removed_note_is_detected(self):
        os.remove(self.path)
        self.assertIn("NOTE_FILE_MISSING", self.run_cli("note", "show", str(self.seq))[1])
        self.assertIn("NOTE_FILE_MISSING", self.run_cli("doctor", "--policy", self.policy)[1])

    def test_a_file_added_outside_the_chain_is_reported(self):
        self.write(os.path.join(self.data, "memory", "projects", "p", "99.txt"), "sneaked in\n")
        code, text = self.run_cli("doctor", "--policy", self.policy)
        self.assertEqual(code, cli.EXIT_DOCTOR, text)
        self.assertIn("NOTE_FILE_UNRECORDED", text)

    def test_a_healthy_note_passes_doctor(self):
        code, text = self.run_cli("doctor", "--policy", self.policy)
        self.assertIn("PASS notes: 1 recorded, all match the chain", text)

    def test_unknown_note_id(self):
        code, text = self.run_cli("note", "show", "12345")
        self.assertEqual(code, cli.EXIT_NOTE)
        self.assertIn("NOTE_UNKNOWN", text)


class NotesAreDataTests(unittest.TestCase):
    def test_nothing_that_decides_or_plans_imports_notes(self):
        for name in ("planner", "evaluator", "tasks", "contracts", "registry", "policy",
                     "canonicalizer", "revocations", "reports"):
            with open(os.path.join(REPO, "jarvis", name + ".py"), encoding="utf-8") as fh:
                source = fh.read()
            self.assertNotIn("notes", source.replace("denotes", ""), name)

    def test_display_escapes_control_characters_but_keeps_text(self):
        self.assertEqual(display.safe("a\x1b[31mb"), "a\\x1b[31mb")
        self.assertEqual(display.safe("line\n\tnext"), "line\n\tnext")
        self.assertEqual(display.safe("x\x9by"), "x\\x9by")
        self.assertEqual(display.safe("a‮b"), "a\\u202eb")
        self.assertEqual(display.safe("naïve ✓"), "naïve ✓")


if __name__ == "__main__":
    unittest.main()
