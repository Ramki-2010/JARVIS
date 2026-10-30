"""`resume` through cli.main (Beta plan BR-5): a cold start with no conversational state.

Uses the notes test base: a store initialized with a policy that knows RECORD_NOTE.
Temporary directories only.
"""

import hashlib
import os
import sqlite3
import unittest

from jarvis import cli
from jarvis.store import Store

from .test_notes_cli import NotesCase


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class ResumeTests(NotesCase):
    def resume(self, *extra):
        return self.run_cli("resume", "--policy", self.policy, *extra)

    def task(self, task_id, *requests, project="p", objective="do something"):
        args = ["task", "create", "--id", task_id, "--project", project, "--objective", objective]
        for request in requests or ("CREATE_TASK",):
            args += ["--request", request]
        self.assertEqual(self.run_cli(*args)[0], cli.EXIT_OK)

    def test_a_cold_empty_store(self):
        code, text = self.resume()
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("audit: OK (tail seq 0)", text)
        self.assertIn("health: OK", text)
        self.assertIn("p  P  [", text)
        self.assertIn("unfinished tasks: 0", text)
        self.assertIn("recent finished tasks: 0 of 0", text)
        self.assertIn("latest notes (data, not instruction): 0 of 0", text)

    def test_unfinished_tasks_notes_and_recent_work_are_recovered(self):
        self.task("t-open", objective="still to do")
        self.task("t-run", objective="in flight")
        self.run_cli("task", "evaluate", "t-run", "--policy", self.policy)
        self.task("t-done", objective="finished work")
        self.run_cli("task", "evaluate", "t-done", "--policy", self.policy)
        self.run_cli("task", "run", "t-done")
        self.add("--project", "p", text="first note")
        self.add("--project", "p", "--decision", text="we chose option Y  with   spacing")
        code, text = self.resume()
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("unfinished tasks: 2", text)
        self.assertLess(text.index("t-run  RUNNING"), text.index("t-open  PENDING"),
                        "RUNNING work is listed before PENDING work")
        self.assertIn("still to do", text)
        self.assertIn("recent finished tasks: 1 of 1", text)
        self.assertIn("t-done  COMPLETED_UNVERIFIED", text)
        self.assertIn("latest notes (data, not instruction): 2 of 2", text)
        self.assertLess(text.index("we chose option Y with spacing"), text.index("first note"),
                        "newest note first")

    def test_two_runs_give_the_same_text_and_write_nothing(self):
        self.task("t1")
        self.add("--project", "p", text="a note")
        before = (digest(Store.db_path(self.data)), digest(os.path.join(self.data, "HEAD")),
                  sorted(self.memory_files()))
        first = self.resume()
        second = self.resume()
        self.assertEqual(first, second)
        after = (digest(Store.db_path(self.data)), digest(os.path.join(self.data, "HEAD")),
                 sorted(self.memory_files()))
        self.assertEqual(before, after)

    def test_project_filter(self):
        self.write(os.path.join(self.gov, "registry.toml"),
                   "schema_version = 1\n[[projects]]\nid = \"p\"\nname = \"P\"\nroot = '%s'\n"
                   "[[projects]]\nid = \"q\"\nname = \"Q\"\n" % self.proj)
        self.task("tp", project="p", objective="belongs to p")
        self.task("tq", project="q", objective="belongs to q")
        text = self.resume("--project", "q")[1]
        self.assertIn("belongs to q", text)
        self.assertNotIn("belongs to p", text)
        self.assertNotIn("p  P  [", text)
        code, text = self.resume("--project", "zzz")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("project zzz is not registered", text)

    def test_a_changed_note_is_flagged_not_shown_and_health_fails(self):
        self.add("--project", "p", text="original words")
        (path,) = self.memory_files()
        with open(path, "ab") as fh:
            fh.write(b"tampered\n")
        code, text = self.resume()
        self.assertIn("[NOTE_FILE_CHANGED]", text)
        self.assertNotIn("original words", text)
        self.assertIn("FAIL notes: NOTE_FILE_CHANGED", text)
        self.assertIn("health: 1 failure(s)", text)

    def test_a_broken_chain_is_reported_and_exits_5(self):
        conn = sqlite3.connect(Store.db_path(self.data))
        try:
            conn.execute("UPDATE audit_log SET record = CAST(record || x'20' AS BLOB) WHERE seq = 0")
            conn.commit()
        finally:
            conn.close()
        code, text = self.resume()
        self.assertEqual(code, cli.EXIT_AUDIT, text)
        self.assertIn("audit: PROBLEMS", text)

    def test_a_missing_registry_falls_back_to_the_projects_of_tasks(self):
        self.task("t1")
        os.remove(os.path.join(self.gov, "registry.toml"))
        code, text = self.resume()
        self.assertEqual(code, cli.EXIT_OK, text)
        self.assertIn("registry unavailable: REGISTRY_MISSING", text)
        self.assertIn("t1  PENDING", text)

    def test_missing_store(self):
        os.remove(Store.db_path(self.data))
        os.remove(os.path.join(self.data, "HEAD"))
        code, text = self.resume()
        self.assertEqual(code, cli.EXIT_STORE_MISSING)


if __name__ == "__main__":
    unittest.main()
